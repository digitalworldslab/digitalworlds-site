#!/usr/bin/env python3
"""Digital Worlds Lab social poster: posts the next queued item to Bluesky and Mastodon.

Runs from GitHub Actions (.github/workflows/social-post.yml). Standard library only.
Credentials come from repository secrets; a platform without secrets is skipped.
  BSKY_HANDLE, BSKY_APP_PASSWORD           -> Bluesky (app password, never the main one)
  MASTODON_INSTANCE, MASTODON_TOKEN        -> Mastodon (token with write:statuses, write:media)
State (what was posted where) is kept in .social/state.json and committed back by the workflow.
"""
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "queue.json")
STATE = os.path.join(HERE, "state.json")
UA = "DigitalWorldsLab-social/1.0 (+https://digitalworlds.cc)"
DRY = os.environ.get("DRY_RUN") == "1"


def http(url, data=None, headers=None, method=None, timeout=30):
    h = {"User-Agent": UA}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def jpost(url, payload, headers=None):
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    body, _ = http(url, json.dumps(payload).encode(), h, "POST")
    return json.loads(body or b"{}")


def with_utm(url, source):
    if "digitalworlds.cc" not in url and "etsy.com" not in url and "gumroad.com" not in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}utm_source={source}&utm_medium=social&utm_campaign=dwl-auto"


def page_meta(url):
    """og:title / og:description / og:image of a page (best effort)."""
    meta = {"title": "", "description": "", "image": ""}
    try:
        raw, _ = http(url, timeout=20)
        text = raw.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print(f"  meta fetch failed for {url}: {e}")
        return meta
    for key, prop in (("title", "og:title"), ("description", "og:description"), ("image", "og:image")):
        m = re.search(r'<meta[^>]+property="%s"[^>]+content="([^"]*)"' % re.escape(prop), text)
        if m:
            meta[key] = html.unescape(m.group(1))
    if not meta["title"]:
        m = re.search(r"<title>([^<]*)</title>", text)
        meta["title"] = html.unescape(m.group(1)) if m else url
    if not meta["description"]:
        m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', text)
        meta["description"] = html.unescape(m.group(1)) if m else ""
    return meta


# ---------------------------------------------------------------- Bluesky
def bsky_post(item):
    handle = os.environ.get("BSKY_HANDLE", "")
    pw = os.environ.get("BSKY_APP_PASSWORD", "")
    base = os.environ.get("BSKY_PDS", "https://bsky.social")
    url = with_utm(item["url"], "bluesky")
    short = re.sub(r"^https?://(www\.)?", "", item["url"]).rstrip("/")
    text = item["text"].strip()
    tags = item.get("tags", [])[:3]
    tail = "\n\n" + short
    if tags:
        tail += "\n" + " ".join("#" + t for t in tags)
    full = text + tail
    if len(full) > 295:  # keep under 300 graphemes
        full = text[: 295 - len(tail) - 1].rstrip() + "…" + tail
    b = full.encode("utf-8")
    facets = []
    i = b.find(short.encode("utf-8"))
    if i >= 0:
        facets.append({"index": {"byteStart": i, "byteEnd": i + len(short.encode())},
                       "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]})
    for t in tags:
        tb = ("#" + t).encode("utf-8")
        j = b.rfind(tb)
        if j >= 0:
            facets.append({"index": {"byteStart": j, "byteEnd": j + len(tb)},
                           "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": t}]})
    meta = page_meta(item["url"])
    if DRY:
        print("  [dry] bluesky:", full.replace("\n", " | "))
        return "dry"
    sess = jpost(f"{base}/xrpc/com.atproto.server.createSession", {"identifier": handle, "password": pw})
    auth = {"Authorization": "Bearer " + sess["accessJwt"]}
    external = {"uri": url, "title": meta["title"][:300], "description": meta["description"][:1000]}
    img = item.get("image") or meta["image"]
    if img:
        try:
            data, ctype = http(img, timeout=30)
            if len(data) < 950_000:
                up_req = urllib.request.Request(
                    f"{base}/xrpc/com.atproto.repo.uploadBlob", data=data, method="POST",
                    headers={"User-Agent": UA, "Content-Type": ctype or "image/jpeg", **auth})
                with urllib.request.urlopen(up_req, timeout=60) as r:
                    external["thumb"] = json.loads(r.read())["blob"]
        except Exception as e:  # noqa: BLE001
            print(f"  thumb upload skipped: {e}")
    record = {
        "$type": "app.bsky.feed.post",
        "text": full,
        "createdAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "langs": [item.get("lang", "en")],
        "facets": facets,
        "embed": {"$type": "app.bsky.embed.external", "external": external},
    }
    res = jpost(f"{base}/xrpc/com.atproto.repo.createRecord",
                {"repo": sess["did"], "collection": "app.bsky.feed.post", "record": record}, auth)
    return res.get("uri", "ok")


# ---------------------------------------------------------------- Mastodon
def mastodon_post(item):
    inst = os.environ.get("MASTODON_INSTANCE", "mastodon.social").rstrip("/")
    if not inst.startswith("http"):
        inst = "https://" + inst
    token = os.environ.get("MASTODON_TOKEN", "")
    url = with_utm(item["url"], "mastodon")
    tags = item.get("mtags") or item.get("tags", [])
    status = item["text"].strip() + "\n\n" + url
    if tags:
        status += "\n\n" + " ".join("#" + t for t in tags[:5])
    if DRY:
        print("  [dry] mastodon:", status.replace("\n", " | "))
        return "dry"
    data = urllib.parse.urlencode({"status": status, "language": item.get("lang", "en"),
                                   "visibility": "public"}).encode()
    body, _ = http(f"{inst}/api/v1/statuses", data,
                   {"Authorization": "Bearer " + token, "Idempotency-Key": "dwl-" + item["id"]}, "POST")
    return json.loads(body).get("url", "ok")


PLATFORMS = {
    "bluesky": (bsky_post, ("BSKY_HANDLE", "BSKY_APP_PASSWORD")),
    "mastodon": (mastodon_post, ("MASTODON_INSTANCE", "MASTODON_TOKEN")),
}


def eligible(item, today):
    s, e = item.get("start"), item.get("end")
    if s and today < s:
        return False
    if e and today > e:
        return False
    return True


def pick(queue, done, platform, today):
    pool = [q for q in queue if q["id"] not in done and platform in q.get("platforms", ["bluesky", "mastodon"])
            and eligible(q, today)]
    dated = [q for q in pool if q.get("start")]  # time-limited items (sales) go first
    return (dated or pool or [None])[0]


def main():
    queue = json.load(open(QUEUE, encoding="utf-8"))
    state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    today = dt.date.today().isoformat()
    only = os.environ.get("ONLY_PLATFORM")
    changed = False
    for name, (fn, keys) in PLATFORMS.items():
        if only and only != name:
            continue
        if not all(os.environ.get(k) for k in keys) and not DRY:
            print(f"{name}: no credentials, skipped")
            continue
        st = state.setdefault(name, {"posted": [], "log": []})
        item = pick(queue, set(st["posted"]), name, today)
        if not item:
            print(f"{name}: queue empty")
            continue
        print(f"{name}: posting {item['id']}")
        try:
            ref = fn(item)
        except urllib.error.HTTPError as e:
            print(f"{name}: FAILED {e.code} {e.read()[:300]!r}")
            continue
        except Exception as e:  # noqa: BLE001
            print(f"{name}: FAILED {e}")
            continue
        if DRY:
            continue
        st["posted"].append(item["id"])
        st["log"].append({"id": item["id"], "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
                          "ref": ref})
        st["log"] = st["log"][-200:]
        changed = True
        print(f"{name}: posted -> {ref}")
    if changed:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
    remaining = {n: len([q for q in queue if q["id"] not in set(state.get(n, {}).get("posted", []))])
                 for n in PLATFORMS}
    print("remaining in queue:", remaining)
    return 0


if __name__ == "__main__":
    sys.exit(main())
