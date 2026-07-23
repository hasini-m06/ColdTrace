import requests
from fetchers.overpass import fetch_phc_locations
from fetchers.openmeteo import fetch_weather_batch

def test():
    locs = fetch_phc_locations()[:50]
    print(f"Testing live Open-Meteo weather fetch for {len(locs)} locations...")
    results = fetch_weather_batch(locs)
    print(f"Successfully fetched live weather for {len(results)} locations!")
    for k in list(results.keys())[:5]:
        print(f"Loc ID {k}: Live Temp = {results[k][0]}°C, 48h Temp Delta = {results[k][1]}°C")

if __name__ == "__main__":
    test()
