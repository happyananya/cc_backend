"""LF1 (index-photos): triggered by S3 PUT on the photos bucket (B2).

Detects labels with Rekognition, merges them with the x-amz-meta-customLabels
metadata, and stores a document in the OpenSearch "photos" index.
"""
import base64
import json
import os
import urllib.parse

import boto3
import urllib3

s3 = boto3.client("s3")
rekognition = boto3.client("rekognition")
http = urllib3.PoolManager()

ES_ENDPOINT = os.environ["ES_ENDPOINT"].rstrip("/")
ES_INDEX = os.environ.get("ES_INDEX", "photos")
ES_AUTH = base64.b64encode(
    f"{os.environ['ES_USER']}:{os.environ['ES_PASS']}".encode()
).decode()


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        # S3 lowercases user metadata keys: x-amz-meta-customLabels -> "customlabels"
        head = s3.head_object(Bucket=bucket, Key=key)
        custom = head.get("Metadata", {}).get("customlabels", "")
        labels = [l.strip().lower() for l in custom.split(",") if l.strip()]

        response = rekognition.detect_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            MaxLabels=20,
            MinConfidence=70,
        )
        labels += [l["Name"].lower() for l in response["Labels"]]

        doc = {
            "objectKey": key,
            "bucket": bucket,
            "createdTimestamp": head["LastModified"].strftime("%Y-%m-%dT%H:%M:%S"),
            "labels": list(dict.fromkeys(labels)),  # dedupe, keep order
        }

        doc_id = urllib.parse.quote(f"{bucket}/{key}", safe="")
        r = http.request(
            "PUT",
            f"{ES_ENDPOINT}/{ES_INDEX}/_doc/{doc_id}",
            body=json.dumps(doc),
            headers={"Content-Type": "application/json", "Authorization": f"Basic {ES_AUTH}"},
        )
        print(f"Indexed {key}: {doc['labels']} -> {r.status} {r.data[:300]}")

    return {"statusCode": 200, "body": "ok"}
