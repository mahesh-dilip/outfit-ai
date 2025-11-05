import React, { useState } from 'react';
import axios from 'axios';
import { getAuthHeaders } from '../App';

const API_URL = 'http://127.0.0.1:8000';

// The component now receives items and loading state as props from App.jsx
const WardrobeGallery = ({ items, loading, onItemDeleted }) => {
  const [deletingItemId, setDeletingItemId] = useState(null);

  const handleDelete = async (itemId, itemTitle) => {
    // Confirm deletion
    if (!window.confirm(`Are you sure you want to delete "${itemTitle}" from your wardrobe?`)) {
      return;
    }

    // Prevent multiple delete operations
    if (deletingItemId) return;

    setDeletingItemId(itemId);

    try {
      await axios.delete(`${API_URL}/me/items/${itemId}`, {
        headers: getAuthHeaders()
      });

      // Notify parent component to refresh items list
      if (onItemDeleted) {
        onItemDeleted();
      }
    } catch (error) {
      console.error('Error deleting item:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to delete item. Please try again.';
      alert(errorMsg);
    } finally {
      setDeletingItemId(null);
    }
  };

  if (loading) {
    return <p className="text-center text-gray-500">Loading your wardrobe...</p>;
  }

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <h2 className="text-3xl font-bold mb-6 text-center text-gray-800">My Wardrobe</h2>

      {items.length === 0 ? (
        <p className="text-center text-gray-500">Your wardrobe is empty. Add an item below!</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {items.map((item) => (
            <div key={item.id} className="bg-white rounded-lg shadow-md overflow-hidden relative group">
              {/* Delete button - shows on hover */}
              <button
                onClick={() => handleDelete(item.id, item.title)}
                disabled={deletingItemId === item.id}
                className="absolute top-2 right-2 bg-red-500 hover:bg-red-700 text-white rounded-full w-8 h-8 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 disabled:opacity-50 disabled:cursor-not-allowed z-10"
                title="Delete item"
              >
                {deletingItemId === item.id ? (
                  <span className="text-xs">...</span>
                ) : (
                  <span className="text-lg font-bold">&times;</span>
                )}
              </button>

              <img
                src={item.image_url}
                alt={item.title}
                className="w-full h-48 object-cover"
                onError={(e) => { e.target.onerror = null; e.target.src="https://via.placeholder.com/150?text=No+Image"; }}
              />
              <div className="p-3">
                <h3 className="font-bold text-sm truncate">{item.title}</h3>
                <p className="text-xs text-gray-600">{item.category}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default WardrobeGallery;