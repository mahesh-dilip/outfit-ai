import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

// This component needs allItems to look up image URLs by ID
const SavedOutfits = ({ allItems }) => {
  const [savedOutfits, setSavedOutfits] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSavedOutfits = async () => {
      const userId = 1; // Hardcoded for now
      try {
        setLoading(true);
        const response = await axios.get(`${API_URL}/users/${userId}/saved-outfits`);
        setSavedOutfits(response.data);
      } catch (err) {
        console.error("Failed to fetch saved outfits", err);
      } finally {
        setLoading(false);
      }
    };

    fetchSavedOutfits();
  }, [allItems]); // Re-fetch if allItems changes, e.g., on first load

  const getItemById = (id) => allItems.find(item => item.id === id);

  if (loading) return <p className="text-center text-gray-500">Loading favorites...</p>;

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <h2 className="text-3xl font-bold mb-6 text-center text-gray-800">My Favorite Outfits</h2>

      {savedOutfits.length === 0 ? (
        <p className="text-center text-gray-500">You haven't saved any outfits yet.</p>
      ) : (
        <div className="space-y-8">
          {savedOutfits.map((outfit) => (
            <div key={outfit.id} className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-2xl font-bold mb-2">{outfit.name}</h3>
              <p className="text-gray-600 mb-4 italic">{outfit.reason}</p>
              <div className="flex flex-wrap gap-4">
                {/* The item IDs are stored as a string "1,5,23", so we split and parse them */}
                {outfit.item_ids.split(',').map(idStr => {
                  const item = getItemById(parseInt(idStr, 10));
                  return item ? (
                    <div key={item.id} className="text-center">
                      <img 
                        src={item.image_url} 
                        alt={item.title}
                        className="w-24 h-24 sm:w-32 sm:h-32 rounded-lg object-cover shadow"
                      />
                      <p className="text-xs mt-1 font-semibold">{item.title}</p>
                    </div>
                  ) : null;
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SavedOutfits;