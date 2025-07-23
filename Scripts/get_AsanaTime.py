import requests
import json
import os
from dotenv import load_dotenv

# Load API token and variables from .env file
load_dotenv()
ASANA_TOKEN = os.getenv("Asana_TOKEN")
ASANA_URL = os.getenv("ASANA_URL")
ASANA_WORK_ID = os.getenv("Asana_WorkID")
ASANA_PORT_ID = os.getenv("Asana_PortID")

# validate environment variables
if not ASANA_TOKEN or not ASANA_URL or not ASANA_WORK_ID or not ASANA_PORT_ID:
    print("Missing Asana details in .env")
    exit()

# Set up headers for Asana API requests
headers = {
    "Authorization": f"Bearer {ASANA_TOKEN}",
    "Accept": "application/json"
}

def get_proj_in_port(portfolio_gid):
    # Fetch projects in a specific portfolio
    # Returns list of project dictionaries, empty if none found
    items_url = f"{ASANA_URL}/portfolios/{portfolio_gid}/items"
    params = {"opt_fields": "name, permalink_url, custom_fields"}

    print(f"Fetching projects in portfolio {portfolio_gid}...")
    try:
        response = requests.get(items_url, headers=headers, params=params)
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
        response = requests.get(search_url, headers=headers, params=params)
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

def get_MP_key(project):
    # Extracts Meisterplan key from project custom fields.
    for field in project.get('custom_fields', []):
        if field and field.get('name') == "MP Mapping":
            return field.get('text_value')
    return None

# Main script execution
if __name__ == "__main__":
    if not all([ASANA_TOKEN, ASANA_URL, ASANA_WORK_ID, ASANA_PORT_ID]):
        print("Missing required environment variables.")
    else:
        projects = get_proj_in_port(ASANA_PORT_ID)

        if projects:
            all_data= []
            for project in projects:
                project_gid = project['gid']
                project_name = project['name']
                project_MP_key = get_MP_key(project)

                project_info = {
                    "project_gid": project_gid,
                    "project_name": project_name,
                    "MP_key": project_MP_key,
                    "milestones": []
                }

                milestones = get_asana_milestones(ASANA_WORK_ID, project_gid, project_name)
                if milestones:
                    project_info["milestones"] = milestones
                
                all_data.append(project_info)

            # Print the aggregated results
            print("\n--- Data fetch summary ---")
            if all_data:
                project_count = len(all_data)
                total_milestones = sum(len(p.get('milestones', [])) for p in all_data)
                print(f"✅ Successfully pulled data from {project_count} projects.")
                print(f"✅ Found a total of {total_milestones} milestones across all projects.")
            else:
                print("\nNo data found for any projects within the portfolio.")            
        else:
            print("\nCould not fetch projects. Please check your Portfolio ID and API permissions.")