import React from 'react';

// The component now receives items and loading state as props from App.jsx
const WardrobeGallery = ({ items, loading }) => {
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
            <div key={item.id} className="bg-white rounded-lg shadow-md overflow-hidden">
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