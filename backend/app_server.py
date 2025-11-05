# ==============================================================================
#  1. IMPORTS
# ==============================================================================
import os
import uuid
from typing import List, Optional
from datetime import timedelta
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from pydantic import BaseModel
from google.cloud import storage
from dotenv import load_dotenv
from ai_stylist import generate_outfit_recommendations
from vector_db import add_item_to_index, find_similar_item_ids
from auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from PIL import Image
import io

# Load environment variables
load_dotenv()

# Setup logging
from logging_config import setup_logging, get_logger, log_event
from exceptions import (
    OutfitAIException,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
    GCSUploadError,
    DatabaseError
)

setup_logging()
logger = get_logger(__name__)

# ==============================================================================
#  2. DATABASE SETUP
# ==============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./outfitai.db")
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==============================================================================
#  3. DATABASE MODELS (SQLAlchemy)
# ==============================================================================
class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    items = relationship("WardrobeItem", back_populates="owner")

class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    category = Column(String, index=True)
    color = Column(String, index=True)
    image_url = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    # Enhanced metadata fields
    brand = Column(String, nullable=True)
    price = Column(Integer, nullable=True)  # Store in cents to avoid float issues
    purchase_date = Column(String, nullable=True)  # ISO format date string
    wear_count = Column(Integer, default=0)
    last_worn_date = Column(String, nullable=True)  # ISO format date string
    is_favorite = Column(Integer, default=0)  # SQLite doesn't have boolean, use 0/1
    tags = Column(String, nullable=True)  # Comma-separated tags
    
    owner = relationship("UserModel", back_populates="items")

class SavedOutfit(Base):
    __tablename__ = "saved_outfits"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    reason = Column(String)
    item_ids = Column(String) # Storing IDs as a comma-separated string
    owner_id = Column(Integer, ForeignKey("users.id"))

Base.metadata.create_all(bind=engine)

# ==============================================================================
#  4. DATA SCHEMAS (Pydantic)
# ==============================================================================
class WardrobeItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    color: str
    brand: Optional[str] = None
    price: Optional[int] = None  # Price in cents
    purchase_date: Optional[str] = None  # ISO format: YYYY-MM-DD
    tags: Optional[str] = None  # Comma-separated: "formal,summer,favorite"

class WardrobeItemSchema(WardrobeItemBase):
    id: int
    owner_id: int
    image_url: Optional[str] = None
    wear_count: int = 0
    last_worn_date: Optional[str] = None
    is_favorite: bool = False
    
    class Config:
        from_attributes = True
        
    # Custom validator to convert SQLite int to bool
    @classmethod
    def model_validate(cls, obj):
        if hasattr(obj, 'is_favorite'):
            obj.is_favorite = bool(obj.is_favorite)
        return super().model_validate(obj)

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserSchema(UserBase):
    id: int
    items: List[WardrobeItemSchema] = []
    class Config:
        from_attributes = True

class SavedOutfitSchema(BaseModel):
    id: int
    name: str
    reason: str
    item_ids: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# ==============================================================================
#  5. GOOGLE CLOUD STORAGE (GCS) UTILITIES
# ==============================================================================
GCS_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

if not GCS_BUCKET_NAME:
    raise ValueError("GCS_BUCKET_NAME environment variable is not set")

if GCS_CREDENTIALS_PATH:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GCS_CREDENTIALS_PATH

def upload_to_gcs(file: UploadFile, image_bytes: bytes) -> str:
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    unique_filename = f"{uuid.uuid4()}-{file.filename}"
    blob = bucket.blob(unique_filename)

    # Upload from the bytes we already read, instead of from the file object
    blob.upload_from_string(image_bytes, content_type=file.content_type)

    return blob.public_url

# ==============================================================================
#  6. DATABASE CRUD FUNCTIONS
# ==============================================================================
def db_create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def db_create_wardrobe_item(
    db: Session,
    user_id: int,
    title: str,
    description: str,
    category: str,
    color: str,
    image_file: UploadFile,
    brand: Optional[str] = None,
    price: Optional[int] = None,
    purchase_date: Optional[str] = None,
    tags: Optional[str] = None,
    is_favorite: Optional[bool] = False
):
    """Create a wardrobe item with full metadata"""
    try:
        # Read image bytes to use for both embedding and uploading
        image_bytes = image_file.file.read()

        # Pass the bytes to the GCS upload function
        image_url = upload_to_gcs(image_file, image_bytes)

        db_item = WardrobeItem(
            title=title,
            description=description,
            category=category,
            color=color,
            image_url=image_url,
            owner_id=user_id,
            brand=brand,
            price=price,
            purchase_date=purchase_date,
            tags=tags,
            is_favorite=1 if is_favorite else 0,  # Convert bool to int for SQLite
            wear_count=0
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)

        # Pass the image bytes along with the text for multimodal embedding
        item_text_for_embedding = f"Title: {db_item.title}, Category: {db_item.category}, Color: {db_item.color}"
        if brand:
            item_text_for_embedding += f", Brand: {brand}"
        if tags:
            item_text_for_embedding += f", Tags: {tags}"
        
        add_item_to_index(item_id=db_item.id, item_text=item_text_for_embedding, image_bytes=image_bytes)
        
        logger.info(f"Created wardrobe item {db_item.id} for user {user_id}")
        log_event(logger, "ITEM_CREATED", user_id=user_id, item_id=db_item.id, category=category)

        return db_item
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create wardrobe item: {e}", exc_info=True)
        raise DatabaseError(f"Failed to create item: {str(e)}")

# ==============================================================================
#  7. FASTAPI APP SETUP
# ==============================================================================
app = FastAPI(title="OutfitAI API", docs_url="/docs")

# Get CORS origins from environment
# Support both localhost and 127.0.0.1 for local development
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler for custom exceptions
@app.exception_handler(OutfitAIException)
async def outfit_ai_exception_handler(request, exc: OutfitAIException):
    logger.error(
        f"{exc.error_code}: {exc.message}",
        extra={"extra_fields": {
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": str(request.url)
        }}
    )
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Outfit AI API starting up...")
    logger.info(f"Database URL: {DATABASE_URL}")
    logger.info(f"CORS origins: {cors_origins}")

# Shutdown event  
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Outfit AI API shutting down...")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current authenticated user from JWT token"""
    from jose import JWTError, jwt
    
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-please-change-in-production")
        ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

# ==============================================================================
#  8. API ENDPOINTS (ROUTES)
# ==============================================================================

# Authentication endpoints
@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint - returns JWT token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=UserSchema)
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return db_create_user(db=db, user=user)

@app.get("/users/me", response_model=UserSchema)
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@app.post("/users/{user_id}/items/", response_model=WardrobeItemSchema)
def create_item_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    color: str = Form(...),
    image: UploadFile = File(...),
    brand: Optional[str] = Form(None),
    price: Optional[int] = Form(None),
    purchase_date: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    is_favorite: Optional[bool] = Form(False)
):
    """Create a new wardrobe item with rich metadata (authenticated)"""
    # Ensure user can only create items for themselves
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to create items for this user")
    
    return db_create_wardrobe_item(
        db=db, user_id=user_id, title=title, description=description,
        category=category, color=color, image_file=image,
        brand=brand, price=price, purchase_date=purchase_date,
        tags=tags, is_favorite=is_favorite
    )

@app.get("/users/{user_id}/items/", response_model=List[WardrobeItemSchema])
def read_items_endpoint(
    user_id: int,
    category: Optional[str] = None,
    color: Optional[str] = None,
    brand: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get wardrobe items with optional filtering (authenticated)"""
    # Ensure user can only read their own items
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's items")
    
    # Build query with filters
    query = db.query(WardrobeItem).filter(WardrobeItem.owner_id == user_id)
    
    if category:
        query = query.filter(WardrobeItem.category == category)
    if color:
        query = query.filter(WardrobeItem.color == color)
    if brand:
        query = query.filter(WardrobeItem.brand == brand)
    if is_favorite is not None:
        query = query.filter(WardrobeItem.is_favorite == (1 if is_favorite else 0))
    if tags:
        # Simple tag search (contains)
        query = query.filter(WardrobeItem.tags.like(f"%{tags}%"))
    
    items = query.all()
    
    logger.info(f"Retrieved {len(items)} items for user {user_id} with filters")
    return items

@app.get("/users/{user_id}/items/{item_id}", response_model=WardrobeItemSchema)
def read_item_endpoint(
    user_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific wardrobe item (authenticated)"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's items")
    
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.owner_id == user_id
    ).first()
    
    if not item:
        raise ResourceNotFoundError("Wardrobe item", item_id)
    
    logger.info(f"Retrieved item {item_id} for user {user_id}")
    return item

@app.put("/users/{user_id}/items/{item_id}", response_model=WardrobeItemSchema)
def update_item_endpoint(
    user_id: int,
    item_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    brand: Optional[str] = Form(None),
    price: Optional[int] = Form(None),
    purchase_date: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    is_favorite: Optional[bool] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Update a wardrobe item with metadata (authenticated)"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user's items")
    
    # Get existing item
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.owner_id == user_id
    ).first()
    
    if not item:
        raise ResourceNotFoundError("Wardrobe item", item_id)
    
    # Update fields if provided
    updated_fields = []
    if title is not None:
        item.title = title
        updated_fields.append("title")
    if description is not None:
        item.description = description
        updated_fields.append("description")
    if category is not None:
        item.category = category
        updated_fields.append("category")
    if color is not None:
        item.color = color
        updated_fields.append("color")
    if brand is not None:
        item.brand = brand
        updated_fields.append("brand")
    if price is not None:
        item.price = price
        updated_fields.append("price")
    if purchase_date is not None:
        item.purchase_date = purchase_date
        updated_fields.append("purchase_date")
    if tags is not None:
        item.tags = tags
        updated_fields.append("tags")
    if is_favorite is not None:
        item.is_favorite = 1 if is_favorite else 0
        updated_fields.append("is_favorite")
    
    try:
        db.commit()
        db.refresh(item)
        logger.info(f"Updated item {item_id} for user {user_id}: {', '.join(updated_fields)}")
        log_event(logger, "ITEM_UPDATED", user_id=user_id, item_id=item_id, fields=updated_fields)
        return item
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update item {item_id}: {e}", exc_info=True)
        raise DatabaseError(f"Failed to update item: {str(e)}")

@app.delete("/users/{user_id}/items/{item_id}")
def delete_item_endpoint(
    user_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a wardrobe item (authenticated)"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user's items")
    
    # Get existing item
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.owner_id == user_id
    ).first()
    
    if not item:
        raise ResourceNotFoundError("Wardrobe item", item_id)
    
    try:
        db.delete(item)
        db.commit()
        logger.info(f"Deleted item {item_id} for user {user_id}")
        log_event(logger, "ITEM_DELETED", user_id=user_id, item_id=item_id)
        return {"status": "success", "message": f"Item {item_id} deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete item {item_id}: {e}", exc_info=True)
        raise DatabaseError(f"Failed to delete item: {str(e)}")

@app.delete("/users/{user_id}/items/")
def bulk_delete_items_endpoint(
    user_id: int,
    item_ids: List[int],
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Bulk delete wardrobe items (authenticated)"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user's items")
    
    if not item_ids:
        raise ValidationError("No item IDs provided", field="item_ids")
    
    try:
        # Delete items that belong to the user
        deleted_count = db.query(WardrobeItem).filter(
            WardrobeItem.id.in_(item_ids),
            WardrobeItem.owner_id == user_id
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"Bulk deleted {deleted_count} items for user {user_id}")
        log_event(logger, "ITEMS_BULK_DELETED", user_id=user_id, count=deleted_count)
        return {
            "status": "success",
            "message": f"Successfully deleted {deleted_count} items",
            "deleted_count": deleted_count
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to bulk delete items: {e}", exc_info=True)
        raise DatabaseError(f"Failed to delete items: {str(e)}")

@app.post("/users/{user_id}/items/{item_id}/mark-worn")
def mark_item_worn_endpoint(
    user_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Mark an item as worn (increment wear count, update last worn date)"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.owner_id == user_id
    ).first()
    
    if not item:
        raise ResourceNotFoundError("Wardrobe item", item_id)
    
    try:
        from datetime import date
        item.wear_count = (item.wear_count or 0) + 1
        item.last_worn_date = date.today().isoformat()
        
        db.commit()
        db.refresh(item)
        
        logger.info(f"Marked item {item_id} as worn (count: {item.wear_count})")
        log_event(logger, "ITEM_WORN", user_id=user_id, item_id=item_id, wear_count=item.wear_count)
        
        return {
            "status": "success",
            "wear_count": item.wear_count,
            "last_worn_date": item.last_worn_date
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to mark item as worn: {e}", exc_info=True)
        raise DatabaseError(f"Failed to update item: {str(e)}")

@app.get("/users/{user_id}/wardrobe-stats")
def get_wardrobe_stats_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get wardrobe statistics (categories, colors, brands, etc.)"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from sqlalchemy import func
    
    items = db.query(WardrobeItem).filter(WardrobeItem.owner_id == user_id).all()
    
    # Calculate statistics
    stats = {
        "total_items": len(items),
        "categories": {},
        "colors": {},
        "brands": {},
        "favorites_count": sum(1 for item in items if item.is_favorite),
        "total_value": sum(item.price or 0 for item in items),  # In cents
        "most_worn_items": [],
        "least_worn_items": [],
        "never_worn_count": sum(1 for item in items if item.wear_count == 0)
    }
    
    # Category distribution
    for item in items:
        stats["categories"][item.category] = stats["categories"].get(item.category, 0) + 1
    
    # Color distribution
    for item in items:
        stats["colors"][item.color] = stats["colors"].get(item.color, 0) + 1
    
    # Brand distribution
    for item in items:
        if item.brand:
            stats["brands"][item.brand] = stats["brands"].get(item.brand, 0) + 1
    
    # Most/least worn
    sorted_by_wear = sorted(items, key=lambda x: x.wear_count or 0, reverse=True)
    stats["most_worn_items"] = [
        {"id": item.id, "title": item.title, "wear_count": item.wear_count}
        for item in sorted_by_wear[:5]
    ]
    stats["least_worn_items"] = [
        {"id": item.id, "title": item.title, "wear_count": item.wear_count or 0}
        for item in sorted_by_wear[-5:]
    ]
    
    logger.info(f"Generated wardrobe stats for user {user_id}")
    return stats

@app.post("/users/{user_id}/recommend-outfit")
def recommend_outfit_endpoint(
    user_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Generate outfit recommendations with context awareness (authenticated)"""
    # Ensure user can only get recommendations for themselves
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to get recommendations for this user")

    user_query = request.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query is missing.")

    # Extract context parameters
    location = request.get("location")
    occasion = request.get("occasion")

    # Get weather data if location is provided
    weather_context = None
    if location:
        from weather_service import get_weather_by_location, format_weather_for_prompt, get_weather_appropriate_clothing_hints
        weather_data = get_weather_by_location(location)
        if weather_data:
            weather_formatted = format_weather_for_prompt(weather_data)
            clothing_hints = get_weather_appropriate_clothing_hints(weather_data)
            weather_context = f"{weather_formatted}\nClothing suggestions: {clothing_hints}"

    # Get time of day and season automatically
    from weather_service import get_time_of_day, get_season
    time_of_day = get_time_of_day()
    season = get_season()

    # 1. RETRIEVAL: Find relevant item IDs using vector search
    relevant_ids = find_similar_item_ids(query=user_query, k=10)

    if not relevant_ids:
        return {"outfits": []}

    # 2. AUGMENTATION: Get the full details for the retrieved items from the main database
    relevant_items = db.query(WardrobeItem).filter(WardrobeItem.id.in_(relevant_ids)).all()

    # 3. GENERATION: Send only the relevant items to the AI with context
    recommendations = generate_outfit_recommendations(
        query=user_query,
        items=relevant_items,
        weather_context=weather_context,
        occasion=occasion,
        time_of_day=time_of_day,
        season=season
    )

    return recommendations

@app.post("/users/{user_id}/save-outfit")
def save_outfit_endpoint(
    user_id: int,
    outfit_data: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Save an outfit (authenticated)"""
    # Ensure user can only save outfits for themselves
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to save outfits for this user")
    
    new_saved_outfit = SavedOutfit(
        name=outfit_data.get("name"),
        reason=outfit_data.get("reason"),
        item_ids=",".join(map(str, outfit_data.get("items", []))),
        owner_id=user_id
    )
    db.add(new_saved_outfit)
    db.commit()
    db.refresh(new_saved_outfit)
    return {"status": "success", "saved_outfit_id": new_saved_outfit.id}

@app.get("/users/{user_id}/saved-outfits", response_model=List[SavedOutfitSchema])
def get_saved_outfits_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get all saved outfits for a user (authenticated)"""
    # Ensure user can only access their own saved outfits
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's saved outfits")
    
    saved_outfits = db.query(SavedOutfit).filter(SavedOutfit.owner_id == user_id).all()
    return saved_outfits

# Convenience endpoints that use the authenticated user automatically
@app.get("/me/items/", response_model=List[WardrobeItemSchema])
def read_my_items_endpoint(
    category: Optional[str] = None,
    color: Optional[str] = None,
    brand: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get current user's wardrobe items with optional filtering"""
    return read_items_endpoint(
        user_id=current_user.id,
        category=category,
        color=color,
        brand=brand,
        is_favorite=is_favorite,
        tags=tags,
        db=db,
        current_user=current_user
    )

@app.get("/me/saved-outfits", response_model=List[SavedOutfitSchema])
def get_my_saved_outfits_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get current user's saved outfits"""
    return get_saved_outfits_endpoint(
        user_id=current_user.id,
        db=db,
        current_user=current_user
    )

@app.post("/me/items/", response_model=WardrobeItemSchema)
def create_my_item_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    color: str = Form(...),
    image: UploadFile = File(...),
    brand: Optional[str] = Form(None),
    price: Optional[int] = Form(None),
    purchase_date: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    is_favorite: Optional[bool] = Form(False)
):
    """Create a new wardrobe item for current user"""
    return create_item_endpoint(
        user_id=current_user.id,
        db=db,
        current_user=current_user,
        title=title,
        description=description,
        category=category,
        color=color,
        image=image,
        brand=brand,
        price=price,
        purchase_date=purchase_date,
        tags=tags,
        is_favorite=is_favorite
    )

@app.post("/me/recommend-outfit")
def recommend_my_outfit_endpoint(
    request: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Generate outfit recommendations for current user"""
    return recommend_outfit_endpoint(
        user_id=current_user.id,
        request=request,
        db=db,
        current_user=current_user
    )

@app.post("/me/save-outfit")
def save_my_outfit_endpoint(
    outfit_data: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Save an outfit for current user"""
    return save_outfit_endpoint(
        user_id=current_user.id,
        outfit_data=outfit_data,
        db=db,
        current_user=current_user
    )

@app.delete("/me/items/{item_id}")
def delete_my_item_endpoint(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a wardrobe item for current user"""
    return delete_item_endpoint(
        user_id=current_user.id,
        item_id=item_id,
        db=db,
        current_user=current_user
    )

@app.post("/ai/analyze-image/")
async def analyze_image_with_ai(
    image: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user)
):
    """
    AI-powered image analysis endpoint.
    Analyzes uploaded clothing image and returns suggested metadata.
    """
    try:
        log_event(logger, "AI_IMAGE_ANALYSIS_START", user_id=current_user.id)
        
        # Read image data
        image_data = await image.read()

        # Use Google Gemini AI to analyze the image
        import google.generativeai as genai
        from PIL import Image
        import io

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        # Create a model for vision tasks (using gemini-2.0-flash which supports vision)
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")

        # Convert image bytes to PIL Image for Gemini
        pil_image = Image.open(io.BytesIO(image_data))

        # Create a detailed prompt for clothing analysis
        prompt = """Analyze this clothing item image and provide structured metadata.

Please provide:
1. A short, descriptive title (e.g., "Blue Denim Jacket", "White Cotton T-Shirt")
2. A brief description of the item (style, material, notable features)
3. The category (one of: Tops, Bottoms, Outerwear, Dresses, Shoes, Accessories)
4. The primary color

Respond in valid JSON format like:
{
    "title": "Item name",
    "description": "Brief description",
    "category": "Category",
    "color": "Primary color"
}"""

        # Call Gemini AI with multimodal input
        response = model.generate_content([prompt, pil_image])
        
        # Parse the AI response
        ai_text = response.text.strip()
        
        # Try to extract JSON from response
        import json
        import re
        
        # Find JSON in response (might be wrapped in markdown code blocks)
        json_match = re.search(r'\{[\s\S]*\}', ai_text)
        if json_match:
            ai_data = json.loads(json_match.group())
        else:
            # Fallback if no JSON found
            ai_data = {
                "title": "Clothing Item",
                "description": "AI analysis unavailable",
                "category": "Tops",
                "color": "Unknown"
            }
        
        log_event(logger, "AI_IMAGE_ANALYSIS_SUCCESS", user_id=current_user.id, result=ai_data)
        
        return ai_data
        
    except Exception as e:
        logger.error(f"AI image analysis failed: {e}", exc_info=True)
        log_event(logger, "AI_IMAGE_ANALYSIS_ERROR", user_id=current_user.id, error=str(e))
        
        # Return default values instead of failing
        return {
            "title": "",
            "description": "",
            "category": "",
            "color": ""
        }

