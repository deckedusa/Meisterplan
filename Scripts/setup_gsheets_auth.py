import gspread
import os
import google.auth
import google.auth.transport.requests

def authenticate_and_save_token():
    creds_dir = os.path.join(os.path.dirname(__file__), '..', 'credentials')
    
    credentials_path = os.path.join(creds_dir, 'credentials.json')
    auth_user_path = os.path.join(creds_dir, 'auth_user.json')

    print("🔐 Launching browser for Google authentication...")

    try:
        gc = gspread.oauth(
            credentials_filename = credentials_path,
            authorized_user_filename = auth_user_path
        )
        # Confirm the user/account
        creds, _ = google.auth.load_credentials_from_file('credentials/auth_user.json')
        request = google.auth.transport.requests.Request()
        creds.refresh(request)
        print("✅ Authenticated Client ID:", creds._client_id)
        print("🔒 Access token valid?", creds.valid)
    except Exception as e:
        print(f"❌ Authentication failed: {e}")

if __name__ == "__main__":
    authenticate_and_save_token()