import requests
import time

def fetch_weather_batch(locations: list):
    """Fetches 48h temp forecast for a batch of locations. Returns a dict mapping loc['id'] to (current_temp, delta)."""
    results = {}
    chunk_size = 50
    url = "https://api.open-meteo.com/v1/forecast"
    
    for i in range(0, len(locations), chunk_size):
        chunk = locations[i:i + chunk_size]
        lats = ",".join([str(loc['lat']) for loc in chunk])
        lngs = ",".join([str(loc['lng']) for loc in chunk])
        
        params = {
            "latitude": lats,
            "longitude": lngs,
            "hourly": "temperature_2m",
            "forecast_days": 3,
            "timezone": "Asia/Kolkata"
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code != 200:
                raise Exception(f"Open-Meteo returned status {response.status_code}: {response.text[:200]}")
            
            data = response.json()
            # If only 1 location is requested, it returns a dict instead of a list
            if isinstance(data, dict):
                data = [data]
            
            for idx, res in enumerate(data):
                loc_id = chunk[idx]['id']
                if 'hourly' in res and 'temperature_2m' in res['hourly']:
                    temps = res['hourly']['temperature_2m']
                    current_temp = temps[0]
                    max_temp = max(temps[:48])
                    delta = max_temp - current_temp
                    results[loc_id] = (current_temp, delta)
            time.sleep(0.5) # respectful delay between chunks
        except Exception as e:
            print(f"Error fetching weather batch {i}: {e}")
            
    return results
