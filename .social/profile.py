#!/usr/bin/env python3
"""Set the Bluesky profile (name, bio, avatar, banner) from .social/profile.json. Run via workflow_dispatch."""
import json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post import http, jpost, UA  # noqa: E402

base = os.environ.get("BSKY_PDS", "https://bsky.social")
cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile.json"), encoding="utf-8"))
sess = jpost(f"{base}/xrpc/com.atproto.server.createSession",
             {"identifier": os.environ["BSKY_HANDLE"], "password": os.environ["BSKY_APP_PASSWORD"]})
auth = {"Authorization": "Bearer " + sess["accessJwt"]}

def blob(path):
    data = open(path, "rb").read()
    req = urllib.request.Request(f"{base}/xrpc/com.atproto.repo.uploadBlob", data=data, method="POST",
                                 headers={"User-Agent": UA, "Content-Type": "image/jpeg", **auth})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["blob"]

try:
    cur = json.loads(http(f"{base}/xrpc/com.atproto.repo.getRecord?repo={sess['did']}&collection=app.bsky.actor.profile&rkey=self", headers=auth)[0]).get("value", {})
except Exception:
    cur = {}
rec = dict(cur)
rec.update({"$type": "app.bsky.actor.profile", "displayName": cfg["displayName"], "description": cfg["description"],
            "avatar": blob(cfg["avatar"]), "banner": blob(cfg["banner"])})
res = jpost(f"{base}/xrpc/com.atproto.repo.putRecord",
            {"repo": sess["did"], "collection": "app.bsky.actor.profile", "rkey": "self", "record": rec}, auth)
print("profile updated", res.get("uri"), "did", sess["did"])
