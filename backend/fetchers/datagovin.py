import requests
import urllib.parse
from core.config import DATA_GOV_IN_API_KEY

def search_dataset(keyword: str):
    """Finds dataset index_name dynamically based on keyword."""
    if not DATA_GOV_IN_API_KEY:
        print("DATA_GOV_IN_API_KEY not set!")
        return None

    url = f"https://api.data.gov.in/lists?filters[keyword]={urllib.parse.quote(keyword)}&api-key={DATA_GOV_IN_API_KEY}&format=json"
    try:
        response = requests.get(url)
        data = response.json()
        records = data.get("records", [])
        if records:
            return records[0].get("index_name")
    except Exception as e:
        print(f"Error searching dataset: {e}")
    return None

def fetch_hmis_wastage():
    """Fetches HMIS wastage data. Returns a dict mapping district to wastage rate."""
    resource_id = search_dataset("HMIS immunization")
    if not resource_id:
        print("HMIS resource ID not found. Using fallback mock data for now.")
        # Provide some fallback for testing
        return {"bengaluru urban": 0.05, "mysuru": 0.08, "belagavi": 0.12}
        
    url = f"https://api.data.gov.in/resource/{resource_id}?api-key={DATA_GOV_IN_API_KEY}&format=json&limit=100"
    try:
        response = requests.get(url)
        data = response.json()
        records = data.get("records", [])
        wastage_map = {}
        for r in records:
            district = str(r.get("district", r.get("District", "Unknown"))).lower()
            try:
                wastage = float(r.get("wastage_rate", r.get("Wastage Rate", 0)))
            except ValueError:
                wastage = 0.0
            wastage_map[district] = wastage
        return wastage_map
    except Exception as e:
        print(f"Error fetching HMIS data: {e}")
    return {}

def fetch_power_outage():
    """Fetches power outage data. Returns a dict mapping district to outage count."""
    resource_id = search_dataset("power outage karnataka")
    if not resource_id:
        print("Power outage resource ID not found. Using fallback.")
        return {"bengaluru urban": 2, "mysuru": 5, "belagavi": 8}
        
    url = f"https://api.data.gov.in/resource/{resource_id}?api-key={DATA_GOV_IN_API_KEY}&format=json&limit=100"
    try:
        response = requests.get(url)
        data = response.json()
        records = data.get("records", [])
        outage_map = {}
        for r in records:
            district = str(r.get("district", r.get("District", "Unknown"))).lower()
            try:
                count = int(r.get("outage_count", r.get("Outage Count", 0)))
            except ValueError:
                count = 0
            outage_map[district] = count
        return outage_map
    except Exception as e:
        print(f"Error fetching Power Outage data: {e}")
    return {}
