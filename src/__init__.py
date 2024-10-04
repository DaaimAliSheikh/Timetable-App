from math import e
from tracemalloc import start
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build  # type: ignore
from google.oauth2 import service_account
from fastapi.staticfiles import StaticFiles
import os
import json
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = './google-sheets-key.json'
SPREADSHEET_ID = '1la-JszZSkQ0RtAlrKzFMUwe1rztryQGrBphrJF8Pm6Y'
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1la-JszZSkQ0RtAlrKzFMUwe1rztryQGrBphrJF8Pm6Y/edit?gid=424654452#gid=424654452"

default_section = "BCS-5G"
lab_hours = 3


# Load the credentials from the environment variable
google_sheets_credentials = os.getenv('GOOGLE_SHEETS_CREDENTIALS') or ""

# Parse the JSON string into a dictionary
credentials_dict = json.loads(google_sheets_credentials)


credentials = service_account.Credentials.from_service_account_info(  # type: ignore
    credentials_dict, scopes=SCOPES)

service = build('sheets', 'v4', credentials=credentials)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your React app's URL
    allow_credentials=True,  # allow client to send cookies
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.get("/")
def index():
    return FileResponse("src/react-app/dist/index.html")


def convert_time(time_str: str):
    # Split the time string into start and end times
    start_time_str, _ = time_str.split('-')

    # Remove the colon only if it exists at the end
    # to counter typo in the google sheet
    if start_time_str.endswith(":"):
        start_time_str = start_time_str[:-1]  # Remove the last character

    # Check if it's AM or PM based on the hour
    hour, _ = map(int, start_time_str.split(':'))

    if hour == 12 or hour < 6:  # If hour is 12, it can only be PM
        start_time_str += ' PM'
    elif hour > 6 and hour < 12:  # If hour is less than 12, it must be AM
        start_time_str += ' AM'

    # Convert the time to a datetime object
    return datetime.strptime(start_time_str, "%I:%M %p")


def format_time(time_str: str):
    start_time_str, _ = time_str.split('-')
    time_str = time_str.replace("-", " - ")
    

    # Remove the colon only if it exists at the end
    # to counter typo in the google sheet
    if start_time_str.endswith(":"):
        start_time_str = start_time_str[:-1]  # Remove the last character

    # Check if it's AM or PM based on the hour
    hour, _ = map(int, start_time_str.split(':'))
    if hour == 12 or hour < 6:  # If hour is 12, it can only be PM
        time_str += ' PM'
    elif hour > 6 and hour < 12:  # If hour is less than 12, it must be AM
        time_str += ' AM'
    return time_str


def concatenate_time_ranges(range1: str, range2: str) -> str:
    # Split the time ranges by the dash to extract the start and end times
    start_time1, _ = range1.split('-')
    _, end_time2 = range2.split('-')

    # Concatenate the start time of the first range with the end time of the second range
    return f"{start_time1}-{end_time2}"


def get_sheet_data(valid_days: list[str], sheetId: str | None) -> list[list[str]]:
    try:
        ranges = [f"{day}!A1:Z1000" for day in valid_days]

        # Use batchGet to fetch data for all sheets in a single request
        result = service.spreadsheets().values().batchGet(
            spreadsheetId=sheetId or SPREADSHEET_ID, ranges=ranges).execute()

        # Extract the values for each day from the response
        sheet_data = []
        for day_data in result.get('valueRanges', []):
            # Get the 2D list for each sheet
            values = day_data.get('values', [])
            sheet_data.append(values)  # Append 2D list to the result
        return sheet_data
    except Exception:
        raise HTTPException(
            status_code=500, detail="Error retrieving sheet data")


@app.get("/timetable")
async def get_timetable(sheetId: str | None = None, section: str | None = None):
    valid_days = ['monday', 'tuesday ', 'wednesday ',
                  'thursday ', 'friday']

    time_table: Any = []
    free_classes: Any = []

    data = get_sheet_data(valid_days, sheetId)

    for i, day in enumerate(valid_days):

        # populating time table
        class_data: list[dict[str, str]] = []

        for row in data[i][4:]:
            for col in range(1, len(row)):
                if (section or default_section) in row[col]:
                    # if it's a lab make it 3 hours
                    if ("lab" in row[col].lower()):
                        class_data.append(
                            {"course": row[col].replace("\n", ""), "time": concatenate_time_ranges(data[i][2][col], data[i][2][col+lab_hours-1]),
                                "room": row[0]}
                        )
                    else:
                        class_data.append(
                            {"course": row[col].replace("\n", ""), "time": data[i][2][col],
                                "room": row[0]})
        class_data = sorted(
            class_data, key=lambda x: convert_time(x['time']))
        for class_info in class_data:
            class_info['time'] = format_time(class_info['time'])

        time_table.append(
            {"day": day.capitalize(), "class_data": class_data})

        # populating free classes
        class_data = []
        for row in data[i][4:]:
            for col in range(len(row)):
                if not row[col]:
                    # print(data[i][2][col], row[0])
                    class_data.append(
                        {"time": data[i][2][col], "room": row[0]})
        class_data = sorted(
            class_data, key=lambda x: convert_time(x['time']))
        for class_info in class_data:
            class_info['time'] = format_time(class_info['time'])
        free_classes.append(
            {"day": day.capitalize(), "class_data": class_data})

    global invalid_section
    invalid_section = True
    for day in time_table:
        if len(day['class_data']) > 0:
            invalid_section = False
            break
    if invalid_section:
        raise HTTPException(
            status_code=400, detail="Invalid section provided")

    return {"time_table": time_table, "free_classes": free_classes, "section": section or default_section, "url": SPREADSHEET_URL}


app.mount("/", StaticFiles(directory="src/react-app/dist/"), name="ui")
