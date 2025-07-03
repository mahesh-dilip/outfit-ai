import React, { useState } from 'react';
import axios from 'axios';

// IMPORTANT: Use the same backend URL from your previous setup.
// If your backend is running on your machine, this should work.
const API_URL = 'http://127.0.0.1:8000';

const AddItemForm = ({ onNewItem }) => {
    // State hooks to store the form input values
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [color, setColor] = useState('');
  const [imageFile, setImageFile] = useState(null); // State for the image file
  const [message, setMessage] = useState(null); // To show success/error messages

  const handleSubmit = async (e) => {
    e.preventDefault(); // Prevent the default form submission behavior

    if (!title || !category || !color || !imageFile) {
      setMessage({ type: 'error', text: 'Please fill in all fields and select an image.' });
      return;
    }

    // For now, we will hardcode the user_id to 1.
    // In a real app, this would come from the logged-in user's state.
    const userId = 1;

    // Use FormData to send both file and text data
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('category', category);
    formData.append('color', color);
    formData.append('image', imageFile); // 'image' must match the backend parameter name

    try {
      // The header is important for file uploads
      const config = {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      };

      const response = await axios.post(`${API_URL}/users/${userId}/items/`, formData, config);

      // Show success message
      setMessage({ type: 'success', text: `Item "${response.data.title}" was added!` });
      onNewItem();

      // Clear the form fields
      setTitle('');
      setDescription('');
      setCategory('');
      setColor('');
      setImageFile(null);
      // Reset the file input visually
      document.getElementById('image-upload').value = null;
    } catch (error) {
      console.error('Error adding item:', error);
      setMessage({ type: 'error', text: 'Could not add item. Check console for details.' });
    }
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white p-8 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">Add a New Wardrobe Item</h2>
      
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="title" className="block text-gray-700 text-sm font-bold mb-2">Title*</label>
          <input
            type="text"
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Blue Denim Jacket"
            className="w-full px-3 py-2 border rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="mb-4">
          <label htmlFor="description" className="block text-gray-700 text-sm font-bold mb-2">Description</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g., Worn once, very comfortable"
            className="w-full px-3 py-2 border rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="mb-4">
          <label htmlFor="category" className="block text-gray-700 text-sm font-bold mb-2">Category*</label>
          <input
            type="text"
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g., Outerwear, Top, Bottom"
            className="w-full px-3 py-2 border rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="mb-4">
          <label htmlFor="color" className="block text-gray-700 text-sm font-bold mb-2">Color*</label>
          <input
            type="text"
            id="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            placeholder="e.g., Blue, Black, Red"
            className="w-full px-3 py-2 border rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="mb-4">
          <label htmlFor="image-upload" className="block text-gray-700 text-sm font-bold mb-2">Image*</label>
          <input
            type="file"
            id="image-upload"
            onChange={(e) => setImageFile(e.target.files[0])} // Get the first selected file
            className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>

        <button 
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-150 ease-in-out"
        >
          Add Item to Wardrobe
        </button>
      </form>

      {message && (
        <div 
          className={`mt-4 p-4 rounded-lg text-center font-bold ${
            message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
};

export default AddItemForm;