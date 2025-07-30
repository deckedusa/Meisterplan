import os
import requests
import pandas as pd
import gspread
import argparse
from gspread_dataframe import set_with_dataframe
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

scenarios_from_env = {}
for key, value in os.environ.items():
    if key.startswith("MP_SCENARIO_"):
        friendly_name = key.replace("MP_SCENARIO_", "").lower()
        scenarios_from_env[friendly_name] = value
if scenarios_from_env:
    print("Loaded scenario aliases from .env file:")
    for alias in scenarios_from_env:
        print(f"  - {alias}")

# build out headers
headers = {
    "Authorization": f"Bearer {MP_TOKEN}",
    "Accept": "application/json"
}

# Generic fetcher to support pagination
def fetch_paginated(endpoint, scenario_id=None):
    all_items = []
    url = f"{MP_URL}/{endpoint}"
    if scenario_id:
        if '?' in url:
            url += f"&scenario={scenario_id}"
        else:
            url += f"?scenario={scenario_id}"
    
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

def authenticate_gsheets():
    # Authenticates with Google Sheets API using credentials
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    CRED_DIR = os.path.join(BASE_DIR, "credentials")
    
    cred_path = os.path.join(CRED_DIR, "credentials.json")
    auth_path = os.path.join(CRED_DIR, "auth_user.json")

    try:
        gc = gspread.oauth(
            credentials_filename=cred_path,
            authorized_user_filename=auth_path
        )
        return gc
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None

def write_to_gsheets(gc, spreadsheet_name: str, dataframes: dict):
    """
    Writes multiple DataFrames to tabs in a Google Sheet, replacing existing data.
    
    Args:
        gc: Authenticated gspread client.
        spreadsheet_name (str): Name of the Google Sheet.
        dataframes (dict): Dictionary where keys are tab names and values are DataFrames.
    """
    try:
        # Open the spreadsheet (must exist beforehand and be shared with service account)
        sh = gc.open(spreadsheet_name)
    except gspread.SpreadsheetNotFound:
        print(f"Spreadsheet '{spreadsheet_name}' not found.")
        return

    for sheet_name, df in dataframes.items():
        try:
            # Try to open the worksheet
            worksheet = sh.worksheet(sheet_name)
            # Clear existing contents
            worksheet.clear()
        except gspread.WorksheetNotFound:
            # If it doesn't exist, create a new one
            worksheet = sh.add_worksheet(title=sheet_name, rows="1000", cols="26")

        # Replace NaN with empty strings and convert to strings
        values = [df.columns.tolist()] + df.fillna("").astype(str).values.tolist()
        worksheet.update(values)

     # Add timestamp sheet
    timestamp_sheet_name = "LastUpdated"
    timestamp_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        ts_sheet = sh.worksheet(timestamp_sheet_name)
        ts_sheet.clear()
    except gspread.WorksheetNotFound:
        ts_sheet = sh.add_worksheet(title=timestamp_sheet_name, rows="10", cols="2")
    
    ts_sheet.update([["Last Updated"], [timestamp_value]])
   
    print(f"Data written to Google Sheet '{spreadsheet_name}'")    

def write_to_excel(dataframes: dict, output_dir: str = "Data") -> tuple:
    """
    Writes multiple DataFrames to a timestamped Excel file.
    
    Args:
        dataframes (dict): Dictionary where keys are sheet names and values are DataFrames.
        output_dir (str): Directory where the Excel file will be saved.
        
    Returns:
        tuple: (output_filepath, output_filename)
    """
    # Base directory of the repo
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DATA_DIR = os.path.join(BASE_DIR, output_dir)    
    
    # Create output directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)

    # Build timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"meisterplan_full_export_{timestamp}.xlsx"
    output_filepath = os.path.join(DATA_DIR, output_filename)

    # Write DataFrames to Excel
    with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Excel file written to {output_filepath}")
    return output_filepath, output_filename

def main(output_mode="gsheets", scenario_id=None):
    if scenario_id:
        print(f"Fetching data from Scenario ID: {scenario_id}")
        spreadsheet = "Meisterplan Resource Map 2 - Scenario"
    else:
        print(f"Fetching data from Plan of Record")
        spreadsheet = "Meisterplan Resource Map 1 - PoR" 
    
    print("Fetching projects...")
    projects = fetch_paginated("projects?startDate=2024-01-01&finishDate=2030-12-31", scenario_id)
    print("Fetching allocations...")
    allocations = fetch_paginated("allocationSlices?startDate=2025-07-01&finishDate=2027-12-31&aggregation=MONTH", scenario_id)
    print("Fetching financial events...")
    financials = fetch_paginated("financials?startDate=2024-01-01&finishDate=2030-12-31", scenario_id)
    print("Fetching milestones...")
    milestones = fetch_paginated("milestones?startDate=2024-01-01&finishDate=2030-12-31", scenario_id)
    print("Fetching resources...")
    resources = fetch_paginated("resources", scenario_id)

    # Create dataframes
    df_projects = pd.DataFrame(projects)
    df_allocations = pd.DataFrame(allocations)
    df_financials = pd.DataFrame(financials)
    df_milestones = pd.DataFrame(milestones)
    df_resources = pd.DataFrame(resources)

    dataframes = {
        "Projects": df_projects,
        "Allocations": df_allocations,
        "Financials": df_financials,
        "Milestones": df_milestones,
        "Resources": df_resources
    }
    
    # THIS BLOCK WRITES TO EXCEL
    if output_mode in ("excel", "both"):
        excel_path, excel_filename = write_to_excel(dataframes)
    
    # THIS BLOCK WRITES TO GOOGLE SHEETS
    if output_mode in ("gsheets", "both"):
        gc = authenticate_gsheets()
        if not gc:
            return
        write_to_gsheets(gc, spreadsheet, dataframes)

if __name__ == "__main__":
    # Set up a more robust command-line argument parser
    parser = argparse.ArgumentParser(
        description="Fetch data from Meisterplan and export to Excel or Google Sheets. Can specify a scenario."
    )
    parser.add_argument(
        "-m", "--output-mode", 
        choices=["gsheets", "excel", "both"], 
        default="gsheets", 
        help="Specify the output destination (default: gsheets)."
    )
    parser.add_argument(
        "-s", "--scenario-id", 
        help="The alias (from .env file) or direct ID of the Meisterplan scenario. If omitted, fetches the Plan of Record."
    )
    args = parser.parse_args()

    # Call the main function with the parsed arguments
    main(output_mode=args.output_mode, scenario_id=args.scenario_id)