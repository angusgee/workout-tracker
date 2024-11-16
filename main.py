#! /usr/bin/env python3

import io
import re
import os
import time
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv
from supabase import create_client
from functools import wraps

# Load environment variables
load_dotenv()

# Constants for Google APIs and configurations
FOLDER_ID = os.getenv('GOOGLE_FOLDER_ID')
KEYWORDS = ["PULL", "PUSH", "FULL BODY", "LEGS", "A", "B", "A day", "B day", "UPPER", "LOWER"]
SCOPES = ['https://www.googleapis.com/auth/drive']
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(
    SUPABASE_URL, 
    SUPABASE_KEY,
)

# Add timing decorator
def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Function '{func.__name__}' took {end - start:.2f} seconds to execute")
        return result
    return wrapper

# Initialize and return Google API clients
@timer
def setup_google_apis():
    try:
        print("Setting up Google API clients...")
        creds = service_account.Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        print(f"Using service account: {creds.service_account_email}")
        
        drive_service = build('drive', 'v3', credentials=creds)
        print("Successfully set up Google API clients")
        
        return drive_service
        
    except Exception as e:
        print(f"Error setting up Google API clients: {str(e)}")
        raise

# Extract date and workout type from filename
@timer
def parse_filename(filename):
    print(f"  Attempting to parse: {filename}")
    
    filename = filename.replace('Sept', 'Sep')
    
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

@timer
def get_list_of_files(drive_service):
        response = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType contains 'text'",
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        
        file_list = response.get('files', [])
        print(f"Found {len(file_list)} files in the folder:")
        
        for file in file_list:
            print(f"  - {file['name']}")
        return file_list

@timer
def check_filenames_for_keywords(file_list):
    valid_workouts = []
    for file in file_list:
        print(f"Processing: {file['name']}")
        result = parse_filename(file['name'])
        if result[0]: 
            valid_workouts.append((file, *result))
    
    print(f"Found {len(valid_workouts)} valid workouts:")
    for file, date, workout_type in valid_workouts:
        print(f"  - {date.strftime('%Y-%m-%d')}: {workout_type}")
    return valid_workouts

@timer
def get_date_list_from_db():
    try:
        print("Retrieving dates from Supabase...")
        result = supabase.table('Workouts_2024').select('date').execute()
        dates = [datetime.fromisoformat(date['date']) for date in result.data]
        print(f"Retrieved {len(dates)} dates from Supabase:")
        for date in dates:
            print(f"  - {date.strftime('%Y-%m-%d')}")
        return dates
    except Exception as e:
        print(f"Error retrieving dates from Supabase: {str(e)}")
        raise
    
@timer
def identify_new_workouts_to_be_added(existing_dates, valid_workouts):
    try:
        # Filter out workouts that already exist in DB
        new_workouts = list(filter(
            lambda workout: workout[1].date() not in map(lambda d: d.date(), existing_dates),
            valid_workouts
        ))

        print(f"\nFound {len(new_workouts)} new workouts to add:")
        for file, date, workout_type in new_workouts:
            print(f"  - {date.strftime('%Y-%m-%d')}: {workout_type}")

        return new_workouts

    except Exception as e:
        print(f"Error identifying new workouts: {str(e)}")
        raise

@timer
def add_new_workouts_to_db(drive_service, new_workouts):
    try:
        workouts_added = 0
        print("\nAdding new workouts to database...")

        for file, date, workout_type in new_workouts:
            print(f"\nProcessing: {date.strftime('%Y-%m-%d')} - {workout_type}")
            
            # Download file content
            print("  Downloading file content...")
            request = drive_service.files().get_media(fileId=file['id'])
            file_data = io.BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)
            
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            content = file_data.getvalue().decode("utf-8")
            print("  Successfully downloaded content")

            # Insert into database
            data = {
                'date': date.isoformat(),
                'workout_type': workout_type,
                'notes': content
            }
            
            print(f"  Inserting workout into database...")
            result = supabase.table('Workouts_2024').insert(data).execute()
            print("  Successfully inserted into database")
            workouts_added += 1

        print(f"\nSummary: Added {workouts_added} new workouts to database")
        print(f"Current time: {datetime.now().strftime('%H:%M:%S')}")
        return workouts_added

    except Exception as e:
        print(f"Error adding new workouts: {str(e)}")
        raise

if __name__ == "__main__":
    start_time = time.time()
    
    drive_service = setup_google_apis()
    file_list = get_list_of_files(drive_service)
    valid_workouts = check_filenames_for_keywords(file_list)
    date_list = get_date_list_from_db()
    new_workouts = identify_new_workouts_to_be_added(date_list, valid_workouts)
    add_new_workouts_to_db(drive_service, new_workouts)
    
    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")
