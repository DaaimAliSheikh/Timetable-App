## Load the json file into the environment variable

export GOOGLE_SHEETS_CREDENTIALS=$(jq -c . google-sheets-key.json)
