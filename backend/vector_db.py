import faiss
import numpy as np
import google.generativeai as genai

API_KEY = "AIzaSyBbzWd10xSgXxbu5_WivBlJDTWxMDufXfo"  # Paste your key here
genai.configure(api_key=API_KEY)

# --- Configuration ---
# Use a dedicated model for embeddings
embedding_model = genai.get_model('models/embedding-001')
EMBEDDING_DIM = 768 # Dimensions for the embedding-001 model

# --- In-Memory Vector Database ---
# We create a simple FAISS index. This will live in memory and be rebuilt on startup.
# For a production app, you'd use a persistent vector DB like Pinecone, Weaviate, or Cloud SQL's vector search.
index = faiss.IndexFlatL2(EMBEDDING_DIM)
# A simple dictionary to map the index position back to our database item ID
index_to_item_id = {}

def get_text_embedding(text: str) -> np.ndarray:
    """Generates an embedding for a piece of text."""
    embedding = genai.embed_content(model=embedding_model,
                                    content=text,
                                    task_type="retrieval_document") # Use "retrieval_query" for user queries
    return np.array(embedding['embedding']).astype('float32')

def add_item_to_index(item_id: int, item_text: str):
    """Generates embedding for an item and adds it to the FAISS index."""
    global index, index_to_item_id
    
    embedding = get_text_embedding(item_text)
    
    # FAISS expects a 2D array, so we reshape our 1D embedding
    embedding_2d = np.array([embedding])
    
    # Add the vector to the index
    index.add(embedding_2d)
    
    # Store the mapping from the new index position to the item's actual ID
    # index.ntotal gives the current number of vectors in the index
    index_to_item_id[index.ntotal - 1] = item_id
    print(f"Successfully added Item ID {item_id} to vector index.")

def find_similar_item_ids(query: str, k: int = 10) -> list[int]:
    """Finds the 'k' most similar item IDs for a given text query."""
    if index.ntotal == 0:
        return []

    # Ensure we don't ask for more neighbors than exist in the index
    search_k = min(k, index.ntotal)

    query_embedding = genai.embed_content(
        model=embedding_model,
        content=query,
        task_type="retrieval_query"
    )['embedding']
    
    query_embedding_2d = np.array([query_embedding]).astype('float32')

    # Use our safe search_k value
    distances, indices = index.search(query_embedding_2d, search_k)
    
    # Filter out any invalid '-1' results from FAISS before looking them up
    retrieved_ids = [index_to_item_id[i] for i in indices[0] if i != -1]
    
    return retrieved_ids