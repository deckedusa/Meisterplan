import os
from dotenv import load_dotenv

load_dotenv()  # loads .env file into environment

MP_TOKEN = os.getenv("MP_TOKEN")
MP_URL = os.getenv("MP_URL")

print("MP_Token:", MP_TOKEN)