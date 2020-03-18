import jwt
import json
import time
import boto3
import logging
import requests
from enum import Enum
import aws_lambda_logging
from functools import wraps
from os import getenv as env
from dotenv import load_dotenv
from os.path import join, dirname
from botocore.exceptions import ClientError

logger = logging.getLogger()

load_dotenv(join(dirname(__file__), '../.env'))

LOG_LEVEL = env('DEBUG') and 'DEBUG' or 'INFO'
BOTO_LOG_LEVEL = env('BOTO_DEBUG') and 'DEBUG' or 'INFO'
ZOOM_API_BASE_URL = "https://api.zoom.us/v2/"
ZOOM_API_KEY = env("ZOOM_API_KEY")
ZOOM_API_SECRET = env("ZOOM_API_SECRET")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
PIPELINE_STATE_TABLE = env("PIPELINE_STATE_TABLE")

class pipeline_states(Enum):
    ON_DEMAND_RECEIVED = 0
    SENT_TO_WEBHOOK = 1
    WEBHOOK_RECEIVED = 2
    WEBHOOK_FAILED = 3
    SENT_TO_DOWNLOADER = 4
    DOWNLOADER_RECIEVED = 5
    DOWNLOADER_FAILED = 6
    SENT_TO_UPLOADER = 7
    UPLOADER_RECIEVED = 8
    UPLOADER_FAILED = 9
    SENT_TO_OPENCAST = 10

pipeine_state_messages = [
    "Received by the ingest webhook",
    "Failed in ingest webhook",
    "Sent to Zoom download queue",
    "Received by Zoom downloader",
    "Failed in Zoom downloader",
    "Sent to Opencast upload queue",
    "Received by Opencast uploader",
    "Failed in Opencast uploader",
    "Opencast upload succeeded",
    "Accepted by on-demand endpoint",
    "Sent to ingest webhook"
]

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

def set_pipeline_state(uuid, state, extra_data=None):
    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(PIPELINE_STATE_TABLE)

        new_item = {
            "recording_uuid": uuid,
            "state": pipeine_state_messages[state.value],
        }
        if extra_data is not None:
            new_item.update(extra_data)

        table.put_item(Item=new_item)
    except ClientError as e:
        error = e.response["Error"]
        logger.exception("{}: {}".format(error["Code"], error["Message"]))
    except Exception as e:
        logger.exception("Something went wrong updating pipeline state")

