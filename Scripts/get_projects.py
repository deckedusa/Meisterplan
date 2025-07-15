import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# load API token and variables from .env file
load_dotenv()  
MP_TOKEN = os.getenv("MP_TOKEN")
MP_URL = os.getenv("MP_URL")
   
# validate environment variables
if not MP_URL or not MP_TOKEN:
    print("Missing MP_URL or MP_TOKEN in .env")
    exit()

# build out headers
headers = {
    "Authorization": f"Bearer {MP_TOKEN}",
    "Accept": "application/json"
}

# Output file path with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_filename = f"meisterplan_projects_{timestamp}.xlsx"
output_filepath = os.path.join("data", output_filename)

# Pull all projects
def fetch_projects():
    all_projects = []

    # Set up API endpoint
    url = f"{MP_URL}/projects?startDate=2024-01-01&finishDate=2030-12-31"
    # scenario_id = "ec8dd97e-d9dd-4264-ad13-d14f7687924b"
    # url = f"{MP_URL}/scenarios/{scenario_id}/projects?page[limit]=1000"

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch data: {response.status_code}")
            print(response.text)
            break

        data = response.json()
        items = data.get("items", [])
        all_projects.extend(items)

        # Get the next page URL, if available
        url = data.get("meta", {}).get("next")
        if url and not url.startswith("http"):
            url = MP_URL + url
    
    project_ids = [p.get('projectId') for p in all_projects]
    print(f"Unique Project IDs Pulled: {len(set(project_ids))}")
    
    return all_projects

def save_to_excel(projects, filepath):
    if not projects:
        print("No project data to save.")
        return

    df = pd.DataFrame(projects)
    df.to_excel(filepath, index=False)
    print(f"Saved {len(df)} projects to {filepath}")


def main():
    projects = fetch_projects()
    save_to_excel(projects, output_filepath)
    
if __name__ == "__main__":
    main()