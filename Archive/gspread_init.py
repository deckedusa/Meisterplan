# Another old test code for trying to authenticate with Google Sheets

from gsheets import Sheets
import gspread
import os
from dotenv import load_dotenv
import pandas as pd

def gspreadoauth():
    """Authenticate with Google Sheets API using gspread."""
    # use os.path to take a copied raw path string and properly handle it

    path_to_json = os.path.join(r"C:\Users\spencer\Documents\GitHub\Meisterplan\Credentials", 'credentials.json')
    path_to_auth_user = os.path.join(r"CC:\Users\spencer\Documents\GitHub\Meisterplan\Credentials", 'auth_user.json')
   

    try:
        # Load credentials from the JSON file
        gc = gspread.oauth(
            credentials_filename=path_to_json,
            authorized_user_filename=path_to_auth_user
        )
        return gc
    
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None
 