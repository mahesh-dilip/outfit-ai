import google.generativeai as genai
import os
import json

API_KEY = "AIzaSyBbzWd10xSgXxbu5_WivBlJDTWxMDufXfo" # Make sure your key is still here
genai.configure(api_key=API_KEY)

# UPDATED: Configure the model to output JSON
generation_config = {
  "temperature": 0.8,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
  "response_mime_type": "application/json", # <-- This is the key change
}

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=generation_config
)

def generate_outfit_recommendations(query: str, items: list) -> dict:
    """
    Takes a user's query and their list of clothes and returns outfit ideas
    as a structured JSON object.
    """
    wardrobe_list = ""
    for item in items:
        wardrobe_list += f"- ID {item.id}: {item.title} (Category: {item.category}, Color: {item.color})\n"

    # UPDATED: The prompt now demands a JSON structure
    prompt_parts = [
        "You are a helpful and creative personal fashion stylist.",
        "A user needs an outfit recommendation based on their real wardrobe.",
        "Your task is to analyze the user's request and their available items and create 2-3 distinct outfit combinations.",
        "You MUST reply with only a valid JSON object.",
        "The JSON object should be an array of outfits. Each outfit object must have three keys:",
        "1. 'outfit_name': A short, creative name for the outfit (e.g., 'Casual Weekend').",
        "2. 'outfit_items': An array of numbers, where each number is the ID of an item from the provided wardrobe list.",
        "3. 'outfit_reason': A brief, one-sentence explanation for why the outfit works.",
        "\n**User's Request:**",
        f"\"{query}\"",
        "\n**Available Wardrobe Items:**",
        f"{wardrobe_list}",
    ]

    response = model.generate_content(prompt_parts)

    # The response text will now be a JSON string, so we parse it into a Python dict
    return json.loads(response.text)