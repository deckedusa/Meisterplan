import gspread

gc = gspread.oauth(
    credentials_filename='credentials/credentials.json',
    authorized_user_filename='credentials/auth_user.json'
)

sh = gc.create("Test Sheet")
print("✅ Created sheet:", sh.url)