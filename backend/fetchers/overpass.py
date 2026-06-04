import requests
from core.config import settings

def fetch_phc_locations():
    """Fetches PHC locations using Overpass API based on bounds in config."""
    b = settings.app.bounds
    query = f"""
    [out:json];
    (
      node["amenity"="clinic"]({b.south},{b.west},{b.north},{b.east});
      node["healthcare"="centre"]({b.south},{b.west},{b.north},{b.east});
    );
    out body;
    """
    
    url = "https://overpass-api.de/api/interpreter"
    headers = {'User-Agent': 'ColdTraceApp/1.0'}
    try:
        response = requests.post(url, data={'data': query}, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Status code {response.status_code}")
        data = response.json()
    except Exception as e:
        print(f"Error fetching Overpass data: {e}")
        
        print("Overpass API failed or empty. Using fallback mock locations for demo...")
        import random
        mock_locations = []
        # Bangalore bounds roughly: lat 12.8 to 13.1, lng 77.4 to 77.8
        for i in range(500):
            mock_locations.append({
                "id": 99900000 + i,
                "name": f"Mock PHC Facility {i}",
                "lat": round(random.uniform(12.8, 13.1), 6),
                "lng": round(random.uniform(77.4, 77.8), 6),
                "district": "Bengaluru Urban"
            })
        return mock_locations
    
    locations = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name", "Unknown PHC")
        district = tags.get("addr:district", "Unknown")
            
        locations.append({
            "name": name,
            "lat": element.get("lat"),
            "lng": element.get("lon"),
            "district": district
        })
    return locations
