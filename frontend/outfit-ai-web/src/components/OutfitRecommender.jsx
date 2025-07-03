import React, { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

// It now receives all wardrobe items as a prop
const OutfitRecommender = ({ allItems }) => {
  const [query, setQuery] = useState('');
  const [recommendations, setRecommendations] = useState([]); // Default to an empty array
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query) {
      setError('Please enter a request.');
      return;
    }

    const userId = 1;
    setLoading(true);
    setError(null);
    setRecommendations([]);

    try {
      const response = await axios.post(`${API_URL}/users/${userId}/recommend-outfit`, { query }, {timeout: 30000});
      setRecommendations(response.data || []); // This uses the whole response directly
    } catch (err) {
      setError('Could not get recommendations. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  // A helper to find item details by its ID
  const getItemById = (id) => allItems.find(item => item.id === id);

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <h2 className="text-3xl font-bold mb-6 text-center text-gray-800">Get Outfit Ideas</h2>
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., 'What can I wear for a casual brunch?'"
          className="flex-grow w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full sm:w-auto bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-150 disabled:bg-purple-300"
        >
          {loading ? 'Thinking...' : 'Get Ideas'}
        </button>
      </form>

      {error && <p className="text-center text-red-500 mb-4">{error}</p>}
      
      {recommendations.length > 0 && (
        <div className="space-y-8">
          {recommendations.map((outfit, index) => (
            <div key={index} className="bg-white p-6 rounded-lg shadow-md">
              <h3 className="text-2xl font-bold mb-2">{outfit.outfit_name}</h3>
              <p className="text-gray-600 mb-4 italic">{outfit.outfit_reason}</p>
              <div className="flex flex-wrap gap-4">
                {outfit.outfit_items.map(itemId => {
                  const item = getItemById(itemId);
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
          ))}
        </div>
      )}
    </div>
  );
};

export default OutfitRecommender;