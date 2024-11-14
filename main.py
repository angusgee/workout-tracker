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
from supabase import create_client

# Load environment variables
load_dotenv()

# Constants for Google APIs and configurations
FOLDER_ID = os.getenv('GOOGLE_FOLDER_ID')
SPREADSHEET_ID = os.getenv('GOOGLE_SPREADSHEET_ID')
KEYWORDS = ["PULL", "PUSH", "FULL BODY", "LEGS", "A", "B", "A day", "B day", "UPPER", "LOWER"]
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(
    SUPABASE_URL, 
    SUPABASE_KEY,
)

# Initialize and return Google API clients
def setup_google_apis():
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

# Extract date and workout type from filename
def parse_filename(filename):
    print(f"  Attempting to parse: {filename}")
    
    workout_type = None
    for keyword in KEYWORDS:
        if keyword in filename:
            workout_type = keyword
            break
    
    if not workout_type:
        print("  No valid workout type found")
        return None, None
    
    date_pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\b|(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\b\s+(\d{1,2})(?:st|nd|rd|th)?'
    date_match = re.search(date_pattern, filename)
    
    try:
        groups = date_match.groups()
        if groups[0]:
            day, month = groups[0], groups[1]
        else:
            month, day = groups[2], groups[3]
            
        year = datetime.now().year
        try:
            date_obj = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
        except ValueError:
            date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
        
        return date_obj, workout_type
        
    except (ValueError, AttributeError) as e:
        print(f"  Error parsing date: {e}")
        return None, None

def insert_into_supabase(date, workout_type, content):
    try:
        # Check for existing workout on the same date
        existing_workout = supabase.table('Workouts_2024') \
            .select('*') \
            .eq('date', date.isoformat()) \
            .execute()
        
        if existing_workout.data:
            print(f"  Skipping: Workout already exists for {date.isoformat()}")
            return False
            
        # If no existing workout, proceed with insert
        data = {
            'date': date.isoformat(),
            'workout_type': workout_type,
            'notes': content
        }
        print(f"  Attempting to insert data: {data}")
        result = supabase.table('Workouts_2024').insert(data).execute()
        print(f"  Insert result: {result}")
        print("  Successfully inserted into Supabase")
        return True
    except Exception as e:
        print(f"  Error inserting into Supabase: {str(e)}")
        print(f"  Error type: {type(e)}")
        raise

# Check the folder for files and process them
def check_folder(drive_service, sheet):
    try:
        print("\nChecking folder for files...")
        print(f"Using folder ID: {FOLDER_ID}")
        
        file_list = []
        page_token = None
        files_processed = 0
        workouts_added = 0
        
        while True:
            response = drive_service.files().list(
                q=f"'{FOLDER_ID}' in parents and mimeType contains 'text'",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token
            ).execute()
            
            file_list.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            
            if not page_token:
                break
        
        print(f"Found {len(file_list)} files in folder:")
        
        for file in file_list:
            files_processed += 1
            print(f"\nProcessing file: {file['name']}")
            date, workout_type = parse_filename(file['name'])
            
            if date and workout_type:
                print(f"  Parsed date: {date}, workout type: {workout_type}")
                print("  Downloading file content...")
                request = drive_service.files().get_media(fileId=file['id'])
                file_data = io.BytesIO()
                downloader = MediaIoBaseDownload(file_data, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                content = file_data.getvalue().decode("utf-8")
                print("  Successfully downloaded content")
                
                # Insert into Supabase and increment counter if successful
                if insert_into_supabase(date, workout_type, content):
                    workouts_added += 1
            else:
                print(f"  Skipping: Not a workout note")
        
        print(f"\nSummary: Processed {files_processed} files, added {workouts_added} workouts to database")
            
    except Exception as e:
        print(f"Error processing files: {str(e)}")
        raise
    
if __name__ == "__main__":
    drive_service, sheet = setup_google_apis()
    check_folder(drive_service, sheet)
