from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# The database URL for SQLite. This will create a file named 'outfitai.db'
SQLALCHEMY_DATABASE_URL = "sqlite:///./outfitai.db"

# Create the SQLAlchemy engine
# connect_args is needed only for SQLite to allow multithreading
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Each instance of the SessionLocal class will be a new database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models. The models will inherit from this class.
Base = declarative_base()