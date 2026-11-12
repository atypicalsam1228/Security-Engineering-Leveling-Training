"""Find labs whose AutoDestroyAfter tag is in the past and report them.

Read-only: lists tagged resources and publishes the expired LabIds to SNS.
Destruction is done by terraform/scripts/sweep.sh.
"""

import datetime
import json
import os
import re

import boto3

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TAG_EXPIRY = "AutoDestroyAfter"
TAG_LAB = "LabId"


def find_expired(today):
    """Return {lab_id: [resource ARNs]} for resources past their date."""
    client = boto3.client("resourcegroupstaggingapi")
    paginator = client.get_paginator("get_resources")
    expired = {}
    for page in paginator.paginate(TagFilters=[{"Key": TAG_EXPIRY}]):
        for item in page["ResourceTagMappingList"]:
            tags = {t["Key"]: t["Value"] for t in item.get("Tags", [])}
            when = tags.get(TAG_EXPIRY, "")
            lab = tags.get(TAG_LAB)
            if lab and DATE_RE.match(when) and when < today:
                expired.setdefault(lab, []).append(item["ResourceARN"])
    return expired


def handler(event, context):
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    expired = find_expired(today)
    summary = {lab: len(arns) for lab, arns in sorted(expired.items())}
    print(json.dumps({"today": today, "expired": summary}))
    if expired:
        lines = [f"{lab}: {count} resources" for lab, count in summary.items()]
        boto3.client("sns").publish(
            TopicArn=os.environ["TOPIC_ARN"],
            Subject="Expired lab(s) need destroying",
            Message=(
                f"Labs past {TAG_EXPIRY} as of {today} (UTC):\n"
                + "\n".join(lines)
                + "\n\nRun terraform/scripts/sweep.sh to destroy them."
            ),
        )
    return {"expired": summary}
