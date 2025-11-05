from sqlalchemy.orm import Session
import models, schemas
from fastapi import UploadFile
import os
from google.cloud import storage

# --- GCS Configuration ---
# Set the path to your service account key file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'gcs_key.json' 
# Replace with your actual GCS bucket name
GCS_BUCKET_NAME = 'outfit-ai-wardrobe-images-mahesh' 

def upload_to_gcs(file: UploadFile) -> str:
    """Uploads a file to the GCS bucket and returns its public URL."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)

    # Create a new blob and upload the file's content
    blob = bucket.blob(file.filename)
    blob.upload_from_file(file.file, content_type=file.content_type)

    return blob.public_url

# For now, we are skipping password hashing for simplicity.
# In a real app, you would NEVER store plain text passwords.
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    # NEVER store plain text passwords. This is a placeholder.
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(email=user.email, hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_wardrobe_items_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.WardrobeItem).filter(models.WardrobeItem.owner_id == user_id).offset(skip).limit(limit).all()

def create_wardrobe_item(db: Session, user_id: int, title: str, description: str, category: str, color: str, image_file: UploadFile):
    # First, upload the image to GCS
    image_url = upload_to_gcs(image_file)

    # Then, create the database record with the public URL
    db_item = models.WardrobeItem(
        title=title,
        description=description,
        category=category,
        color=color,
        image_url=image_url, # Save the URL here
        owner_id=user_id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item