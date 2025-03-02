from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Any
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
import os
import httpx

# Load environment variables from .env file
load_dotenv()

TIMETABLE_API_URL = os.getenv("TIMETABLE_API_URL") or ""
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1fOKzJfMlgU1ZTrpPhf065Im0pk0sdV87uu73uyJmphw/edit?gid=1909094994#gid=1909094994"

#Extracted from above, not done programmatically through regex because if google decides to change its URL structure then this code will break
DEFAULT_SHEET_ID = "1fOKzJfMlgU1ZTrpPhf065Im0pk0sdV87uu73uyJmphw" 
DEFAULT_SECTIONS = ["BCS-6G"]

#The spaces(whitespaces) after certain days ie: 'tuesday ' is important as it is the the way it is written in the google sheet
SHEET_NAMES = ['MONDAY', 'TUESDAY ', 'WEDNESDAY',
               'THURSDAY', 'FRIDAY']
LAB_HEADING_ROW = 46  # ignore this heading row as it has no classes
FRIDAY_LAB_HEADING_ROW = 47  # ignore this heading row as it has no classes(friday has this heading on a differnet row number)
LAB_CELL_SIZE = 3 #number of cells a LAB session occupies horizontally


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


def get_sheet_data(sheetId: str | None) -> list[list[str]]:
    try:
        response = httpx.get(TIMETABLE_API_URL + (sheetId or ""), timeout=None)
        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"Request failed with status code {response.status_code}: {response.text}",
                request=response.request,
                response=response
            )
        json_data = response.json()
        grouped_data = defaultdict(list)
        for row in json_data:
            for key, value in row.items():
                if key in SHEET_NAMES:
                    row_values = [value] + \
                        [row.get(f"col_{i}", "") for i in range(2, 11)]
                    grouped_data[key].append(row_values)
        return list(grouped_data.values())
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500, detail="Error retrieving sheet data")


@app.post("/timetable")
async def get_timetable(sheetId: str = DEFAULT_SHEET_ID, json_data: dict = Body()):
    
    sections = json_data.get(
        'sections', DEFAULT_SECTIONS)
    sections = sections if len(sections) > 0 else DEFAULT_SECTIONS
    time_table: Any = []
    free_classes: Any = []

    data = get_sheet_data(sheetId)

    for i, day in enumerate(SHEET_NAMES):
        # populating time table
        class_data: list[dict[str, str]] = []

        for row in data[i][3:]:
            for col in range(1, len(row)):
                if any(section in row[col] for section in sections):
                    # if it's a lab, use the time range of three cells horizontally
                    if ("lab" in row[col].lower()):
                        class_data.append(
                            {"course": row[col], "time": concatenate_time_ranges(data[i][1][col], data[i][1][col+LAB_CELL_SIZE-1]),
                                "room": row[0]}
                        )
                    else:
                        class_data.append(
                            {"course": row[col], "time": data[i][1][col],
                                "room": row[0]})
        class_data = sorted(
            class_data, key=lambda x: convert_time(x['time']))
        for class_info in class_data:
            class_info['time'] = format_time(class_info['time'])

        time_table.append(
            {"day": day.capitalize(), "class_data": class_data})

        # populating free classes
        class_data = []
        for index, row in enumerate(data[i][3:]):

            if index == LAB_HEADING_ROW or (day == "FRIDAY" and index == FRIDAY_LAB_HEADING_ROW):  # ignore the LABS heading row as it contains no classes
                continue
            for col in range(len(row)):
                # checking for existence of timeslot by checking data[i][1][col] as some empty cells are out of bounds
                if not row[col] and data[i][1][col]:
                    # labs actually occupy only the first column of the three columns they seem to occupy in the timetable, rest two are empty
                    prev_col = col-1
                    prev_prev_col = col-2
                    if "lab" in row[prev_col].lower() and prev_col != 0:
                        continue
                    if prev_prev_col > -1 and "lab" in row[prev_prev_col].lower() and prev_col != 0:
                        continue
                    class_data.append(
                        {"time": data[i][1][col], "room": row[0]})
        class_data = sorted(
            class_data, key=lambda x: x['time'])
        for class_info in class_data:
            class_info['time'] = class_info['time']
        free_classes.append(
            {"day": day.capitalize(), "class_data": class_data})

    return {"time_table": time_table, "free_classes": free_classes, "sections": sections or DEFAULT_SECTIONS, "url": SPREADSHEET_URL}


app.mount("/", StaticFiles(directory="src/react-app/dist/"), name="ui")
