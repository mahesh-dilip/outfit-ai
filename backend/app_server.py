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

class WardrobeItemSchema(WardrobeItemBase):
    id: int
    owner_id: int
    image_url: Optional[str] = None
    class Config:
        from_attributes = True

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

def db_create_wardrobe_item(db: Session, user_id: int, title: str, description: str, category: str, color: str, image_file: UploadFile):
    # Read image bytes to use for both embedding and uploading
    image_bytes = image_file.file.read()

    # Pass the bytes to the GCS upload function
    image_url = upload_to_gcs(image_file, image_bytes)

    db_item = WardrobeItem(
        title=title, description=description, category=category, color=color,
        image_url=image_url, owner_id=user_id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # NEW: Pass the image bytes along with the text for multimodal embedding
    item_text_for_embedding = f"Title: {db_item.title}, Category: {db_item.category}, Color: {db_item.color}"
    add_item_to_index(item_id=db_item.id, item_text=item_text_for_embedding, image_bytes=image_bytes)

    return db_item

# ==============================================================================
#  7. FASTAPI APP SETUP
# ==============================================================================
app = FastAPI(title="OutfitAI API", docs_url="/docs")

# Get CORS origins from environment
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    image: UploadFile = File(...)
):
    """Create a new wardrobe item (authenticated)"""
    # Ensure user can only create items for themselves
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to create items for this user")
    
    return db_create_wardrobe_item(
        db=db, user_id=user_id, title=title, description=description,
        category=category, color=color, image_file=image
    )

@app.get("/users/{user_id}/items/", response_model=List[WardrobeItemSchema])
def read_items_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get all wardrobe items for a user (authenticated)"""
    # Ensure user can only read their own items
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's items")
    
    items = db.query(WardrobeItem).filter(WardrobeItem.owner_id == user_id).all()
    return items

@app.post("/users/{user_id}/recommend-outfit")
def recommend_outfit_endpoint(
    user_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Generate outfit recommendations (authenticated)"""
    # Ensure user can only get recommendations for themselves
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to get recommendations for this user")
    
    user_query = request.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query is missing.")

    # 1. RETRIEVAL: Find relevant item IDs using vector search
    relevant_ids = find_similar_item_ids(query=user_query, k=10)

    if not relevant_ids:
        return {"outfits": []}

    # 2. AUGMENTATION: Get the full details for the retrieved items from the main database
    relevant_items = db.query(WardrobeItem).filter(WardrobeItem.id.in_(relevant_ids)).all()

    print(f"--- Found {len(relevant_items)} relevant items for query: '{user_query}' ---")

    # 3. GENERATION: Send only the relevant items to the AI
    recommendations = generate_outfit_recommendations(query=user_query, items=relevant_items)
    
    print("----- DEBUG: FINAL RESPONSE TO FRONTEND -----")
    print(recommendations)
    print("-------------------------------------------")

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

