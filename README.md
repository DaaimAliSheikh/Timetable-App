## Load the json file into the environment variable

# PREVIOUSLY WHEN USING GOOGLE SERVICE ACCOUNT(BUT THEN FAST MANAGEMENT MADE THE TIMETABLE GOOGLE SHEET ACCEESSIBLE ONLY FOR @nu.edu.pk domains)

export GOOGLE_SHEETS_CREDENTIALS=$(jq -c . google-sheets-key.json)

# NOW USING GOOGLE OAUTH FROM THE k224363@nu.edu.pk account automated through n8n instance deployed on render, so no need to set the above env variable
