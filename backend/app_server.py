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
    # This now calls the real upload function
    image_url = upload_to_gcs(image_file) 
    
    db_item = WardrobeItem(
        title=title, description=description, category=category, color=color,
        image_url=image_url, owner_id=user_id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
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

# ADD THIS ENTIRE FUNCTION

@app.get("/users/{user_id}/items/", response_model=List[WardrobeItemSchema])
def read_items_endpoint(user_id: int, db: Session = Depends(get_db)):
    # This function fetches all items for a specific user
    items = db.query(WardrobeItem).filter(WardrobeItem.owner_id == user_id).all()
    return items

@app.post("/users/{user_id}/recommend-outfit")
def recommend_outfit_endpoint(user_id: int, request: dict, db: Session = Depends(get_db)):
    user_query = request.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query is missing.")
    
    items = db.query(WardrobeItem).filter(WardrobeItem.owner_id == user_id).all()
    if not items:
        return {"outfits": []}

    # --- START OF DEBUG CODE ---
    print("----- DEBUG: ITEMS SENT TO AI -----")
    for item in items:
        print(f"ID: {item.id}, Title: {item.title}")
    print("---------------------------------")
    # --- END OF DEBUG CODE ---
    
    recommendations = generate_outfit_recommendations(query=user_query, items=items)

    # --- START OF DEBUG CODE ---
    print("----- DEBUG: AI RESPONSE -----")
    print(recommendations)
    print("----------------------------")
    # --- END OF DEBUG CODE ---
    
    return recommendations
