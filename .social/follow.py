#!/usr/bin/env python3
"""Grow the Bluesky audience gently: follow up to MAX_FOLLOWS people per run who post about
budgeting / personal finance / debt payoff / small business (EN, PL, DE). Skips accounts already
followed, bots without posts, and huge accounts (they don't follow back). Runs once a day."""
import json, os, random, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post import http, jpost  # noqa: E402

BASE = os.environ.get("BSKY_PDS", "https://bsky.social")
MAX = int(os.environ.get("MAX_FOLLOWS", "25"))
TERMS = ["#personalfinance", "#budgeting", "#debtfree", "#sinkingfunds", "#frugal", "#savingmoney",
         "#moneytips", "#etsyseller", "#smallbusiness", "#freelance", "#finanse", "#oszczędzanie",
         "#Haushaltsbuch", "#Finanzen", "#sparen", "budget spreadsheet", "debt snowball", "zero based budget"]
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "follow-state.json")

sess = jpost(f"{BASE}/xrpc/com.atproto.server.createSession",
             {"identifier": os.environ["BSKY_HANDLE"], "password": os.environ["BSKY_APP_PASSWORD"]})
AUTH = {"Authorization": "Bearer " + sess["accessJwt"]}
ME = sess["did"]

def get(path, **q):
    body, _ = http(f"{BASE}/xrpc/{path}?{urllib.parse.urlencode(q)}", headers=AUTH)
    return json.loads(body)

state = json.load(open(STATE)) if os.path.exists(STATE) else {"followed": [], "runs": []}
seen = set(state["followed"])
cur = None
while True:  # who we already follow
    q = {"actor": ME, "limit": 100}
    if cur: q["cursor"] = cur
    r = get("app.bsky.graph.getFollows", **q)
    seen |= {f["did"] for f in r.get("follows", [])}
    cur = r.get("cursor")
    if not cur: break

cands = {}
random.shuffle(TERMS)
for t in TERMS[:8]:
    try:
        r = get("app.bsky.feed.searchPosts", q=t, limit=40, sort="latest")
    except Exception as e:  # noqa: BLE001
        print("search failed", t, e); continue
    for p in r.get("posts", []):
        a = p["author"]
        if a["did"] != ME and a["did"] not in seen:
            cands.setdefault(a["did"], a)
print("candidates", len(cands))
done = []
for did in list(cands)[:MAX * 3]:
    if len(done) >= MAX: break
    try:
        prof = get("app.bsky.actor.getProfile", actor=did)
    except Exception:
        continue
    fol, posts = prof.get("followersCount", 0), prof.get("postsCount", 0)
    if posts < 5 or fol > 20000 or prof.get("viewer", {}).get("following"):
        continue
    if any(l.get("val") in ("spam", "!hide", "porn", "sexual", "nudity") for l in prof.get("labels", [])):
        continue
    jpost(f"{BASE}/xrpc/com.atproto.repo.createRecord",
          {"repo": ME, "collection": "app.bsky.graph.follow",
           "record": {"$type": "app.bsky.graph.follow", "subject": did,
                      "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())}}, AUTH)
    done.append(did); print("followed", prof.get("handle"), fol, "followers")
    time.sleep(random.uniform(2, 5))
me = get("app.bsky.actor.getProfile", actor=ME)
state["followed"] = (state["followed"] + done)[-5000:]
state["runs"] = (state["runs"] + [{"at": time.strftime("%Y-%m-%d %H:%M"), "new": len(done),
                 "followers": me.get("followersCount"), "follows": me.get("followsCount")}])[-120:]
json.dump(state, open(STATE, "w"), indent=1)
print("followers now", me.get("followersCount"), "following", me.get("followsCount"))
