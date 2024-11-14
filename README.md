# Workout Tracker

Automated workout tracker for Google Drive.

## User Story

As a gym user, I take a lot of notes on my phone during workouts. I wanted to be able to upload these to Google Drive and have them automatically parsed and stored in a database.

## How it works

1. Create a Google Cloud project and enable the Google Drive API
2. Create a service account and download the credentials as `credentials.json`
3. Create a `.env` file in the root directory with the following variables:

    ```
    GOOGLE_FOLDER_ID=your_folder_id
    SUPABASE_URL=your_supabase_url
    SUPABASE_KEY=your_supabase_key
    ```

    - `GOOGLE_FOLDER_ID`: The ID of the Google Drive folder containing your workout notes
    - `SUPABASE_URL`: Your Supabase project URL
    - `SUPABASE_KEY`: Your Supabase project API key

4. Save your workout notes in Google Drive with the workout type in the filename (e.g., "15th January PUSH ", "18th February LEGS" )
5. Run the script. It will:
    - Parse the filename to extract the date and workout type
    - Download the workout notes content
    - Store all information in your Supabase database
