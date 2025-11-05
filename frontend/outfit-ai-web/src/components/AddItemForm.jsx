import React, { useState } from 'react';
import axios from 'axios';
import { getAuthHeaders } from '../App';

const API_URL = 'http://127.0.0.1:8000';

const AddItemForm = ({ onNewItem }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [color, setColor] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [message, setMessage] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);

  // AI Auto-Fill Feature - Analyzes image and suggests metadata
  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    setImageFile(file);

    if (!file) return;

    // Show AI loading state
    setAiLoading(true);
    setMessage({ type: 'info', text: '🤖 AI analyzing image...' });

    try {
      const formData = new FormData();
      formData.append('image', file);

      // Call backend AI analysis endpoint
      const response = await axios.post(`${API_URL}/ai/analyze-image/`, formData, {
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'multipart/form-data',
        },
      });

      // Auto-fill form with AI suggestions
      const aiData = response.data;
      if (aiData.title) setTitle(aiData.title);
      if (aiData.description) setDescription(aiData.description);
      if (aiData.category) setCategory(aiData.category);
      if (aiData.color) setColor(aiData.color);

      setMessage({ type: 'success', text: '✨ AI auto-filled form! Feel free to edit.' });
    } catch (error) {
      console.error('AI analysis failed:', error);
      setMessage({ type: 'warning', text: 'AI analysis unavailable. Please fill manually.' });
    } finally {
      setAiLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!title || !category || !color || !imageFile) {
      setMessage({ type: 'error', text: 'Please fill in all required fields and select an image.' });
      return;
    }

    // Prevent double submissions
    if (submitLoading) return;

    setSubmitLoading(true);
    setMessage(null);

    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('category', category);
    formData.append('color', color);
    formData.append('image', imageFile);

    try {
      const config = {
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'multipart/form-data',
        },
      };

      const response = await axios.post(`${API_URL}/me/items/`, formData, config);

      setMessage({ type: 'success', text: `Item "${response.data.title}" was added!` });
      onNewItem();

      // Clear form
      setTitle('');
      setDescription('');
      setCategory('');
      setColor('');
      setImageFile(null);
      document.getElementById('image-upload').value = null;
    } catch (error) {
      console.error('Error adding item:', error);
      const errorMsg = error.response?.data?.detail || 'Could not add item. Check console for details.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setSubmitLoading(false);
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
          <label htmlFor="image-upload" className="block text-gray-700 text-sm font-bold mb-2">
            Image* {aiLoading && <span className="text-blue-600 animate-pulse">(AI analyzing...)</span>}
          </label>
          <input
            type="file"
            id="image-upload"
            onChange={handleImageUpload}
            accept="image/*"
            className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <p className="text-xs text-gray-500 mt-1">
            🤖 AI will automatically fill the form based on your image!
          </p>
        </div>

        <button
          type="submit"
          disabled={submitLoading}
          className={`w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition duration-150 ease-in-out ${
            submitLoading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {submitLoading ? 'Adding...' : 'Add Item to Wardrobe'}
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