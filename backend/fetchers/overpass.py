import requests
from core.config import settings
import os
import json

def fetch_phc_locations():
    """
    Fetches PHC (Primary Health Centre) and hospital locations in Karnataka.
    Uses static JSON cache to prevent API rate limits.
    """
    data_file = os.path.join(os.path.dirname(__file__), "..", "data", "locations.json")
    
    # Return cached data if available
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            return json.load(f)
            
    query = """
    [out:json];
    area["name"="Karnataka"]->.searchArea;
    (
      node["amenity"="hospital"](area.searchArea);
      node["amenity"="clinic"](area.searchArea);
      node["healthcare"="centre"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
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
        name = tags.get("name", "Unknown Facility")
        
        # Only take nodes with lat/lng
        if "lat" in element and "lon" in element:
            locations.append({
                "id": element["id"],
                "name": name,
                "lat": element["lat"],
                "lng": element["lon"],
                "district": "Unknown" # OpenStreetMap doesn't easily map to district
            })
            
    # ensure data directory exists
    os.makedirs(os.path.dirname(data_file), exist_ok=True)
    with open(data_file, "w") as f:
        json.dump(locations, f)
        
    return locations
