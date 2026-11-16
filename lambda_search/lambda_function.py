"""LF2 (search-photos): GET /search?q=...

Sends the query to the Lex bot to extract keywords, then searches the
OpenSearch "photos" index for any photo whose labels match a keyword.
"""
import base64
import json
import os
import uuid

import boto3
import urllib3

lex = boto3.client("lexv2-runtime")
http = urllib3.PoolManager()

ES_ENDPOINT = os.environ["ES_ENDPOINT"].rstrip("/")
ES_INDEX = os.environ.get("ES_INDEX", "photos")
ES_AUTH = base64.b64encode(
    f"{os.environ['ES_USER']}:{os.environ['ES_PASS']}".encode()
).decode()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,x-api-key,x-amz-meta-customLabels",
    "Access-Control-Allow-Methods": "GET,PUT,OPTIONS",
    "Content-Type": "application/json",
}


def singular(word):
    """Rekognition labels are singular ("dog"), queries are often plural ("dogs")."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and word[:-2].endswith(("ch", "sh", "x", "ss")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def get_keywords(query):
    response = lex.recognize_text(
        botId=os.environ["BOT_ID"],
        botAliasId=os.environ["BOT_ALIAS_ID"],
        localeId=os.environ.get("BOT_LOCALE", "en_US"),
        sessionId=str(uuid.uuid4()),
        text=query,
    )
    print("Lex response:", json.dumps(response.get("sessionState", {}), default=str))

    slots = response.get("sessionState", {}).get("intent", {}).get("slots") or {}
    keywords = []
    for slot in slots.values():
        if slot and slot.get("value"):
            value = slot["value"].get("interpretedValue") or slot["value"].get("originalValue")
            if value:
                keywords.append(value)
    return keywords


def search(keywords):
    terms = set()
    for keyword in keywords:
        keyword = keyword.lower().strip()
        terms.update([keyword, singular(keyword)])

    query = {
        "size": 100,
        "query": {"bool": {"should": [{"match": {"labels": t}} for t in terms]}},
    }
    r = http.request(
        "GET",
        f"{ES_ENDPOINT}/{ES_INDEX}/_search",
        body=json.dumps(query),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {ES_AUTH}"},
    )
    hits = json.loads(r.data).get("hits", {}).get("hits", [])

    results = []
    for hit in hits:
        src = hit["_source"]
        results.append({
            "url": f"https://{src['bucket']}.s3.amazonaws.com/{src['objectKey']}",
            "labels": src["labels"],
        })
    return results


def lambda_handler(event, context):
    q = (event.get("queryStringParameters") or {}).get("q", "").strip()
    keywords = get_keywords(q) if q else []
    print(f"q={q!r} keywords={keywords}")

    results = search(keywords) if keywords else []
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({"results": results}),
    }
