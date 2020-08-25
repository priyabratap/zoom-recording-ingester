import sys
import json
import jwt
import time
import logging
import requests
import aws_lambda_logging
from functools import wraps
from os import getenv as env
from dotenv import load_dotenv
from os.path import join, dirname, exists
from urllib.parse import urlparse
import csv
import itertools
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import boto3
# google sheets imports
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger()

load_dotenv(join(dirname(__file__), '../.env'))

LOG_LEVEL = env('DEBUG') and 'DEBUG' or 'INFO'
BOTO_LOG_LEVEL = env('BOTO_DEBUG') and 'DEBUG' or 'INFO'
ZOOM_API_BASE_URL = "https://api.zoom.us/v2/"
ZOOM_API_KEY = env("ZOOM_API_KEY")
ZOOM_API_SECRET = env("ZOOM_API_SECRET")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
GSHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
SCHEDULE_TABLE = env("CLASS_SCHEDULE_TABLE")
STACK_NAME = env("STACK_NAME")


class ZoomApiRequestError(Exception):
    pass


def setup_logging(handler_func):

    @wraps(handler_func)
    def wrapped_func(event, context):

        extra_info = {'aws_request_id': context.aws_request_id}
        aws_lambda_logging.setup(
            level=LOG_LEVEL,
            boto_level=BOTO_LOG_LEVEL,
            **extra_info
        )

        logger = logging.getLogger()

        logger.debug("{} invoked!".format(context.function_name))
        logger.debug({
            'event': event,
            'context': context.__dict__
        })

        try:
            retval = handler_func(event, context)
        except Exception:
            logger.exception("handler failed!")
            raise

        logger.debug("{} complete!".format(context.function_name))
        return retval

    wrapped_func.__name__ = handler_func.__name__
    return wrapped_func


def gen_token(key, secret, seconds_valid=60):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"iss": key, "exp": int(time.time() + seconds_valid)}
    return jwt.encode(payload, secret, headers=header)


def zoom_api_request(endpoint, key=ZOOM_API_KEY, secret=ZOOM_API_SECRET,
                     seconds_valid=60, ignore_failure=False, retries=3):
    required_params = [("endpoint", endpoint),
                       ("zoom api key", key),
                       ("zoom api secret", secret)]
    for name, param in required_params:
        if not param:
            raise Exception(
                "Call to zoom_api_request "
                "missing required param '{}'".format(name)
            )

    url = "{}{}".format(ZOOM_API_BASE_URL, endpoint)
    headers = {
        "Authorization": "Bearer {}"
        .format(gen_token(key, secret, seconds_valid).decode())
    }

    while True:
        try:
            r = requests.get(url, headers=headers)
            break
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ConnectTimeout) as e:
            if retries > 0:
                logger.warning("Connection Error: {}".format(e))
                retries -= 1
            else:
                logger.error("Connection Error: {}".format(e))
                raise ZoomApiRequestError(
                    "Error requesting {}: {}".format(url, e)
                )

    if not ignore_failure:
        r.raise_for_status()

    return r


class GSheetsToken():
    def __init__(self, in_lambda=False):
        self.creds = None
        self.load_token()
        if not self.creds:
            if in_lambda:
                raise Exception("Cannot find token.pickle file.")
            else:
                self.create_token()
        elif not self.creds.valid:
            self.refresh_token()

    def valid(self):
        return self.creds and self.creds.valid

    def load_token(self):
        # The file token.pickle stores the user's access and refresh tokens,
        # and is created automatically when the authorization flow completes
        # for the first time.
        if exists("token.pickle"):
            print("FOUND TOKEN PICKLE")
            logger.debug("Found token.pickle")
            with open("token.pickle", "rb") as token:
                self.creds = pickle.load(token)

    def create_token(self):
        print("prompt user to login to generate gsheets token")
        if not exists("credentials.json"):
            raise Exception("Missing required credentials.json file.")
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", [GSHEETS_SCOPE]
        )
        self.creds = flow.run_local_server(port=0)

    def refresh_token(self):
        # If there are no (valid) credentials available, 
        # try to refresh the token or let the user log in.
        if self.creds and self.creds.expired and self.creds.refresh_token:
            print("try to refresh gsheets token")
            self.creds.refresh(Request())

    def save_token(self):
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(self.creds, token)


class GSheet:
    def __init__(self, spreadsheet_id, in_lambda=False):
        self.spreadsheet_id = spreadsheet_id
        token = GSheetsToken(in_lambda)
        if not token.valid():
            raise Exception("No valid gsheets token found.")
        else:
            self.creds = token.creds

    @property
    def service(self):
        return build(
            "sheets", "v4", credentials=self.creds, cache_discovery=False
        )

    def _download_csv(self, sheet_name):
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=sheet_name)
            .execute()
        )

        print(result.get("values"))
        # /tmp is the only directory you can write to in a lambda function
        file_path = f"/tmp/{sheet_name.replace('/', '-')}.csv"

        with open(file_path, "w") as f:
            writer = csv.writer(f)
            writer.writerows(result.get("values"))

        f.close()

        logger.debug(f"Successfully downloaded {sheet_name}.csv")
        return file_path

    def import_to_dynamo(self, sheet_name):
        file_path = self._download_csv(sheet_name)

        schedule_csv_to_dynamo(SCHEDULE_TABLE, file_path)


def schedule_json_to_dynamo(schedule_table, json_file=None, schedule_data=None):

    if json_file is not None:
        with open(json_file, "r") as file:
            try:
                schedule_data = json.load(file)
            except Exception as e:
                print("Unable to load {}: {}" \
                      .format(json_file, str(e)))
                return
    elif schedule_data is None:
        raise Exception("{} called with no json_file or schedule_data args".format(
            sys._getframe().f_code.co_name
        ))

    try:
        dynamodb = boto3.resource('dynamodb')
        table_name = f"{schedule_table}"
        table = dynamodb.Table(table_name)

        for item in schedule_data.values():
            table.put_item(Item=item)
    except ClientError as e:
        error = e.response['Error']
        raise Exception("{}: {}".format(error['Code'], error['Message']))


def schedule_csv_to_dynamo(schedule_table, filepath):
    valid_days = ["M", "T", "W", "R", "F"]

    # make it so we can use lower-case keys in our row dicts;
    # there are lots of ways this spreadsheet data import could go wrong and
    # this is only one, but we do what we can.
    def lower_case_first_line(iter):
        header = next(iter).lower()
        return itertools.chain([header], iter)

    with open(filepath, "r") as f:
        reader = csv.DictReader(lower_case_first_line(f))
        rows = list(reader)

    schedule_data = {}
    for row in rows:

        try:
            zoom_link = urlparse(row["meeting id with password"])
            assert zoom_link.scheme.startswith("https")
        except AssertionError:
            zoom_link = None

        if zoom_link is None:
            print("Invalid zoom link value for {}: {}" \
                  .format(row["course code"], zoom_link))
            continue

        zoom_series_id = zoom_link.path.split("/")[-1]
        schedule_data.setdefault(zoom_series_id, {})
        schedule_data[zoom_series_id]["zoom_series_id"] = zoom_series_id

        opencast_series_id = urlparse(row["oc series"]) \
            .fragment.replace("/", "")
        schedule_data[zoom_series_id]["opencast_series_id"] = opencast_series_id

        subject = "{} - {}".format(row["course code"], row["type"])
        schedule_data[zoom_series_id]["opencast_subject"] = subject
        
        schedule_data[zoom_series_id].setdefault("Days", set())
        for day in row["day"].strip():
            if day not in valid_days:
                raise Exception("Got bad day value: {}".format(day))
            schedule_data[zoom_series_id]["Days"].add(day)

        schedule_data[zoom_series_id].setdefault("Time", set())
        time_object = datetime.strptime(row["start"], "%H:%M")
        schedule_data[zoom_series_id]["Time"].update([
            datetime.strftime(time_object, "%H:%M"),
            (time_object + timedelta(minutes=30)).strftime("%H:%M"),
            (time_object + timedelta(hours=1)).strftime("%H:%M")
        ])

    for id, item in schedule_data.items():
        item["Days"] = list(item["Days"])
        item["Time"] = list(item["Time"])

    schedule_json_to_dynamo(schedule_table, schedule_data=schedule_data)
