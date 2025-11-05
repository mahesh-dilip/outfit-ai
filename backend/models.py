from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from database import Base
# This is a SQLAlchemy Model, representing the 'users' table in the database.
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    # In a real app, this would be a hashed password, not plain text!
    hashed_password = Column(String)

    # This creates the relationship between User and WardrobeItem
    items = relationship("WardrobeItem", back_populates="owner")


# This is a SQLAlchemy Model, representing the 'wardrobe_items' table.
class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    category = Column(String, index=True)
    color = Column(String, index=True)
    image_url = Column(String, nullable=True)
    # The owner_id column is a foreign key to the users.id column
    owner_id = Column(Integer, ForeignKey("users.id"))

    # This creates the relationship back to the User
    owner = relationship("User", back_populates="items")