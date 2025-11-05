"""
Weather Service - Integrates with OpenWeather API for context-aware outfit recommendations
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, Dict, Any

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather_by_location(location: str) -> Optional[Dict[str, Any]]:
    """
    Fetch current weather for a location using OpenWeather API.

    Args:
        location: City name, e.g., "San Francisco" or "London,UK"

    Returns:
        Dictionary with weather data or None if request fails
    """
    if not OPENWEATHER_API_KEY:
        print("Warning: OPENWEATHER_API_KEY not set. Weather features will be disabled.")
        return None

    try:
        params = {
            "q": location,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"  # Use metric for Celsius, imperial for Fahrenheit
        }

        response = requests.get(OPENWEATHER_BASE_URL, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()

        # Extract relevant weather information
        weather_info = {
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "temp_min": data["main"]["temp_min"],
            "temp_max": data["main"]["temp_max"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "main": data["weather"][0]["main"],  # e.g., "Rain", "Clear", "Clouds"
            "wind_speed": data["wind"]["speed"],
            "location": data["name"],
            "country": data["sys"]["country"]
        }

        return weather_info

    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Error parsing weather data: {e}")
        return None


def get_weather_by_coordinates(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Fetch current weather by latitude and longitude.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dictionary with weather data or None if request fails
    """
    if not OPENWEATHER_API_KEY:
        print("Warning: OPENWEATHER_API_KEY not set. Weather features will be disabled.")
        return None

    try:
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }

        response = requests.get(OPENWEATHER_BASE_URL, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()

        weather_info = {
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "temp_min": data["main"]["temp_min"],
            "temp_max": data["main"]["temp_max"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "main": data["weather"][0]["main"],
            "wind_speed": data["wind"]["speed"],
            "location": data["name"],
            "country": data["sys"]["country"]
        }

        return weather_info

    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Error parsing weather data: {e}")
        return None


def get_season() -> str:
    """
    Determine current season based on date.

    Returns:
        Season name: "Winter", "Spring", "Summer", or "Fall"
    """
    month = datetime.now().month

    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    else:  # 9, 10, 11
        return "Fall"


def get_time_of_day() -> str:
    """
    Determine time of day based on current hour.

    Returns:
        Time of day: "Morning", "Afternoon", "Evening", or "Night"
    """
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 21:
        return "Evening"
    else:
        return "Night"


def format_weather_for_prompt(weather: Optional[Dict[str, Any]]) -> str:
    """
    Format weather data into a human-readable string for AI prompt.

    Args:
        weather: Weather data dictionary from get_weather_by_location/coordinates

    Returns:
        Formatted weather string
    """
    if not weather:
        return "Weather information unavailable."

    temp_c = weather["temperature"]
    temp_f = temp_c * 9/5 + 32

    return (
        f"Current weather in {weather['location']}, {weather['country']}: "
        f"{weather['description']} with temperature {temp_c:.1f}°C ({temp_f:.1f}°F), "
        f"feels like {weather['feels_like']:.1f}°C. "
        f"Humidity: {weather['humidity']}%, Wind speed: {weather['wind_speed']} m/s."
    )


def get_weather_appropriate_clothing_hints(weather: Optional[Dict[str, Any]]) -> str:
    """
    Generate clothing suggestions based on weather conditions.

    Args:
        weather: Weather data dictionary

    Returns:
        Clothing hints string
    """
    if not weather:
        return ""

    temp = weather["temperature"]
    main_condition = weather["main"].lower()
    hints = []

    # Temperature-based hints
    if temp < 0:
        hints.append("very cold weather (consider heavy coats, scarves, gloves)")
    elif temp < 10:
        hints.append("cold weather (consider jackets, sweaters, long pants)")
    elif temp < 20:
        hints.append("mild weather (consider light layers, long sleeves)")
    elif temp < 28:
        hints.append("warm weather (consider t-shirts, light fabrics)")
    else:
        hints.append("hot weather (consider shorts, tank tops, breathable fabrics)")

    # Condition-based hints
    if "rain" in main_condition or "drizzle" in main_condition:
        hints.append("rainy conditions (consider waterproof layers)")
    elif "snow" in main_condition:
        hints.append("snowy conditions (consider warm, waterproof boots and coat)")
    elif "clear" in main_condition and temp > 25:
        hints.append("sunny and hot (consider sun protection, light colors)")

    return " - ".join(hints) if hints else ""
