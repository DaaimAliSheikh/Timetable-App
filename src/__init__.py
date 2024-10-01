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

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = './google-sheets-key.json'
SPREADSHEET_ID = '1la-JszZSkQ0RtAlrKzFMUwe1rztryQGrBphrJF8Pm6Y'


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


def convert_time_to_sortable(time_str: str) -> tuple:
    # Split the time range (e.g., "09:00-09:55")
    start_time_str, end_time_str = time_str.split('-')

    # Convert the start time to a datetime object
    start_time = datetime.strptime(
        start_time_str, '%I:%M')  # %I for 12-hour format

    # Return a tuple with the start time for sorting
    return start_time.hour, start_time.minute


def get_sheet_data(valid_days: list[str]) -> list[list[str]]:
    try:
        ranges = [f"{day}!A1:Z1000" for day in valid_days]

        # Use batchGet to fetch data for all sheets in a single request
        result = service.spreadsheets().values().batchGet(
            spreadsheetId=SPREADSHEET_ID, ranges=ranges).execute()

        # Extract the values for each day from the response
        sheet_data = []
        for day_data in result.get('valueRanges', []):
            # Get the 2D list for each sheet
            values = day_data.get('values', [])
            sheet_data.append(values)  # Append 2D list to the result

        return sheet_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving sheet data: {str(e)}")


section = "BCS-5G"


@app.get("/timetable")
async def get_timetable():
    try:
        valid_days = ['monday', 'tuesday ', 'wednesday ',
                      'thursday ', 'friday']

        time_table: Any = []

        data = get_sheet_data(valid_days)

        for i, day in enumerate(valid_days):
            class_data: list[dict[str, str]] = []

            for row in data[i][4:]:
                for col in range(len(row)):
                    if section in row[col]:
                        class_data.append(
                            {"course": row[col].replace("\n", ""), "time": data[i][2][col],
                                "room": row[0]}
                        )
            # class_data.sort(
            #     key=lambda item: convert_time_to_sortable(item["time"]))
            time_table.append({"day": day, "class_data": class_data})
        return time_table
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/", StaticFiles(directory="src/react-app/dist/"), name="ui")
