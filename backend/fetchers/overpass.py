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
    response = requests.post(url, data={'data': query})
    if response.status_code != 200:
        print(f"Error fetching Overpass data: {response.text}")
        return []
    
    data = response.json()
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
