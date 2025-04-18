from contextlib import asynccontextmanager
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import Any
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
import os
import httpx
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Load environment variables from .env file
load_dotenv()
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
ALLOWED_EMAIL = os.getenv("ALLOWED_EMAIL")

SCOPES = [
    "openid",                                 # for ID token
    # to read the user’s email
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]
TOKEN_STORE = "token.json"
oauth2_flow = None     # holds the Flow during the auth handoff
creds: Credentials | None = None

TIMETABLE_API_URL = os.getenv("TIMETABLE_API_URL") or ""
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1fOKzJfMlgU1ZTrpPhf065Im0pk0sdV87uu73uyJmphw/edit?gid=1909094994#gid=1909094994"

# Extracted from above, not done programmatically through regex because if google decides to change its URL structure then this code will break
DEFAULT_SHEET_ID = "1fOKzJfMlgU1ZTrpPhf065Im0pk0sdV87uu73uyJmphw"
DEFAULT_SECTIONS = ["BCS-6G"]

# The spaces(whitespaces) after certain days ie: 'tuesday ' is important as it is the the way it is written in the google sheet
SHEET_NAMES = ['MONDAY', 'TUESDAY ', 'WEDNESDAY ',
               'THURSDAY', 'FRIDAY']
LAB_HEADING_ROW = 46  # ignore this heading row as it has no classes
# ignore this heading row as it has no classes(friday has this heading on a differnet row number)
FRIDAY_LAB_HEADING_ROW = 47
LAB_CELL_SIZE = 3  # number of cells a LAB session occupies horizontally


def save_refresh_token(refresh_token: str):
    with open(TOKEN_STORE, "w") as f:
        json.dump({"refresh_token": refresh_token}, f)


def generate_credentials(refresh_token: str) -> Credentials:
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES
    )


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
        service = build("sheets", "v4", credentials=creds)

        data = []  # this will be List[List[List[str]]]

        for raw_name in SHEET_NAMES:

            # 2) quote the sheet name in case it has spaces/special chars
            range_name = f"'{raw_name}'!A1:Z100"

            # 3) fetch values (returns a Python dict) :contentReference[oaicite:0]{index=0}
            result = (
                service
                .spreadsheets()
                .values()
                .get(spreadsheetId=sheetId, range=range_name)
                .execute()
            )

            # 4) extract rows (list of lists of strings)
            # each row is a list of cell‐value strings :contentReference[oaicite:1]{index=1}
            rows = result.get("values", [])

            # 5) append to our top‑level list
            data.append(rows)

        # now `data` is a list with one entry per sheet, each being its own rows list
        return data

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500, detail="Error retrieving sheet data")


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


@app.get("/login")
def login():
    """
    Step 1: Redirect *you* to Google’s OAuth consent screen.
    Only ALLOWED_EMAIL will be allowed in the callback.
    """

    global oauth2_flow
    client_config = {
        "web": {
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
        }
    }
    oauth2_flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = oauth2_flow.authorization_url(
        access_type="offline",          # request a one-time refresh token
        include_granted_scopes=False,  # keep any prior consents
        prompt="consent"               # force the consent dialog
    )
    return RedirectResponse(auth_url)


@app.get("/oauth2callback")
def oauth2callback(request: Request):
    """
    Step 2: Google redirects here with ?code=…
    We exchange it for tokens, verify the email, and save the refresh token.
    """
    global oauth2_flow, creds
    if oauth2_flow is None:
        raise HTTPException(400, "Start at /login first.")

    # Exchange code for tokens
    oauth2_flow.fetch_token(code=request.query_params["code"])
    temp_creds = oauth2_flow.credentials

    # Verify that *you* are the one authenticating
    resp = httpx.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {temp_creds.token}"}
    )
    resp.raise_for_status()
    user_info = resp.json()
    if user_info.get("email") != ALLOWED_EMAIL:
        raise HTTPException(403, "Unauthorized user")

    # Persist your one-time refresh token
    if not temp_creds.refresh_token:
        raise HTTPException(
            400, "No refresh token.")
    # Load into our global creds so /sheet-data works immediately
    creds = generate_credentials(temp_creds.refresh_token)
    oauth2_flow = None  # clear the flow

    return {"status": "authorized", "email": user_info["email"]}


@app.post("/timetable")
async def get_timetable(sheetId: str = DEFAULT_SHEET_ID, json_data: dict = Body()):
    if creds is None:
        raise HTTPException(
            401, f'Not authorized, please authorize at /login with {ALLOWED_EMAIL}')
    sections = json_data.get(
        'sections', DEFAULT_SECTIONS)
    sections = sections if len(sections) > 0 else DEFAULT_SECTIONS
    time_table: Any = []
    free_classes: Any = []

    data = get_sheet_data(sheetId)
    # print(data)
    # it's in the format:
    # [[['MONDAY'], ['Slots', '1', '2', '3', '4', '5', '6', '7', '8'], ['Venues/time', '08:00-8:55', '09:00-09:55', '10:00-10:55', '11:00-11:55', '12:00-12:55', '1:00-01:55', '02:00-02:55', '03:00-03:55'], ['CLASSROOMS'], ['E-1 Academic Block I (50)', 'SE BCS-6A\nHajra Ahmed', 'Data Science BCS-6A\nSania Urooj', 'TBW BCS-6A\nNazia Imam', 'DSci BCS-6B\nSania Urooj', 'SE BCS-6J\nRubab Manzar', 'AI BCS-6A\nDr. Fahad Sherwani'],

    for i, day in enumerate(SHEET_NAMES):
        # populating time table
        class_data: list[dict[str, str]] = []

        for row in data[i][4:]:
            for col in range(1, len(row)):
                if any(section in row[col] for section in sections):
                    # if it's a lab, use the time range of three cells horizontally
                    if ("lab" in row[col].lower()):
                        class_data.append(
                            {"course": row[col], "time": concatenate_time_ranges(data[i][2][col], data[i][2][col+LAB_CELL_SIZE-1]),
                                "room": row[0]}
                        )
                    else:
                        class_data.append(
                            {"course": row[col], "time": data[i][2][col],
                                "room": row[0]})
        class_data = sorted(
            class_data, key=lambda x: convert_time(x['time']))
        for class_info in class_data:
            class_info['time'] = format_time(class_info['time'])

        time_table.append(
            {"day": day.capitalize(), "class_data": class_data})

        # populating free classes
        class_data = []
        for index, row in enumerate(data[i][4:]):

            # ignore the LABS heading row as it contains no classes
            if index == LAB_HEADING_ROW or (day == "FRIDAY" and index == FRIDAY_LAB_HEADING_ROW):
                continue
            for col in range(len(row)):
                # checking for existence of timeslot by checking data[i][2][col] as some empty cells are out of bounds
                if not row[col] and data[i][2][col]:
                    # labs actually occupy only the first column of the three columns they seem to occupy in the timetable, rest two are empty
                    prev_col = col-1
                    prev_prev_col = col-2
                    if "lab" in row[prev_col].lower() and prev_col != 0:
                        continue
                    if prev_prev_col > -1 and "lab" in row[prev_prev_col].lower() and prev_col != 0:
                        continue
                    class_data.append(
                        {"time": data[i][2][col], "room": row[0]})
        class_data = sorted(
            class_data, key=lambda x: x['time'])
        for class_info in class_data:
            class_info['time'] = class_info['time']
        free_classes.append(
            {"day": day.capitalize(), "class_data": class_data})

    return {"time_table": time_table, "free_classes": free_classes, "sections": sections or DEFAULT_SECTIONS, "url": SPREADSHEET_URL}


app.mount("/", StaticFiles(directory="src/react-app/dist/"), name="ui")
