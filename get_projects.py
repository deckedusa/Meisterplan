import os
import requests
from dotenv import load_dotenv

# load API token and variables from .env file
load_dotenv()  
MP_TOKEN = os.getenv("MP_TOKEN")
MP_URL = os.getenv("MP_URL")
   
# validate environment variables
if not MP_URL or not MP_TOKEN:
    print("Missing MP_URL or MP_TOKEN in .env")
    exit()

# build API endpoint
projurl = f"{MP_URL}/projects"

# build out headers
headers = {
    "Authorization": f"Bearer {MP_TOKEN}",
    "Accept": "application/json"
}

# Pull all projects
def fetch_projects():
    print("Request URL:", projurl)
    response = requests.get(projurl, headers=headers)
    print("Response status code:", response.status_code)

    if response.ok:
        try:
            data = response.json()
            # Check for standard API structure
            if isinstance(data, dict) and "items" in data:
                return data["items"]
            return data
        except ValueError:
            print("Could not decode JSON. Raw response:")
            print(response.text)
            return []
    else:
        print("Request failed.")
        print("Response text:")
        print(response.text)
        return []
 

def main():
    projects = fetch_projects()
    print(f"Found {len(projects)} projects.")
    print("First project preview:\n", projects[0])  # ← show raw data

    for proj in projects:
        print(f"- {proj.get('projectName')} (ID: {proj.get('projectId')})")

if __name__ == "__main__":
    main()