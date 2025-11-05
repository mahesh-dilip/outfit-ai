import faiss
import numpy as np
from google.cloud import aiplatform
from vertexai.vision_models import Image, MultiModalEmbeddingModel
import os
import pickle
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from logging_config import get_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = get_logger(__name__)

# --- Configuration ---
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR", "./vector_db_data")

if not PROJECT_ID:
    raise ValueError("GCP_PROJECT_ID environment variable is not set")

# Initialize the Vertex AI client
aiplatform.init(project=PROJECT_ID, location=LOCATION)

# Load the multimodal embedding model from Vertex AI
model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding")
EMBEDDING_DIM = 1408 # The dimension for this specific model

# Persistence file paths
VECTOR_DB_PATH = Path(VECTOR_DB_DIR)
FAISS_INDEX_FILE = VECTOR_DB_PATH / "faiss_index.bin"
MAPPING_FILE = VECTOR_DB_PATH / "index_mapping.pkl"

# --- Vector Database with Persistence ---
index = faiss.IndexFlatL2(EMBEDDING_DIM)
index_to_item_id = {}


def get_multimodal_embedding(text: str, image_bytes: bytes) -> np.ndarray:
    """Generates a multimodal embedding from text and an image using Vertex AI."""
    
    # Load the image data
    image = Image(image_bytes=image_bytes)
    
    # Get the embeddings
    embeddings = model.get_embeddings(
        contextual_text=text,
        image=image,
        dimension=EMBEDDING_DIM,
    )
    
    # Extract the image embedding vector
    vector = embeddings.image_embedding
    return np.array(vector).astype('float32')


def save_index():
    """Save FAISS index and mapping to disk."""
    try:
        # Create directory if it doesn't exist
        VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(index, str(FAISS_INDEX_FILE))
        
        # Save item ID mapping
        with open(MAPPING_FILE, 'wb') as f:
            pickle.dump(index_to_item_id, f)
        
        logger.info(f"Vector index saved successfully: {index.ntotal} embeddings")
        return True
    except Exception as e:
        logger.error(f"Failed to save vector index: {e}", exc_info=True)
        return False


def load_index():
    """Load FAISS index and mapping from disk."""
    global index, index_to_item_id
    
    try:
        if not FAISS_INDEX_FILE.exists() or not MAPPING_FILE.exists():
            logger.info("No existing vector index found - starting fresh")
            return False
        
        # Load FAISS index
        index = faiss.read_index(str(FAISS_INDEX_FILE))
        
        # Load item ID mapping
        with open(MAPPING_FILE, 'rb') as f:
            index_to_item_id = pickle.load(f)
        
        logger.info(f"Vector index loaded successfully: {index.ntotal} embeddings")
        return True
    except Exception as e:
        logger.error(f"Failed to load vector index: {e}", exc_info=True)
        logger.warning("Starting with empty index")
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        index_to_item_id = {}
        return False


def backup_index():
    """Create a backup of the current index."""
    try:
        if not FAISS_INDEX_FILE.exists():
            logger.warning("No index to backup")
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = VECTOR_DB_PATH / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_index_file = backup_dir / f"faiss_index_{timestamp}.bin"
        backup_mapping_file = backup_dir / f"index_mapping_{timestamp}.pkl"
        
        # Copy files
        import shutil
        shutil.copy2(FAISS_INDEX_FILE, backup_index_file)
        shutil.copy2(MAPPING_FILE, backup_mapping_file)
        
        logger.info(f"Vector index backed up: {backup_index_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to backup vector index: {e}", exc_info=True)
        return False


def get_index_stats():
    """Get statistics about the vector index."""
    return {
        "total_embeddings": index.ntotal,
        "dimension": EMBEDDING_DIM,
        "index_type": "IndexFlatL2",
        "persisted": FAISS_INDEX_FILE.exists(),
        "mapping_count": len(index_to_item_id)
    }


def add_item_to_index(item_id: int, item_text: str, image_bytes: bytes):
    """Generates multimodal embedding and adds it to the index."""
    try:
        embedding = get_multimodal_embedding(item_text, image_bytes)
        index.add(np.array([embedding]))
        index_to_item_id[index.ntotal - 1] = item_id
        
        # Save after each addition to ensure persistence
        save_index()
        
        logger.info(f"Added item {item_id} to vector index (total: {index.ntotal})")
    except Exception as e:
        logger.error(f"Failed to add item {item_id} to vector index: {e}", exc_info=True)
        raise


def find_similar_item_ids(query: str, k: int = 10) -> list[int]:
    """Finds similar items for a text query."""
    if index.ntotal == 0:
        logger.warning("Vector index is empty - no items to search")
        return []

    search_k = min(k, index.ntotal)
    
    try:
        # Get the embedding for the text query
        embeddings = model.get_embeddings(
            contextual_text=query,
            dimension=EMBEDDING_DIM,
        )
        
        query_embedding = np.array(embeddings.text_embedding).astype('float32')
        
        query_embedding_2d = np.array([query_embedding])
        distances, indices = index.search(query_embedding_2d, search_k)
        retrieved_ids = [index_to_item_id[i] for i in indices[0] if i != -1]
        
        logger.info(f"Vector search for '{query}': found {len(retrieved_ids)} items")
        return retrieved_ids
    except Exception as e:
        logger.error(f"Vector search failed for query '{query}': {e}", exc_info=True)
        return []


# Load index on module import
logger.info("Initializing vector database...")
load_index()