import google.generativeai as genai
import os
import json

API_KEY = "AIzaSyBbzWd10xSgXxbu5_WivBlJDTWxMDufXfo" # Your key here
genai.configure(api_key=API_KEY)

generation_config = {
  "temperature": 0.8, "response_mime_type": "application/json",
}
model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

def generate_outfit_recommendations(query: str, items: list) -> dict:
    """Generates outfits from a pre-filtered list of relevant items."""
    wardrobe_list = "".join([f"- ID {item.id}: {item.title} (Category: {item.category}, Color: {item.color})\n" for item in items])

    prompt_parts = [
        "You are a helpful and creative personal fashion stylist.",
        "A user needs an outfit recommendation. You have already been provided with a pre-filtered list of the most relevant items from their wardrobe.",
        "Your task is to create 2-3 distinct outfit combinations from ONLY these provided items.",
        "You MUST reply with only a valid JSON object. The object should contain a single key 'outfits' which is an array of outfit objects.",
        "Each outfit object must have three keys: 'outfit_name', 'outfit_items', and 'outfit_reason'.",
        "1. 'outfit_name': A short, creative name for the outfit.",
        "2. 'outfit_items': An array of INTEGERS. Each integer MUST be the ID of an item from the provided wardrobe list (e.g., [1, 5, 23]).",
        "3. 'outfit_reason': A short explanation for why these items were chosen together.",
        f"\n**User's Request:** \"{query}\"",
        f"\n**Relevant Wardrobe Items:**\n{wardrobe_list}",
    ]
    
    try:
        response = model.generate_content(prompt_parts)
        
        if not response.parts:
            print("ERROR: AI response was blocked for safety reasons.")
            block_reason = response.prompt_feedback.block_reason
            print(f"Block Reason: {block_reason}")
            return {
                "outfits": [{
                    "outfit_name": "Could not generate outfits",
                    "outfit_items": [],
                    "outfit_reason": f"The request was blocked by the AI for safety reasons: {block_reason}. Please try a different query."
                }]
            }
            
        return json.loads(response.text)

    except Exception as e:
        print(f"ERROR: An exception occurred during AI generation: {e}")
        return {
            "outfits": [{
                "outfit_name": "Error Generating Outfit",
                "outfit_items": [],
                "outfit_reason": "An unexpected error occurred while talking to the AI. Please check the backend logs."
            }]
        }