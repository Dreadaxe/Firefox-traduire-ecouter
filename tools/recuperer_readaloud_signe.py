#!/usr/bin/env python3
"""Recover an already-approved, unlisted Read Aloud signed XPI from Mozilla AMO.

Read-only: this script NEVER uploads a new version or requests signing.
Secrets are read from the environment and never written to logs.
"""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zipfile import ZipFile

ADDON_ID = "read-aloud-traduire-ecouter@dreadaxe"
BASE = "https://addons.mozilla.org/api/v5/addons/addon"
OUTPUT = Path("dist/read-aloud-traduire-ecouter-signe-mozilla.xpi")


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def auth_header():
    issuer = os.environ["AMO_JWT_ISSUER"].strip()
    secret = os.environ["AMO_JWT_SECRET"].strip()
    if not issuer or not secret:
        raise RuntimeError("Missing AMO secret")
    now = int(time.time())
    payload = {"iss": issuer, "iat": now, "exp": now + 60, "jti": secrets.token_hex(16)}
    head = {"typ": "JWT", "alg": "HS256"}
    signing_input = (
        b64(json.dumps(head, separators=(",", ":")).encode()) + "." +
        b64(json.dumps(payload, separators=(",", ":")).encode())
    )
    digest = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return "JWT " + signing_input + "." + b64(digest)


def fetch(url):
    req = urllib.request.Request(url, headers={
        "Authorization": auth_header(), "User-Agent": "Dreadaxe-signed-addon-recovery/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.read()
    except urllib.error.HTTPError as error:
        print(f"Mozilla returned HTTP {error.code} for approved-version lookup", file=sys.stderr)
        raise


def main():
    path = urllib.parse.quote(ADDON_ID, safe="@")
    url = f"{BASE}/{path}/versions/?filter=all_with_unlisted&page_size=50"
    response = json.loads(fetch(url))
    versions = response.get("results", [])
    print(f"Mozilla returned {len(versions)} Read Aloud versions")
    for version in versions[:10]:
        print("Version:", version.get("version"), "reviewed:", bool(version.get("reviewed")),
              "files:", [(f.get("status"), bool(f.get("url")), f.get("is_mozilla_signed_extension")) for f in version.get("files", [])])
    found = []
    for version in versions:
        for file in version.get("files", []):
            # Published/signed private versions have status "public".
            if file.get("status") != "public" or not file.get("url"):
                continue
            found.append((version.get("reviewed") or "", version.get("version") or "", file))
    if not found:
        raise RuntimeError("No approved Read Aloud version with a downloadable XPI found on Mozilla")
    found.sort(key=lambda entry: entry[0], reverse=True)
    reviewed, version, file = found[0]
    print(f"Approved version located: {version} (reviewed: {reviewed})")
    file_url = file["url"]
    if not file_url.startswith("https://addons.mozilla.org/"):
        raise RuntimeError("Unexpected signed file URL domain; refusing to fetch")
    data = fetch(file_url)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(data)
    with ZipFile(OUTPUT) as z:
        manifest = json.loads(z.read("manifest.json"))
        actual_id = manifest.get("browser_specific_settings", {}).get("gecko", {}).get("id")
        if actual_id != ADDON_ID:
            OUTPUT.unlink(missing_ok=True)
            raise RuntimeError("The signed XPI has an unexpected extension ID")
        if not any(name.startswith("META-INF/") for name in z.namelist()):
            OUTPUT.unlink(missing_ok=True)
            raise RuntimeError("XPI does not contain Mozilla signing metadata")
    print(f"Recovered signed Read Aloud {version}: {len(data)} bytes")
    print("Ready to upload as GitHub Actions artifact. Actual Android operation not yet tested.")


if __name__ == "__main__":
    main()
