#! /usr/bin/env python3

import io
import re
import os
from datetime import datetime
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants for Google APIs and configurations
FOLDER_ID = os.getenv('GOOGLE_FOLDER_ID')
SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID')
KEYWORDS = ["PULL", "PUSH", "FULL BODY", "A", "B"]
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

def setup_google_apis():
    """Initialize and return Google API clients"""
    try:
        print("Setting up Google API clients...")
        creds = service_account.Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        print(f"Using service account: {creds.service_account_email}")
        
        drive_service = build('drive', 'v3', credentials=creds)
        sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
        print("Successfully set up Google API clients")
        
        return drive_service, sheet
        
    except Exception as e:
        print(f"Error setting up Google API clients: {str(e)}")
        raise

def parse_filename(filename):
    """Extract date and workout type from filenames like 'Sunday 3rd November PULL.txt'."""
    match = re.match(r"(\w+) (\d{1,2})(?:st|nd|rd|th) (\w+) (\w+)\.txt", filename)
    if match:
        day, date, month, workout_type = match.groups()
        return datetime.strptime(f"{date} {month} {datetime.now().year}", "%d %B %Y"), workout_type
    return None, None

def check_folder(drive_service, sheet):
    try:
        files = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType contains 'text'",
            fields="files(id, name, mimeType)",
            pageSize=10
        ).execute()
        
        file_list = files.get("files", [])
        
        for file in file_list:
            date, workout_type = parse_filename(file['name'])
            
            if date and workout_type:
                request = drive_service.files().get_media(fileId=file['id'])
                file_data = io.BytesIO()
                downloader = MediaIoBaseDownload(file_data, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                content = file_data.getvalue().decode("utf-8")
                
                row = [
                    date.strftime('%Y-%m-%d'),
                    workout_type,
                    content
                ]
                sheet.append_row(row)
                print(f"Added workout: {date.strftime('%Y-%m-%d')} - {workout_type}")
            
    except Exception as e:
        print(f"Error processing files: {str(e)}")
        raise

if __name__ == "__main__":
    drive_service, sheet = setup_google_apis()
    check_folder(drive_service, sheet)
