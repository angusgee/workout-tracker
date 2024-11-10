# Workout Tracker

Automated workout tracker for Google Drive.

## User Story

As a gym user, I take a lot of notes on my phone during workouts. I wanted to be able to upload these to Google Drive and have them automatically parsed and added to a spreadsheet.

## How it works

1. Create a Google Cloud project and enable the Google Drive and Google Sheets APIs
2. Create a service account and download the credentials as `credentials.json`
3. Create a `.env` file in the root directory with the following variables:
    ```
    GOOGLE_FOLDER_ID=your_folder_id
    GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
    ```
    - `GOOGLE_FOLDER_ID`: The ID of the Google Drive folder containing your workout notes
    - `GOOGLE_SPREADSHEET_ID`: The ID of the Google Spreadsheet where you want to store the data
4. Save your workout notes with the workout type in the filename.
5. Run the script. It will parse the filename and add the date and workout type to the spreadsheet.
6. The script will also download the workout notes and add them to the spreadsheet.
