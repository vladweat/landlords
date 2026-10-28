#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NETWORK="landlords-rate-test-$$"
API="${NETWORK}-api"
NGINX="${NETWORK}-nginx"
CADDY="${NETWORK}-caddy"
TEMP_DIR="$(mktemp -d)"

cleanup() {
  docker rm -f "$CADDY" "$NGINX" "$API" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

docker network create "$NETWORK" >/dev/null
SUBNET="$(docker network inspect --format '{{(index .IPAM.Config 0).Subnet}}' "$NETWORK")"
NETWORK_PREFIX="$(cut -d/ -f1 <<< "$SUBNET" | cut -d. -f1-3)"
PROXY_IP="${NETWORK_PREFIX}.10"
CLIENT_A_IP="${NETWORK_PREFIX}.20"
CLIENT_B_IP="${NETWORK_PREFIX}.21"

cat >"$TEMP_DIR/mock-api.py" <<'PY'
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond()

    def do_POST(self):
        self.respond()

    def respond(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"success","data":{}}')

    def log_message(self, *_args):
        pass


HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
PY

cat >"$TEMP_DIR/client.py" <<'PY'
import json
import sys
import time
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request, urlopen


def request(path, forwarded=None):
    headers = {"Content-Type": "application/json"}
    if forwarded:
        headers["X-Forwarded-For"] = forwarded
    req = Request(
        f"http://caddy{path}", data=b"{}", headers=headers, method="POST"
    )
    for attempt in range(30):
        try:
            response = urlopen(req, timeout=2)
        except HTTPError as error:
            response = error
        except URLError:
            if attempt == 29:
                raise
            time.sleep(1)
            continue
        return response.code, response.headers.get("Content-Type", ""), response.read()


def flood(path):
    for _ in range(30):
        status, content_type, body = request(path)
        if status == 429:
            assert "application/json" in content_type, content_type
            assert json.loads(body) == {
                "status": "error",
                "message": "Too many requests",
            }, body
            return
        assert status == 200, (path, status, body)
    raise AssertionError(f"route was not rate limited: {path}")


mode, path, *args = sys.argv[1:]
if mode == "flood":
    flood(path)
elif mode == "single":
    forwarded = args[0] if args else None
    status, _content_type, body = request(path, forwarded)
    assert status == 200, (path, status, body)
else:
    raise AssertionError(f"unknown mode: {mode}")
PY

sed "s/172.18.0.10/$PROXY_IP/" "$ROOT_DIR/nginx/nginx.conf" >"$TEMP_DIR/nginx.conf"
cat >"$TEMP_DIR/Caddyfile" <<'CADDY'
:80 {
    reverse_proxy nginx:80
}
CADDY

docker run -d --name "$API" --network "$NETWORK" --network-alias api \
  -v "$TEMP_DIR/mock-api.py:/mock-api.py:ro" landlords-api python /mock-api.py >/dev/null
docker run -d --name "$NGINX" --network "$NETWORK" --network-alias nginx \
  -v "$TEMP_DIR/nginx.conf:/etc/nginx/conf.d/default.conf:ro" landlords-nginx >/dev/null
docker run -d --name "$CADDY" --network "$NETWORK" --network-alias caddy \
  --ip "$PROXY_IP" -v "$TEMP_DIR/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2 caddy run --config /etc/caddy/Caddyfile >/dev/null

run_client() {
  local client_ip="$1"
  shift
  docker run --rm --network "$NETWORK" --ip "$client_ip" \
    -v "$TEMP_DIR/client.py:/client.py:ro" landlords-api python /client.py "$@"
}

run_client "$CLIENT_A_IP" flood /api/v1/auth/login
run_client "$CLIENT_B_IP" single /api/v1/auth/login "$CLIENT_A_IP"
run_client "$CLIENT_A_IP" flood /api/v1/auth/forgot-password
run_client "$CLIENT_A_IP" flood /api/v1/auth/reset-password
run_client "$CLIENT_A_IP" flood /api/v1/auth/register
run_client "$CLIENT_A_IP" flood /api/v1/public/invites/test-token-marker/accept
run_client "$CLIENT_A_IP" flood /api/v1/public/invoices/test-token-marker/claim
run_client "$CLIENT_A_IP" flood /api/v1/public/portal/test-token-marker/claim
run_client "$CLIENT_A_IP" flood /api/v1/reminders
run_client "$CLIENT_B_IP" single /health
run_client "$CLIENT_B_IP" single /api/v1/public/status

if docker logs "$NGINX" 2>&1 | grep -q 'test-token-marker'; then
  echo "token-bearing request was written to nginx logs" >&2
  exit 1
fi

echo "Rate-limit proxy smoke checks passed."
