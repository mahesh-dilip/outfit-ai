import React, { useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { getAuthHeaders } from '../App';

const API_URL = 'http://127.0.0.1:8000';

// It now receives all wardrobe items as a prop
const OutfitRecommender = ({ allItems }) => {
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [occasion, setOccasion] = useState('');
  const [recommendations, setRecommendations] = useState([]); // Default to an empty array
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query) {
      setError('Please enter a request.');
      return;
    }

    setLoading(true);
    setError(null);
    setRecommendations([]);

    try {
      const requestData = { query };
      if (location) requestData.location = location;
      if (occasion) requestData.occasion = occasion;

      const response = await axios.post(
        `${API_URL}/me/recommend-outfit`,
        requestData,
        {
          timeout: 30000,
          headers: getAuthHeaders()
        }
      );
      setRecommendations(response.data.outfits || []); // This uses the whole response directly
    } catch (err) {
      setError('Could not get recommendations. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  // A helper to find item details by its ID
  const getItemById = (id) => allItems.find(item => item.id === id);

  const handleSaveOutfit = async (outfit) => {
    const outfitData = {
      name: outfit.outfit_name,
      reason: outfit.outfit_reason,
      items: outfit.outfit_items
    };
    try {
      await axios.post(`${API_URL}/me/save-outfit`, outfitData, {
        headers: getAuthHeaders()
      });
      alert(`Outfit "${outfit.outfit_name}" saved!`);
    } catch (err) {
      alert("Failed to save outfit.");
      console.error(err);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <h2 className="text-3xl font-bold mb-6 text-center text-gray-800">Get Outfit Ideas</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., 'What can I wear for a casual brunch?'"
          className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        />

        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Location (e.g., 'San Francisco' or 'London,UK')"
            className="flex-grow px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
          <select
            value={occasion}
            onChange={(e) => setOccasion(e.target.value)}
            className="flex-grow px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
          >
            <option value="">Occasion (optional)</option>
            <option value="casual">Casual</option>
            <option value="work">Work</option>
            <option value="date night">Date Night</option>
            <option value="gym">Gym</option>
            <option value="formal">Formal Event</option>
            <option value="wedding">Wedding</option>
            <option value="party">Party</option>
            <option value="outdoor activity">Outdoor Activity</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-150 disabled:bg-purple-300"
        >
          {loading ? 'Thinking...' : 'Get Ideas'}
        </button>
      </form>

      {error && <p className="text-center text-red-500 mb-4">{error}</p>}
      
      {/* --- START OF NEW SKELETON UI --- */}
      {loading && (
        <div className="space-y-8">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="bg-white p-6 rounded-lg shadow-md">
              <motion.div 
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="h-8 w-1/2 bg-gray-200 rounded mb-4"
              ></motion.div>
              <motion.div 
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
                className="h-4 w-3/4 bg-gray-200 rounded mb-6"
              ></motion.div>
              <div className="flex flex-wrap gap-4">
                {[...Array(3)].map((_, j) => (
                  <motion.div 
                    key={j}
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: j * 0.2 }}
                    className="w-32 h-32 bg-gray-200 rounded-lg"
                  ></motion.div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      {/* --- END OF NEW SKELETON UI --- */}

      {/* The existing recommendation display */}
      {!loading && recommendations.length > 0 && (
        <div className="space-y-8">
          {recommendations.map((outfit, index) => {
            console.log("--- Rendering Outfit:", outfit.outfit_name);
            return (
            <div key={index} className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-grow">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-2xl font-bold">{outfit.outfit_name}</h3>
                    {outfit.formality_level && (
                      <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs font-semibold rounded-full">
                        {outfit.formality_level}
                      </span>
                    )}
                  </div>
                  <p className="text-gray-600 italic">{outfit.outfit_reason}</p>
                </div>
                <button
                  onClick={() => handleSaveOutfit(outfit)}
                  className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-1 px-3 rounded-full ml-4"
                >
                  Save
                </button>
              </div>
              <div className="flex flex-wrap gap-4">
                {outfit.outfit_items.map(itemId => {
                  console.log(`Looking for item with ID: ${itemId} (Type: ${typeof itemId})`);
                  const item = getItemById(itemId);
                  console.log("Found item:", item); 
                  return item ? (
                    <div key={item.id} className="text-center">
                      <img 
                        src={item.image_url} 
                        alt={item.title}
                        className="w-24 h-24 sm:w-32 sm:h-32 rounded-lg object-cover shadow"
                        onError={(e) => { e.target.onerror = null; e.target.src="https://via.placeholder.com/150?text=No+Image"; }}
                      />
                      <p className="text-xs mt-1 font-semibold">{item.title}</p>
                    </div>
                  ) : null;
                })}
              </div>
            </div>
          )})}
        </div>
      )}
    </div>
  );
};

export default OutfitRecommender;