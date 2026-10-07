#!/usr/bin/env python3
"""
One-time script to deploy the SAM (Segment Anything Model) endpoint via SageMaker JumpStart.
Run this manually before deploying the CDK stacks that reference the endpoint.

Usage:
    pip install "sagemaker>=2.100.0,<3.0.0" boto3
    python deploy_sam_endpoint.py --env poc --instance-type ml.g6.24xlarge
"""

import argparse
import json
import time
import boto3
from sagemaker import Session
from sagemaker.jumpstart.model import JumpStartModel
from sagemaker.jumpstart.notebook_utils import list_jumpstart_models

# SAM 2.1 (Segment Anything Model 2.1) from Meta — supports both images and video.
# Other available sizes: meta-vs-sam-2-1-hiera-tiny, -small, -large
SAM_MODEL_ID = "meta-vs-sam-2-1-hiera-tiny"
SAM_MODEL_VERSION = "*"  # latest


def get_endpoint_name(identifier: str, env: str) -> str:
    return f"{identifier}-{env}-sam-endpoint"


def endpoint_exists(sm_client, endpoint_name: str) -> bool:
    try:
        sm_client.describe_endpoint(EndpointName=endpoint_name)
        return True
    except sm_client.exceptions.ClientError:
        return False


def delete_stale_endpoint_config(sm_client, endpoint_name: str) -> None:
    """
    A failed deployment can leave an orphaned EndpointConfig behind.
    Delete it so the next deploy attempt can create a fresh one.
    """
    try:
        sm_client.delete_endpoint_config(EndpointConfigName=endpoint_name)
        print(f"[INFO] Deleted stale endpoint config: {endpoint_name}")
    except sm_client.exceptions.ClientError:
        pass  # config doesn't exist, nothing to clean up


def get_or_create_sagemaker_role(iam_client, identifier: str, env: str) -> str:
    """
    SageMaker needs its own IAM role with sagemaker.amazonaws.com in the trust
    relationship. SSO session roles cannot be assumed by AWS services directly,
    so we create a dedicated one here.
    """
    role_name = f"{identifier}-{env}-sagemaker-execution-role"

    try:
        response = iam_client.get_role(RoleName=role_name)
        print(f"[INFO] Using existing SageMaker role: {role_name}")
        return response["Role"]["Arn"]
    except iam_client.exceptions.NoSuchEntityException:
        pass

    trust_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "sagemaker.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    })

    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=trust_policy,
        Description=f"SageMaker JumpStart execution role for {identifier}-{env}",
    )

    # AmazonSageMakerFullAccess includes S3 access to the JumpStart artifact buckets
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess",
    )

    print(f"[OK] Created SageMaker role: {role_name}")
    print("[INFO] Waiting 15s for IAM role to propagate...")
    time.sleep(15)
    return response["Role"]["Arn"]


def deploy(env: str, instance_type: str, region: str, identifier: str):
    boto_session = boto3.Session(region_name=region)
    sm_client = boto_session.client("sagemaker")
    iam_client = boto_session.client("iam")

    endpoint_name = get_endpoint_name(identifier, env)

    if endpoint_exists(sm_client, endpoint_name):
        print(f"[INFO] Endpoint already exists: {endpoint_name}")
        print(f"[INFO] Add this to your CDK config > compute.segmentLambda env vars:")
        print(f"       SAGEMAKER_ENDPOINT_NAME={endpoint_name}")
        return

    role_arn = get_or_create_sagemaker_role(iam_client, identifier, env)
    delete_stale_endpoint_config(sm_client, endpoint_name)

    print(f"[INFO] Deploying SAM model '{SAM_MODEL_ID}' to {instance_type}...")
    print(f"[INFO] First invocation takes 10–15 min to spin up.")

    sagemaker_session = Session(boto_session=boto_session)

    model = JumpStartModel(
        model_id=SAM_MODEL_ID,
        model_version=SAM_MODEL_VERSION,
        sagemaker_session=sagemaker_session,
        role=role_arn,
    )

    predictor = model.deploy(
        initial_instance_count=1,
        instance_type=instance_type,
        endpoint_name=endpoint_name,
    )

    print(f"\n[OK] Endpoint deployed successfully.")
    print(f"[INFO] Add this to your CDK config > compute.segmentLambda env vars:")
    print(f"       SAGEMAKER_ENDPOINT_NAME={predictor.endpoint_name}")


def delete(env: str, region: str, identifier: str):
    sm_client = boto3.client("sagemaker", region_name=region)
    endpoint_name = get_endpoint_name(identifier, env)

    if not endpoint_exists(sm_client, endpoint_name):
        print(f"[INFO] Endpoint not found: {endpoint_name}")
        return

    sm_client.delete_endpoint(EndpointName=endpoint_name)
    print(f"[OK] Endpoint deleted: {endpoint_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage the SAM SageMaker endpoint.")
    parser.add_argument("--env", default="poc", help="Environment name (e.g. poc, dev, prod)")
    parser.add_argument("--identifier", default="wound-scan", help="Project identifier")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument(
        "--instance-type",
        default="ml.g5.24xlarge",
        help="Instance type (e.g. ml.g6.24xlarge, ml.g5.24xlarge, ml.p4d.24xlarge)"
    )
    parser.add_argument("--delete", action="store_true", help="Delete the endpoint instead of deploying")
    args = parser.parse_args()

    if args.delete:
        delete(args.env, args.region, args.identifier)
    else:
        deploy(args.env, args.instance_type, args.region, args.identifier)
