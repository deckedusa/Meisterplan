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
output_filename = f"meisterplan_full_export_{timestamp}.xlsx"
output_filepath = os.path.join("data", output_filename)

# Generic fetcher to support pagination
def fetch_paginated(endpoint):
    all_items = []
    url = f"{MP_URL}/{endpoint}"
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch data from {endpoint}: {response.status_code}")
            print(response.text)
            break
        data = response.json()
        items = data.get("items", [])
        all_items.extend(items)
        url = data.get("meta", {}).get("next")
        if url and not url.startswith("http"):
            url = MP_URL + url
    return all_items

def main():
    print("Fetching projects...")
    projects = fetch_paginated("projects?startDate=2024-01-01&finishDate=2030-12-31")
    print("Fetching allocations...")
    allocations = fetch_paginated("allocationSlices?startDate=2025-07-01&finishDate=2027-12-31&aggregation=MONTH")
    print("Fetching financial events...")
    financials = fetch_paginated("financials?startDate=2024-01-01&finishDate=2030-12-31")
    print("Fetching milestones...")
    milestones = fetch_paginated("milestones?startDate=2024-01-01&finishDate=2030-12-31")

    # Create dataframes
    df_projects = pd.DataFrame(projects)
    df_allocations = pd.DataFrame(allocations)
    df_financials = pd.DataFrame(financials)
    df_milestones = pd.DataFrame(milestones)

    # Write to Excel
    with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
        df_projects.to_excel(writer, sheet_name='Projects', index=False)
        df_allocations.to_excel(writer, sheet_name='Allocations', index=False)
        df_financials.to_excel(writer, sheet_name='FinancialEvents', index=False)
        df_milestones.to_excel(writer, sheet_name='Milestones', index=False)

    print(f"Exported all data to {output_filepath}")

if __name__ == "__main__":
    main()
