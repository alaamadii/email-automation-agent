import os
import base64
import google.genai as genai
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
# constants for google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

def authenticate_google():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    gmail_service = build('gmail', 'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    return gmail_service, sheets_service

def extract_email_info(payload, body):
    """Extract email information from headers and body without Gemini"""
    headers = payload.get('headers', [])
    
    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
    
    # Extract first 100 chars of email as summary
    summary = body[:100] if body else "No content"
    
    return [sender, subject, date, summary]

def main():
    gmail, sheets = authenticate_google()
    results = gmail.users().messages().list(userId='me', q='is:unread', maxResults=3).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No new emails found")
        return

    for message in messages:
        msg = gmail.users().messages().get(userId='me', id=message['id']).execute()
        
        body = "" 
        payload = msg['payload']
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        
        print("Processing email.....")
        data_row = extract_email_info(payload, body)
        
        # write to Google Sheets
        sheets.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Sheet1!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [data_row]}
        ).execute()
    
    print("Messages processed and data written to Google Sheets successfully!")

if __name__ == '__main__':
    main()