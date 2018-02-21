
import time
import aws_lambda_logging
from os import getenv as env

LOG_LEVEL = env('DEBUG') and 'DEBUG' or 'INFO'
BOTO_LOG_LEVEL = env('BOTO_DEBUG') and 'DEBUG' or 'INFO'

def setup_logging(context):
    aws_lambda_logging.setup(
        level=LOG_LEVEL,
        boto_level=BOTO_LOG_LEVEL,
        aws_request_id=context.aws_request_id
    )

class timethis():

    def __init__(self, name, log_method):
        self.metric_name = name
        self.log_method = log_method

    def __enter__(self):
        self.t = time.clock()
        return self

    def __exit__(self, type, value, traceback):
        self.t = time.clock() - self.t
        self.log_method("TIMETHIS {} {}".format(self.name, self.t))