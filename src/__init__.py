import os
import json
from typing import Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime


load_dotenv()
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
APP_SECRET = os.getenv("APP_SECRET_KEY")
ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN")

if not all([CLIENT_ID, CLIENT_SECRET, APP_SECRET, ALLOWED_DOMAIN]):
    raise RuntimeError("Missing required environment variables")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=APP_SECRET or "abcd")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Replace your Flow logic with Authlib ---
oauth = OAuth()
CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
oauth.register(
    name="google",
    server_metadata_url=CONF_URL,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    client_kwargs={
        "scope": "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/spreadsheets.readonly"
    }
)

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


def get_sheet_data(sheetId: str | None, creds: Credentials) -> list[list[str]]:

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


@app.get("/login")
async def login(request: Request):
    # Redirect the user to Google’s consent page; state is kept in session
    redirect_uri = request.url_for("auth")
    if not oauth.google:
        raise HTTPException(400, "OAuth not configured")
    return await oauth.google.authorize_redirect(request, redirect_uri, prompt="select_account")


@app.get("/validate")
async def validate(request: Request):
    token = request.session.get("token")
    if not token or not oauth.google:
        raise HTTPException(
            401, f"Not authorized. Try login with an {ALLOWED_DOMAIN} email")
    try:
        creds = Credentials(
            token=token["access_token"],
            refresh_token=token.get("refresh_token"),
            # ✔️ correct
            token_uri=oauth.google.server_metadata["token_endpoint"],
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=oauth.google.client_kwargs["scope"].split()
        )
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f'Error retrieving credentials, perhaps try login with an {ALLOWED_DOMAIN} email')


@app.get("/auth")
async def auth(request: Request):
    if not oauth.google:
        raise HTTPException(400, "OAuth not configured")
    try:
        # Exchange code for tokens
        token = await oauth.google.authorize_access_token(request)
        # Authlib automatically populated token['userinfo'] if id_token was present
        user = token.get("userinfo")

        # Fallback: call the userinfo endpoint manually
        if not user:
            resp = await oauth.google.get("userinfo", token=token)
            resp.raise_for_status()
            user = resp.json()

        # Now enforce your email check
        email = user.get("email", "").lower()
        if not email.endswith(ALLOWED_DOMAIN):
            return RedirectResponse(
                url=f"/?error=unauthorized_domain"
            )

        # Store tokens in session (refresh_token included on first consent)
        request.session["token"] = token
        # Redirect back to your UI

        return RedirectResponse(url="/")

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=403, detail=f'Authorization failed.')
        # Handle error


@app.post("/timetable")
async def get_timetable(request: Request, sheetId: str = DEFAULT_SHEET_ID, json_data: dict = Body()):

    token = request.session.get("token")
    if not token or not oauth.google:
        raise HTTPException(
            401, f"Not authorized. Try login with an {ALLOWED_DOMAIN} email")

    # Build Google Credentials from the session token
    try:
        creds = Credentials(
            token=token["access_token"],
            refresh_token=token.get("refresh_token"),
            # ✔️ correct
            token_uri=oauth.google.server_metadata["token_endpoint"],
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=oauth.google.client_kwargs["scope"].split()
        )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=401, detail=f'Error retrieving credentials, perhaps try login with an {ALLOWED_DOMAIN} email')

    sections = json_data.get(
        'sections', DEFAULT_SECTIONS)
    sections = sections if len(sections) > 0 else DEFAULT_SECTIONS
    time_table: Any = []
    free_classes: Any = []

    data = get_sheet_data(sheetId, creds)
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


# app.mount("/static", StaticFiles(directory="src/react-app/dist"), name="static")

# app.mount("/static", StaticFiles(directory="src/react-app/dist"), name="static")

# # ─── 5) SPA Catch‑All ─────────────────────────────────────────────────────


# @app.get("/{full_path:path}")
# async def serve_spa(request: Request, full_path: str):
#     """
#     All unmatched GETs hit here.
#     If no session token, redirect to /login.
#     Otherwise serve the React index.html.
#     """
#     if request.session.get("token") is None:
#         return RedirectResponse("/login")
#     # serve the SPA entrypoint
#     return FileResponse("src/react-app/dist/index.html")
app.mount(
    "/",
    StaticFiles(directory="src/react-app/dist", html=True),
    name="ui"
)
