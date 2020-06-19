import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import csv

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


class Spreadsheet():
    
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
    
    @property
    def credentials(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'gsheets-credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return creds
          
    @property
    def service(self):
        return build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)
    
    def download_sheet_to_csv(self, sheet_name):
        folder = "gsheets-downloads"
        if not os.path.exists("gsheets-downloads"):
            os.mkdir(folder)

        result = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, 
                                                          range=sheet_name).execute()
        output_file = f'{folder}/{sheet_name.replace("/", "-")}.csv'

        with open(output_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(result.get('values'))

        f.close()

        print(f'Successfully downloaded {sheet_name}.csv')
        return output_file

