import json
import uuid
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

TABLE_NAME = "wound-scan-poc-session-schema"
BUCKET_NAME = "wound-scan-poc-assets-962524581373-us-east-1-an"

# TODO: Confirm exact file naming convention with iOS/Yogi
# Assumption: 5 frames x 5 file types = 25 files
FRAME_FILE_TYPES = [
    "rgb.jpg",
    "depth.bin",
    "confidence.bin",
    "intrinsics.json",
    "metadata.json",
]
FRAME_COUNT = 5
PRESIGNED_URL_EXPIRY = 3600  # 1 hour in seconds

# S3 output file keys (confirmed with Andres — processed/{scanId}/ prefix)
RESULTS_FILES = {
    "measurements": "measurements.json",
    "diagram_top": "diagram_top.svg",
    "diagram_cross": "diagram_cross.png",
    "narration": "narration.txt",
}


def generate_frame_keys(scan_id):
    """Generate S3 keys for all 25 frame files."""
    keys = []
    for i in range(1, FRAME_COUNT + 1):
        for file_type in FRAME_FILE_TYPES:
            keys.append(f"scans/{scan_id}/frames/frame_{i}_{file_type}")
    return keys


def post_scans(event):
    """
    POST /scans
    Accepts session.json, creates a scan record in DynamoDB,
    generates 25 presigned PUT URLs, and returns scanId + URLs.
    """
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)

    scan_id = str(uuid.uuid4())

    table = dynamodb.Table(TABLE_NAME)
    table.put_item(
        Item={
            "id": scan_id,
            "status": "UPLOADING",
            "session": body,
        }
    )

    frame_keys = generate_frame_keys(scan_id)
    presigned_urls = {}

    for key in frame_keys:
        url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": key,
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY,
            HttpMethod="PUT",
        )
        file_name = key.split("/")[-1]
        presigned_urls[file_name] = url

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "scanId": scan_id,
            "uploadUrls": presigned_urls,
        })
    }


def get_scan_status(event):
    """
    GET /scans/{scanId}/status
    Returns the current processing status of a scan.
    """
    path_params = event.get("pathParameters") or {}
    scan_id = path_params.get("scanId")

    if not scan_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing scanId"})
        }

    table = dynamodb.Table(TABLE_NAME)

    response = table.query(
        KeyConditionExpression=Key("id").eq(scan_id)
    )

    items = response.get("Items", [])

    if not items:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Scan not found"})
        }

    item = items[-1]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "scanId": scan_id,
            "status": item.get("status"),
        })
    }


def get_scan_results(event):
    """
    GET /scans/{scanId}/results
    Returns measurements, presigned GET URLs for diagrams, and narration.
    Only available when scan status is COMPLETE.
    """
    path_params = event.get("pathParameters") or {}
    scan_id = path_params.get("scanId")

    if not scan_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing scanId"})
        }

    table = dynamodb.Table(TABLE_NAME)

    # Look up scan record
    response = table.query(
        KeyConditionExpression=Key("id").eq(scan_id)
    )
    items = response.get("Items", [])

    if not items:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Scan not found"})
        }

    item = items[-1]
    status = item.get("status")

    # Handle incomplete/failed scans
    if status == "FAILED":
        return {
            "statusCode": 422,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "scanId": scan_id,
                "status": "FAILED",
                "error": item.get("error", "Scan processing failed."),
            })
        }

    if status != "COMPLETE":
        return {
            "statusCode": 409,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "scanId": scan_id,
                "status": status,
                "error": f"Results not available. Scan is currently {status}.",
            })
        }

    # Build S3 keys for all result files
    results_prefix = f"processed/{scan_id}"
    result_keys = {
        name: f"{results_prefix}/{filename}"
        for name, filename in RESULTS_FILES.items()
    }

    # Read measurements.json content from S3
    measurements = None
    try:
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=result_keys["measurements"])
        measurements = json.loads(obj["Body"].read().decode("utf-8"))
    except s3_client.exceptions.NoSuchKey:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "measurements.json not found in S3."})
        }

    # Read narration.txt content from S3
    narration = None
    try:
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=result_keys["narration"])
        narration = obj["Body"].read().decode("utf-8")
    except s3_client.exceptions.NoSuchKey:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "narration.txt not found in S3."})
        }

    # Generate presigned GET URLs for both diagrams
    diagram_urls = {}
    for diagram_key in ["diagram_top", "diagram_cross"]:
        diagram_urls[diagram_key] = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": result_keys[diagram_key],
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY,
        )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "scanId": scan_id,
            "status": "COMPLETE",
            "measurements": measurements,
            "diagrams": diagram_urls,
            "narration": narration,
        })
    }


def handler(event, context):
    http_method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod", "")
    )
    path = event.get("rawPath") or event.get("path", "")

    # Route: POST /scans
    if http_method == "POST" and path == "/scans":
        return post_scans(event)

    # Route: GET /scans/{scanId}/status
    if http_method == "GET" and "/status" in path:
        return get_scan_status(event)

    # Route: GET /scans/{scanId}/results
    if http_method == "GET" and "/results" in path:
        return get_scan_results(event)

    return {
        "statusCode": 404,
        "body": json.dumps({"error": "Route not found"})
    }
