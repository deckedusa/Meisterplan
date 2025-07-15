# get_scenarios.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MP_URL = os.getenv("MP_URL")
MP_TOKEN = os.getenv("MP_TOKEN")

headers = {
    "Authorization": f"Bearer {MP_TOKEN}",
    "Accept": "application/json"
}

def fetch_scenarios():
    scenurl = f"{MP_URL}/scenarios"
    response = requests.get(scenurl, headers=headers)

    if response.ok:
        data = response.json()
        print("Scenarios:")
        for s in data.get("items", []):
            print(f"- {s['scenarioName']} (ID: {s['scenarioId']})")
    else:
        print("Error fetching scenarios:", response.status_code)
        print(response.text)

if __name__ == "__main__":
    fetch_scenarios()