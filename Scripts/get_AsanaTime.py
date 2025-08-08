import requests
import json
import os
import gspread
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load API token and variables from .env file
load_dotenv()
ASANA_TOKEN = os.getenv("Asana_TOKEN")
ASANA_URL = os.getenv("ASANA_URL")
ASANA_WORK_ID = os.getenv("Asana_WorkID")
ASANA_PORT_ID = os.getenv("Asana_PortID")
MP_TOKEN = os.getenv("MP_TOKEN")
MP_URL = os.getenv("MP_URL")

# validate environment variables
if not ASANA_TOKEN or not ASANA_URL or not ASANA_WORK_ID or not ASANA_PORT_ID:
    print("Missing Asana details in .env")
    exit()

scenarios_from_env = {}
for key, value in os.environ.items():
    if key.startswith("MP_SCENARIO_"):
        friendly_name = key.replace("MP_SCENARIO_", "").lower()
        scenarios_from_env[friendly_name] = value
if scenarios_from_env:
    print(f"Loaded {len(scenarios_from_env)} scenario aliases from .env file:")
    # for alias in scenarios_from_env:
    #     print(f"  - {alias}")

# Set up headers for API requests
asana_headers = {
    "Authorization": f"Bearer {ASANA_TOKEN}",
    "Accept": "application/json"
}
mp_headers = {
    "Authorization": f"Bearer {MP_TOKEN}",
    "Accept": "application/json"
}

CUSTOM_FIELDS_LIST = [
    "MP Mapping", 
    "Product Stage",
    "PD Proj Status"
]

# ASANA PROJECT PULLING FUNCTIONS - get_proj, get_milestones, get_cust fields, ready_for_sheet
def get_proj_in_port(portfolio_gid):
    # Fetch projects in a specific portfolio
    # Returns list of project dictionaries, empty if none found
    items_url = f"{ASANA_URL}/portfolios/{portfolio_gid}/items"
    params = {"opt_fields": "name, permalink_url, custom_fields"}

    print(f"Fetching projects in portfolio {portfolio_gid}...")
    try:
        response = requests.get(items_url, headers=asana_headers, params=params)
        response.raise_for_status()  # Raise an error for bad responses
        projects = response.json().get("data", [])
        print(f"Found {len(projects)} projects in portfolio {portfolio_gid}.")
        return projects
    
    except requests.RequestException as e:
        print(f"Error fetching projects: {e}")
        if e.response:
            print(f"Response: {e.response.text}")
        return []

def get_asana_milestones(workspace_gid, project_gid, project_name):
    # Fetches all milestones for a specific project from the Asana API.
    
    search_url = f"{ASANA_URL}/workspaces/{workspace_gid}/tasks/search"
    params = {
        "projects.any": project_gid,
        "resource_subtype": "milestone",
        "opt_fields": "name,due_on,completed,permalink_url",
    }    
    # print(f"\n- Querying for milestones in project: '{project_name}'...")
    
    try:
        response = requests.get(search_url, headers=asana_headers, params=params)
        response.raise_for_status()
        milestones = response.json().get("data", [])
        # print(f"  Found {len(milestones)} milestones.")
        return milestones
    except requests.exceptions.RequestException as e:
        print(f"  An error occurred while fetching milestones for project {project_gid}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"  Failed to decode the JSON response for project {project_gid}.")
        return []

def get_cust_fields(project, field_name):
    # Extracts Meisterplan key from project custom fields.
    for field in project.get('custom_fields', []):
        if field and field.get('name') == field_name:
            if field.get('enum_value'):
                return field.get('enum_value').get('name')
            return field.get('display_value')
    return None

def ready_asana_data_for_sheet(all_data, custom_field_names):
    header = ["Project Name", "Asana Project ID"]
    header.extend(custom_field_names)
    header.extend(["Milestone Name", "Due Date", "Status"])

    rows_for_sheet = [header]

    # Outer loop - looping through all projects in the all_data list
    for project in all_data:
        project_name = project.get('project_name')
        asana_id = project.get('project_gid')

        custom_field_values = []
        project_custom_fields = project.get('custom_fields', {})
        for field_name in custom_field_names:
            custom_field_values.append(project_custom_fields.get(field_name))
        
        project_row_part = [project_name, asana_id] + custom_field_values
        milestones = project.get('milestones', [])

        # if no milestones, still want 1x row for the project
        if not milestones:
            row = project_row_part + ["N/A", "N/A", "N/A"]
            rows_for_sheet.append(row)
            continue

        for milestone in milestones:
            milestone_name = milestone.get('name')
            due_date = milestone.get('due_on')
            status = "Completed" if milestone.get('completed') else "Incomplete"

            full_row = project_row_part + [milestone_name, due_date, status]
            rows_for_sheet.append(full_row)
    
    return rows_for_sheet

# MEISTERPLAN PULLING FUNCTIONS - fetch_paginated, ready_for_sheet
def fetch_paginated(endpoint, scenario_id=None):
    all_items = []
    url = f"{MP_URL}/{endpoint}"
    if scenario_id:
        if '?' in url:
            url += f"&scenario={scenario_id}"
        else:
            url += f"?scenario={scenario_id}"
    
    page_count = 1
    while url:
        # *** DEBUGGING: Print the URL we are about to call ***
        # print(f"DEBUG: Calling page {page_count}: {url}")

        response = requests.get(url, headers=mp_headers)
        if response.status_code != 200:
            print(f"Failed to fetch data from {endpoint}: {response.status_code}")
            print(response.text)
            break
        data = response.json()
        items = data if isinstance(data, list) else data.get("items", [])
        all_items.extend(items)
        
        url = data.get("meta", {}).get("next") if isinstance(data, dict) else None
        
        # *** DEBUGGING: Print the 'next' link we received from the API ***
        # if url:
        #     print(f"DEBUG: API returned next link: {url}")
        # else:
        #     print("DEBUG: No more pages.")

        if url and not url.startswith("http"):
            url = MP_URL + url
        
        page_count += 1
            
    return all_items

def ready_mp_data_for_sheet(mp_projects, mp_milestones):
    header = ["projectName", "projectKey", "projectStart", "projectFinish", "projectId", "scenarioProjectId", "cust_asana_id", "milestoneName", "milestoneDate", "projectPhaseName"]
    rows_for_sheet = [header]
    
    milestones_by_project = {}
    for ms in mp_milestones:
        scenario_project_id = ms.get('scenarioProjectId') or ms.get('projectId')
        if scenario_project_id not in milestones_by_project:
            milestones_by_project[scenario_project_id] = []
        milestones_by_project[scenario_project_id].append(ms)

    for project in mp_projects:
        project_name = project.get('projectName')
        project_key = project.get('projectKey')
        project_start = project.get('projectStart')
        project_finish = project.get('projectFinish')
        project_id = project.get('projectId')
        scenario_project_id = project.get('scenarioProjectId')
        cust_asana_id = project.get('cust_asana_id')

        project_milestones = milestones_by_project.get(scenario_project_id, [])

        if not project_milestones:
            rows_for_sheet.append([project_name, project_key, project_start, project_finish, project_id, scenario_project_id, cust_asana_id, "N/A", "N/A", "N/A"])
            continue

        for milestone in project_milestones:
            row = [
                project_name,
                project_key,
                project_start,
                project_finish,
                project_id,
                scenario_project_id,
                cust_asana_id,
                milestone.get('milestoneName'),
                milestone.get('milestoneDate'),
                milestone.get('projectPhaseName')
            ]
            rows_for_sheet.append(row)

    return rows_for_sheet

# Google sheets authetication & writing functions
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
    
def write_to_gsheets(gc, spreadsheet_name: str, sheet_name: str, rows_to_write: list):
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

    # Writing main data to spreadsheet
    try:
        worksheet = sh.worksheet(sheet_name)
        worksheet.clear()
        worksheet.update(rows_to_write)

    except gspread.WorksheetNotFound:
        print(f"❌ ERROR: Worksheet '{sheet_name}' not found. Please create it first.")
    except Exception as e:
        print(f"An unexpected error occurred during writing: {e}")       

    # Writing Timestamp data to spreadsheet 
    try:
        timestamp_sheet_name = "LastUpdated"
        timestamp_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")        
        try:
            ts_sheet = sh.worksheet(timestamp_sheet_name)
            ts_sheet.clear()
        except gspread.WorksheetNotFound:
            ts_sheet = sh.add_worksheet(title=timestamp_sheet_name, rows="10", cols="2")
        ts_sheet.update([["Last Updated"], [timestamp_value]])
    except gspread.WorksheetNotFound:
        print(f"❌ ERROR: Worksheet '{sheet_name}' not found. Please create it first.")
    except Exception as e:
        print(f"An unexpected error occurred during writing: {e}")
   
    print(f"Data written to Google Sheet '{spreadsheet_name}'")  

# Main script definition
def main(scenario_id=None):
    gc = authenticate_gsheets()
    if not gc:
        print("Google sheets authentication failed!")
        return
    
    if not all([ASANA_TOKEN, ASANA_URL, ASANA_WORK_ID, ASANA_PORT_ID, MP_TOKEN, MP_URL]):
        print("Missing required environment variables.")
    else:
        # Asana Data fetch & write
        print("--- Starting Asana Data fetch ---")        
        projects = get_proj_in_port(ASANA_PORT_ID)
        
        if projects:
            all_data = []
            for project in projects:
                project_gid = project['gid']
                project_name = project['name']
                custom_fields_data = {}

                for field_name in CUSTOM_FIELDS_LIST:
                    field_value = get_cust_fields(project, field_name)
                    custom_fields_data[field_name] = field_value

                project_info = {
                    "project_gid": project_gid,
                    "project_name": project_name,
                    "custom_fields": custom_fields_data,
                    "milestones": []
                }

                milestones = get_asana_milestones(ASANA_WORK_ID, project_gid, project_name)
                if milestones:
                    project_info["milestones"] = milestones

                all_data.append(project_info)

            # Print the aggregated results
            if all_data:
                project_count = len(all_data)
                total_milestones = sum(len(p.get('milestones', [])) for p in all_data)
                print(f"✅ Successfully pulled data from {project_count} projects.")
                
                spreadsheet_rows = ready_asana_data_for_sheet(all_data, CUSTOM_FIELDS_LIST)
                write_to_gsheets(gc, "Asana - MP Mapping", "Asana Data", spreadsheet_rows)
  
            else:
                print("\nNo Asana data found for any projects within the portfolio.")            
        else:
            print("\nCould not fetch Asana projects. Please check your Portfolio ID and API permissions.")
        
        # Meisterplan Data fetch & write
        print("\n--- Starting Meisterplan Data Fetch ---")
        if scenario_id:
            print(f"Fetching data from Scenario ID: {scenario_id}")
        else:
            print(f"Fetching data from Plan of Record")
        
        mp_projects = fetch_paginated("projects?startDate=2024-01-01&finishDate=2030-12-31", scenario_id)
        mp_milestones = fetch_paginated("milestones?startDate=2024-01-01&finishDate=2030-12-31", scenario_id)
        if mp_projects and mp_milestones:
            mp_data = ready_mp_data_for_sheet(mp_projects, mp_milestones)
            write_to_gsheets(gc, "Asana - MP Mapping", "MP Data", mp_data)
        else:
            print("\nCould not fetch Meisterplan projects. Please check your Portfolio ID and API permissions.")

# Main script execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch data from Meisterplan and Asana.")
    parser.add_argument("-s", "--scenario-id", help="Alias (from .env) or direct ID of the Meisterplan scenario.")
    args = parser.parse_args()

    scenario_input = args.scenario_id
    final_scenario_id = None

    if scenario_input:
        if scenario_input in scenarios_from_env:
            final_scenario_id = scenarios_from_env[scenario_input]
            print(f"Found alias '{scenario_input}'. Using Scenario ID: {final_scenario_id}")
        else:
            final_scenario_id = scenario_input
    
    main(scenario_id=final_scenario_id)