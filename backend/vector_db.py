import faiss
import numpy as np
from google.cloud import aiplatform
from vertexai.vision_models import Image, MultiModalEmbeddingModel
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

if not PROJECT_ID:
    raise ValueError("GCP_PROJECT_ID environment variable is not set")

# Initialize the Vertex AI client
aiplatform.init(project=PROJECT_ID, location=LOCATION)

# Load the multimodal embedding model from Vertex AI
model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding")
EMBEDDING_DIM = 1408 # The dimension for this specific model

# --- In-Memory Vector Database ---
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


def add_item_to_index(item_id: int, item_text: str, image_bytes: bytes):
    """Generates multimodal embedding and adds it to the index."""
    embedding = get_multimodal_embedding(item_text, image_bytes)
    index.add(np.array([embedding]))
    index_to_item_id[index.ntotal - 1] = item_id
    print(f"Successfully added Item ID {item_id} to Vertex AI multimodal vector index.")


def find_similar_item_ids(query: str, k: int = 10) -> list[int]:
    """Finds similar items for a text query."""
    if index.ntotal == 0:
        return []

    search_k = min(k, index.ntotal)
    
    # Get the embedding for the text query
    embeddings = model.get_embeddings(
        contextual_text=query,
        dimension=EMBEDDING_DIM,
    )
    
    query_embedding = np.array(embeddings.text_embedding).astype('float32')
    
    query_embedding_2d = np.array([query_embedding])
    distances, indices = index.search(query_embedding_2d, search_k)
    retrieved_ids = [index_to_item_id[i] for i in indices[0] if i != -1]
    
    return retrieved_ids