import React, { useState, useEffect } from 'react';
import axios from 'axios';
import AddItemForm from './components/AddItemForm';
import WardrobeGallery from './components/WardrobeGallery';
import OutfitRecommender from './components/OutfitRecommender';
import SavedOutfits from './components/SavedOutfits'; // <-- 1. Import new component

const API_URL = 'http://127.0.0.1:8000';

function App() {
  const [wardrobeItems, setWardrobeItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchItems = async () => {
    const userId = 1;
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/users/${userId}/items/`);
      setWardrobeItems(response.data);
    } catch (err) {
      console.error("Failed to fetch items", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 font-sans">
      <header className="bg-white shadow-sm">
        <h1 className="text-4xl font-bold text-center text-gray-800 py-4">
          OutfitAI
        </h1>
      </header>

      <main className="p-4 sm:p-6 md:p-8">
        <OutfitRecommender allItems={wardrobeItems} />

        {/* 2. Add the SavedOutfits component here */}
        <hr className="my-8 sm:my-12 border-t-2 border-gray-200" />
        <SavedOutfits allItems={wardrobeItems} />

        <hr className="my-8 sm:my-12 border-t-2 border-gray-200" />
        
        <WardrobeGallery items={wardrobeItems} loading={loading} />

        <hr className="my-8 sm:my-12 border-t-2 border-gray-200" />
        
        <AddItemForm onNewItem={fetchItems} />
      </main>
    </div>
  );
}

export default App;