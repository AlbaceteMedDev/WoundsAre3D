import json
import logging
import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")
sfn_client = boto3.client("stepfunctions")

TABLE_NAME = "wound-scan-poc-session-schema"
BUCKET_NAME = "wound-scan-poc-assets-962524581373-us-east-1-an"
STATE_MACHINE_ARN = "arn:aws:states:us-east-1:962524581373:stateMachine:wound-scan-poc-workflow"

EXPECTED_FILE_COUNT = 25  # 5 frames x 5 file types


def get_scan_id_from_key(s3_key):
    """
    Extract scanId from S3 key.
    Expected format: scans/{scanId}/frames/frame_{n}_{type}
    """
    parts = s3_key.split("/")
    if len(parts) >= 2 and parts[0] == "scans":
        return parts[1]
    return None


def count_uploaded_files(scan_id):
    """Count how many files have been uploaded for a given scanId."""
    prefix = f"scans/{scan_id}/frames/"
    paginator = s3_client.get_paginator("list_objects_v2")
    total = 0
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        total += page.get("KeyCount", 0)
    return total


def get_scan_record(table, scan_id):
    """Query DynamoDB for the scan record by scanId."""
    response = table.query(
        KeyConditionExpression=Key("id").eq(scan_id)
    )
    items = response.get("Items", [])
    return items[-1] if items else None


def update_scan_status(table, scan_id, old_status, new_status, extra_attrs=None):
    """
    Update scan status by deleting the old record and creating a new one.
    Required because status is a sort key (immutable in DynamoDB).
    TODO: Andres should change status to a regular attribute to avoid this.
    """
    # Delete old record
    table.delete_item(Key={"id": scan_id, "status": old_status})

    # Build new item
    new_item = {"id": scan_id, "status": new_status}
    if extra_attrs:
        new_item.update(extra_attrs)

    table.put_item(Item=new_item)
    logger.info(f"Scan {scan_id} status updated: {old_status} -> {new_status}")


def start_step_functions(scan_id, session_data):
    """Start the Step Functions workflow for a completed scan."""
    execution_input = json.dumps({
        "scanId": scan_id,
        "bucket": BUCKET_NAME,
        "prefix": f"scans/{scan_id}/frames/",
        "session": session_data or {},
    })

    response = sfn_client.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=f"scan-{scan_id}",  # unique per scan
        input=execution_input,
    )

    logger.info(f"Started Step Functions execution for scan {scan_id}: {response['executionArn']}")
    return response["executionArn"]


def process_s3_event(record):
    """Process a single S3 event record."""
    s3_key = record["s3"]["object"]["key"]
    logger.info(f"Processing S3 event for key: {s3_key}")

    # Extract scanId from the S3 key
    scan_id = get_scan_id_from_key(s3_key)
    if not scan_id:
        logger.warning(f"Could not extract scanId from key: {s3_key}")
        return

    table = dynamodb.Table(TABLE_NAME)

    # Get current scan record
    scan = get_scan_record(table, scan_id)
    if not scan:
        logger.warning(f"Scan record not found for scanId: {scan_id}")
        return

    current_status = scan.get("status")

    # Skip if already past UPLOADING (avoid duplicate triggers)
    if current_status != "UPLOADING":
        logger.info(f"Scan {scan_id} is already in status {current_status}, skipping.")
        return

    # Count uploaded files
    uploaded_count = count_uploaded_files(scan_id)
    logger.info(f"Scan {scan_id}: {uploaded_count}/{EXPECTED_FILE_COUNT} files uploaded.")

    if uploaded_count < EXPECTED_FILE_COUNT:
        # Not all files are here yet, nothing to do
        return

    # All 25 files uploaded — update status to PROCESSING and start workflow
    logger.info(f"All {EXPECTED_FILE_COUNT} files uploaded for scan {scan_id}. Starting workflow.")

    session_data = scan.get("session", {})

    try:
        execution_arn = start_step_functions(scan_id, session_data)
        update_scan_status(
            table,
            scan_id,
            old_status=current_status,
            new_status="PROCESSING",
            extra_attrs={
                "session": session_data,
                "executionArn": execution_arn,
            }
        )
    except Exception as e:
        logger.error(f"Failed to start workflow for scan {scan_id}: {str(e)}")
        update_scan_status(
            table,
            scan_id,
            old_status=current_status,
            new_status="FAILED",
            extra_attrs={
                "session": session_data,
                "error": str(e),
            }
        )
        raise


def handler(event, context):
    """
    SQS trigger handler.
    Each SQS message contains one or more S3 event records.
    """
    logger.info(f"Received {len(event.get('Records', []))} SQS messages.")

    for sqs_record in event.get("Records", []):
        try:
            body = json.loads(sqs_record["body"])

            # S3 test notification — skip
            if "Event" in body and body["Event"] == "s3:TestEvent":
                logger.info("Skipping S3 test event.")
                continue

            s3_records = body.get("Records", [])
            for s3_record in s3_records:
                process_s3_event(s3_record)

        except Exception as e:
            logger.error(f"Error processing SQS record: {str(e)}", exc_info=True)
            raise  # Re-raise so SQS retries the message
