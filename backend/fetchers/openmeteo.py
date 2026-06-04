import requests

def fetch_temperature_forecast(lat: float, lng: float):
    """Fetches 48h temp forecast and returns current temp and max delta."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": "temperature_2m",
        "forecast_days": 3,
        "timezone": "Asia/Kolkata"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Get current temp
        current_temp = data['hourly']['temperature_2m'][0]
        
        # Get max temp over next 48h
        next_48h = data['hourly']['temperature_2m'][:48]
        max_temp = max(next_48h)
        
        delta = max_temp - current_temp
        return current_temp, delta
    except Exception as e:
        print(f"Error fetching weather for {lat},{lng}: {e}")
        return None, None
