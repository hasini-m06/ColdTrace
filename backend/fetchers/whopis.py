import requests
from bs4 import BeautifulSoup
import re

def scrape_equipment_reliability():
    """Scrapes WHO PIS cold chain equipment catalog to get reliability scores (cold life hours)."""
    url = "https://extranet.who.int/prequal/cold-chain-equipment"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        equipment_map = {}
        
        rows = soup.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 3:
                model = cols[0].text.strip()
                cold_life_text = cols[2].text.strip()
                match = re.search(r'(\d+)', cold_life_text)
                if match:
                    equipment_map[model] = int(match.group(1))
                    
        return equipment_map
    except Exception as e:
        print(f"Error scraping WHO PIS: {e}")
        return {}

def get_equipment_reliability(model_name: str) -> int:
    """Returns reliability score (cold life in hours) for a given model, or default."""
    equip_map = scrape_equipment_reliability()
    # Default 48 hours if not found
    return equip_map.get(model_name, 48)
