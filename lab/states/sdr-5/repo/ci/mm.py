"""Mattermost helper for the time measurement. Reads MM_URL and MM_TOKEN (a personal access token). Standard library only."""
import json
import os
import urllib.request

TEAM = os.environ.get("MM_TEAM", "lab")
CHANNEL = "siem-alerts"


def api(method, path, body=None):
    headers = {"Authorization": "Bearer " + os.environ["MM_TOKEN"], "Content-Type": "application/json"}
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(os.environ["MM_URL"].rstrip("/") + "/api/v4" + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def channel_id():
    return api("GET", "/teams/name/%s/channels/name/%s" % (TEAM, CHANNEL))["id"]


def posts_since(channel, since_ms):
    """Posts in the channel created after since_ms, as a list of {id, message, create_at}."""
    data = api("GET", "/channels/%s/posts?since=%d" % (channel, since_ms))
    return sorted(data["posts"].values(), key=lambda p: p["create_at"])


def post_text(post):
    """All visible text of a post: its message plus the title, text and fallback of each attachment."""
    parts = [post.get("message", "")]
    for att in (post.get("props") or {}).get("attachments") or []:
        parts += [att.get("title", ""), att.get("text", ""), att.get("fallback", "")]
    return " ".join(str(p) for p in parts)


def reply(channel, root_id, text):
    """Reply in the alert's thread and return the reply's create_at in milliseconds."""
    return api("POST", "/posts", {"channel_id": channel, "root_id": root_id, "message": text})["create_at"]
