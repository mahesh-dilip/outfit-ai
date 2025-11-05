import React, { useState, useEffect } from 'react';
import axios from 'axios';
import AddItemForm from './components/AddItemForm';
import WardrobeGallery from './components/WardrobeGallery';
import OutfitRecommender from './components/OutfitRecommender';
import SavedOutfits from './components/SavedOutfits';
import Login from './components/Login';

const API_URL = 'http://127.0.0.1:8000';

// Helper to get auth headers
export const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

function App() {
  const [wardrobeItems, setWardrobeItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check if user is already logged in
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setIsAuthenticated(true);
    }
  }, []);

  const fetchItems = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/me/items/`, {
        headers: getAuthHeaders()
      });
      setWardrobeItems(response.data);
    } catch (err) {
      console.error("Failed to fetch items", err);
      // If unauthorized, clear token and show login
      if (err.response?.status === 401 || err.response?.status === 403) {
        localStorage.removeItem('token');
        setIsAuthenticated(false);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchItems();
    }
  }, [isAuthenticated]);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setWardrobeItems([]);
  };

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-gray-100 font-sans">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-4xl font-bold text-gray-800">
            OutfitAI
          </h1>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold transition duration-150"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="p-4 sm:p-6 md:p-8">
        <OutfitRecommender allItems={wardrobeItems} />

        <hr className="my-8 sm:my-12 border-t-2 border-gray-200" />
        <SavedOutfits allItems={wardrobeItems} />

        <hr className="my-8 sm:my-12 border-t-2 border-gray-200" />
        
        <WardrobeGallery items={wardrobeItems} loading={loading} onItemDeleted={fetchItems} />

        <hr className="my-8 sm:my-12 border-t-2 border-gray-200" />
        
        <AddItemForm onNewItem={fetchItems} />
      </main>
    </div>
  );
}

export default App;
