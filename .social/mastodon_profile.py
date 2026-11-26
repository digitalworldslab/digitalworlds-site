#!/usr/bin/env python3
"""Set the Mastodon profile (name, bio, links, avatar, header). Run via workflow_dispatch."""
import json, os, urllib.request, uuid
inst = os.environ["MASTODON_INSTANCE"].rstrip("/")
inst = inst if inst.startswith("http") else "https://" + inst
tok = os.environ["MASTODON_TOKEN"]
fields = {
    "display_name": "Digital Worlds Lab",
    "note": "Free money calculators + budget, debt payoff & savings spreadsheets (Google Sheets / Excel). Plain guides with worked examples. EN · PL · DE. Kostenloses Haushaltsbuch auf Deutsch.",
    "fields_attributes[0][name]": "Website", "fields_attributes[0][value]": "https://digitalworlds.cc",
    "fields_attributes[1][name]": "Shop", "fields_attributes[1][value]": "https://digitalworldslab.etsy.com",
    "fields_attributes[2][name]": "Deutsch", "fields_attributes[2][value]": "https://digitalworlds.cc/de/",
    "discoverable": "true", "indexable": "true",
}
files = {"avatar": "social-assets/avatar-v2.jpg", "header": "social-assets/banner-v2.jpg"}
b = uuid.uuid4().hex
body = b""
for k, v in fields.items():
    body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
for k, p in files.items():
    body += (f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{os.path.basename(p)}"\r\n'
             f'Content-Type: image/jpeg\r\n\r\n').encode() + open(p, "rb").read() + b"\r\n"
body += f"--{b}--\r\n".encode()
req = urllib.request.Request(f"{inst}/api/v1/accounts/update_credentials", data=body, method="PATCH",
                             headers={"Authorization": "Bearer " + tok, "User-Agent": "DigitalWorldsLab/1.0",
                                      "Content-Type": f"multipart/form-data; boundary={b}"})
with urllib.request.urlopen(req, timeout=60) as r:
    j = json.loads(r.read())
print("mastodon profile updated:", j.get("acct"), j.get("url"))
