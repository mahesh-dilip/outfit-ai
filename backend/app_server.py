# ==============================================================================
#  1. IMPORTS
# ==============================================================================
import os
import uuid
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from pydantic import BaseModel
from google.cloud import storage # <-- RE-ENABLED
from ai_stylist import generate_outfit_recommendations
from vector_db import add_item_to_index, find_similar_item_ids

# ==============================================================================
#  2. DATABASE SETUP
# ==============================================================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./outfitai.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
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

# ==============================================================================
#  5. GOOGLE CLOUD STORAGE (GCS) UTILITIES
# ==============================================================================
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'gcs_key.json'
GCS_BUCKET_NAME = 'outfit-ai-wardrobe-images-mahesh' # Your bucket name

def upload_to_gcs(file: UploadFile) -> str:
    """Uploads a file to the GCS bucket and returns its public URL."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    
    # Create a unique filename to prevent overwrites
    unique_filename = f"{uuid.uuid4()}-{file.filename}"
    blob = bucket.blob(unique_filename)
    
    blob.upload_from_file(file.file, content_type=file.content_type)
    
    return blob.public_url

# ==============================================================================
#  6. DATABASE CRUD FUNCTIONS
# ==============================================================================
def db_create_user(db: Session, user: UserCreate):
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = UserModel(email=user.email, hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def db_create_wardrobe_item(db: Session, user_id: int, title: str, description: str, category: str, color: str, image_file: UploadFile):
    image_url = upload_to_gcs(image_file)
    db_item = WardrobeItem(
        title=title, description=description, category=category, color=color,
        image_url=image_url, owner_id=user_id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # NEW: Generate and add embedding to vector DB after saving
    item_text_for_embedding = f"Title: {db_item.title}, Category: {db_item.category}, Color: {db_item.color}, Description: {db_item.description}"
    add_item_to_index(item_id=db_item.id, item_text=item_text_for_embedding)

    return db_item

# ==============================================================================
#  7. FASTAPI APP SETUP
# ==============================================================================
app = FastAPI(title="OutfitAI API", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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

# ==============================================================================
#  8. API ENDPOINTS (ROUTES)
# ==============================================================================
@app.post("/users/", response_model=UserSchema)
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return db_create_user(db=db, user=user)

@app.post("/users/{user_id}/items/", response_model=WardrobeItemSchema)
def create_item_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    title: str = File(...),
    description: str = File(...),
    category: str = File(...),
    color: str = File(...),
    image: UploadFile = File(...)
):
    return db_create_wardrobe_item(
        db=db, user_id=user_id, title=title, description=description,
        category=category, color=color, image_file=image
    )

@app.get("/users/{user_id}/items/", response_model=List[WardrobeItemSchema])
def read_items_endpoint(user_id: int, db: Session = Depends(get_db)):
    # This function fetches all items for a specific user
    items = db.query(WardrobeItem).filter(WardrobeItem.owner_id == user_id).all()
    return items

# This will build the index from existing DB items on startup
def build_index_on_startup():
    db = SessionLocal()
    print("Building vector index from database...")
    all_items = db.query(WardrobeItem).all()
    for item in all_items:
        item_text_for_embedding = f"Title: {item.title}, Category: {item.category}, Color: {item.color}, Description: {item.description}"
        add_item_to_index(item_id=item.id, item_text=item_text_for_embedding)
    db.close()
    print("Vector index built successfully.")

build_index_on_startup() # Call the function when the server starts

@app.post("/users/{user_id}/recommend-outfit")
def recommend_outfit_endpoint(user_id: int, request: dict, db: Session = Depends(get_db)):
    user_query = request.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query is missing.")

    # 1. RETRIEVAL: Find relevant item IDs using vector search
    relevant_ids = find_similar_item_ids(query=user_query, k=10) # Get top 10 relevant items

    if not relevant_ids:
        return {"outfits": []}

    # 2. AUGMENTATION: Get the full details for the retrieved items from the main database
    relevant_items = db.query(WardrobeItem).filter(WardrobeItem.id.in_(relevant_ids)).all()

    print(f"--- Found {len(relevant_items)} relevant items for query: '{user_query}' ---")

    # 3. GENERATION: Send only the relevant items to the AI
    recommendations = generate_outfit_recommendations(query=user_query, items=relevant_items)
    
    # --- START OF DEBUG CODE ---
    print("----- DEBUG: FINAL RESPONSE TO FRONTEND -----")
    print(recommendations)
    print("-------------------------------------------")
    # --- END OF DEBUG CODE ---

    return recommendations

@app.post("/users/{user_id}/save-outfit")
def save_outfit_endpoint(user_id: int, outfit_data: dict, db: Session = Depends(get_db)):
    new_saved_outfit = SavedOutfit(
        name=outfit_data.get("name"),
        reason=outfit_data.get("reason"),
        item_ids=",".join(map(str, outfit_data.get("items", []))), # Convert list of ints to string
        owner_id=user_id
    )
    db.add(new_saved_outfit)
    db.commit()
    db.refresh(new_saved_outfit)
    return {"status": "success", "saved_outfit_id": new_saved_outfit.id}

@app.get("/users/{user_id}/saved-outfits", response_model=List[SavedOutfitSchema])
def get_saved_outfits_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Fetches all saved outfits for a specific user."""
    saved_outfits = db.query(SavedOutfit).filter(SavedOutfit.owner_id == user_id).all()
    return saved_outfits

