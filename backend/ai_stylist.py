import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

genai.configure(api_key=API_KEY)

generation_config = {
  "temperature": 0.8, "response_mime_type": "application/json",
}
model = genai.GenerativeModel(model_name="gemini-2.0-flash", generation_config=generation_config)

def generate_outfit_recommendations(
    query: str,
    items: list,
    weather_context: str = None,
    occasion: str = None,
    time_of_day: str = None,
    season: str = None
) -> dict:
    """
    Generates outfits from a pre-filtered list of relevant items with context awareness.

    Args:
        query: User's outfit request/query
        items: List of wardrobe items
        weather_context: Formatted weather information
        occasion: Type of occasion (e.g., "work", "date night", "casual")
        time_of_day: Time of day (e.g., "Morning", "Evening")
        season: Current season (e.g., "Summer", "Winter")

    Returns:
        Dictionary with outfit recommendations
    """
    wardrobe_list = "".join([f"- ID {item.id}: {item.title} (Category: {item.category}, Color: {item.color})\n" for item in items])

    # Build context information
    context_parts = []
    if weather_context:
        context_parts.append(f"**Weather:** {weather_context}")
    if occasion:
        context_parts.append(f"**Occasion:** {occasion}")
    if time_of_day:
        context_parts.append(f"**Time of Day:** {time_of_day}")
    if season:
        context_parts.append(f"**Season:** {season}")

    context_info = "\n".join(context_parts) if context_parts else ""

    prompt_parts = [
        "You are a helpful and creative personal fashion stylist with expertise in weather-appropriate dressing, occasion styling, and color coordination.",
        "A user needs an outfit recommendation. You have already been provided with a pre-filtered list of the most relevant items from their wardrobe.",
        f"Your task is to create 5-7 distinct outfit combinations from ONLY these provided items.",
        "Consider the context information (weather, occasion, time of day, season) when making recommendations.",
        "You MUST reply with only a valid JSON object. The object should contain a single key 'outfits' which is an array of outfit objects.",
        "Each outfit object must have four keys: 'outfit_name', 'outfit_items', 'outfit_reason', and 'formality_level'.",
        "1. 'outfit_name': A short, creative name for the outfit.",
        "2. 'outfit_items': An array of INTEGERS. Each integer MUST be the ID of an item from the provided wardrobe list (e.g., [1, 5, 23]).",
        "3. 'outfit_reason': A detailed explanation for why these items work together. Include style principles, color theory, and how the outfit fits the context.",
        "4. 'formality_level': Rate the outfit's formality on a scale: 'Very Casual', 'Casual', 'Smart Casual', 'Business Casual', 'Formal', or 'Very Formal'.",
        f"\n**User's Request:** \"{query}\"",
    ]

    if context_info:
        prompt_parts.append(f"\n**Context:**\n{context_info}")

    prompt_parts.append(f"\n**Relevant Wardrobe Items:**\n{wardrobe_list}")
    prompt_parts.append("\nRemember: Create 5-7 different outfit combinations with detailed explanations for each.")
    
    try:
        response = model.generate_content(prompt_parts)
        
        if not response.parts:
            block_reason = response.prompt_feedback.block_reason
            return {
                "outfits": [{
                    "outfit_name": "Could not generate outfits",
                    "outfit_items": [],
                    "outfit_reason": f"The request was blocked by the AI for safety reasons: {block_reason}. Please try a different query."
                }]
            }
            
        return json.loads(response.text)

    except Exception as e:
        print(f"Error in generate_outfit_recommendations: {e}")
        import traceback
        traceback.print_exc()
        return {
            "outfits": [{
                "outfit_name": "Error Generating Outfit",
                "outfit_items": [],
                "outfit_reason": f"An unexpected error occurred: {str(e)}. Please try again."
            }]
        }