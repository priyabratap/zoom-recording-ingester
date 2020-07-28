RECORDINGS_BUCKET = "zoom-recording-files"

NOTIFICATIONS_TOPIC = "notifications"
METRIC_NAMESPACE = "log-metrics"

SCHEDULE_TABLE = "schedule"

DOWNLOAD_QUEUE = "download"
DOWNLOAD_DLQ = "download-dlq"
UPLOAD_QUEUE = "upload.fifo"
UPLOAD_DLQ = "upload-dlq.fifo"
QUEUES = [DOWNLOAD_QUEUE, DOWNLOAD_DLQ, UPLOAD_QUEUE, UPLOAD_DLQ]

ON_DEMAND_FUNCTION = "zoom-on-demand"
WEBHOOK_FUNCTION = "zoom-webhook"
DOWNLOAD_FUNCTION = "zoom-downloader"
UPLOAD_FUNCTION = "zoom-uploader"
OP_COUNTS_FUNCTION = "opencast-op-counts"
LOG_NOTIFICATION_FUNCTION = "zoom-log-notifications"
FUNCTIONS = [
    ON_DEMAND_FUNCTION,
    WEBHOOK_FUNCTION,
    DOWNLOAD_FUNCTION,
    UPLOAD_FUNCTION,
    OP_COUNTS_FUNCTION,
    LOG_NOTIFICATION_FUNCTION,
]

REST_API = "api"
API_STAGE = "live"
WEBHOOK_ENDPOINT = "webhook"
ON_DEMAND_ENDPOINT = "ingest"

CODEBUILD_PROJECT = "codebuild"

LAMBDA_RELEASE_ALIAS = "live"
