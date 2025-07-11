import os
import requests
from dotenv import load_dotenv

# load API token and base URL from .env file
load_dotenv()  # loads .env file into environment

MP_TOKEN = os.getenv("MP_TOKEN")
MP_URL = os.getenv("MP_URL")
   
headers = {
    "Authorization": f"Bearer {MP_TOKEN}",
    "Accept": "application/json",
}

url = f"{MP_URL}/workspaces"
response = requests.get(url, headers=headers)
print(response.status_code)
print(response.text)


# Pull all projects
def fetch_projects():
    print("URL:", url)
    print("Headers:", headers)
    response = requests.get(url, headers=headers)

    if response.ok:
        try:
            return response.json()
        except ValueError:
            print("Could not parse JSON response")
            print("Response text:", response.text)
            return []
    else:
        print("Request failed")
        print("Status code:", response.status_code)
        print("Response text:", response.text)
        return []

def main():
    

   projects = fetch_projects()
   print(f"Found {len(projects)} projects:\n")

   for proj in projects:
      print(f"- ID: {proj['id']} | Name: {proj['name']} | Start: {proj['startDate']}")

if __name__ == "__main__":
    main()