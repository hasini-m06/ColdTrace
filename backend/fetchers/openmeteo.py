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
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Error fetching OpenMeteo: {response.text}")
        return None, None
        
    data = response.json()
    hourly_temps = data.get("hourly", {}).get("temperature_2m", [])
    if not hourly_temps:
        return None, None
        
    current_temp = hourly_temps[0]
    max_48h_temp = max(hourly_temps[:48])
    delta = max_48h_temp - current_temp
    
    return current_temp, delta
