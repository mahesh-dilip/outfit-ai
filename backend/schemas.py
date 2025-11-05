from pydantic import BaseModel
from typing import List, Optional

# --- Wardrobe Item Schemas ---

class WardrobeItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    color: str
    image_url: Optional[str] = None

class WardrobeItemCreate(WardrobeItemBase):
    pass

class WardrobeItem(WardrobeItemBase):
    id: int
    owner_id: int

    # This is a Pydantic configuration setting that allows it to work
    # with ORM models (like our SQLAlchemy models).
    class Config:
        from_attributes = True


# --- User Schemas ---

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    items: List[WardrobeItem] = []

    class Config:
        from_attributes = True