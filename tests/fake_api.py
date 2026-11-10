"""A small in-process stand-in for the Wallet API, used by the tests.

It follows the routes, parameters, status codes and error bodies of
hypercore-one/znn_walletapi_csharp closely enough to exercise the client over
real HTTP.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ADMIN = ("admin", "admin-password")
WALLET_PASSWORD = "Secret#123"
MNEMONIC = " ".join(["abandon"] * 23 + ["art"])
ADDRESS_0 = "z1qqjnwjjpnue8xmmpanz6csze6tcmtzzdtfsww7"
ADDRESS_1 = "z1qr00j9wkcyvgz567sygnjxshnkq3xqxsc0t7cv"
ZNN = "zts1znnxxxxxxxxxxxxx9z4ulx"
QSR = "zts1qsrxxxxxxxxxxxxxmrhjll"


class FakeWalletApi:
    """Server state plus a log of every request the client made."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.tokens: set[str] = set()
        self.token_counter = 0
        self.logins = 0
        self.initialized = True
        self.unlocked = False
        self.accounts = [ADDRESS_0, ADDRESS_1]
        self.plasma: dict[str, int] = {}
        # Number of plasma checks after a bot fusion before plasma shows up.
        self.plasma_delay = 0
        self._plasma_countdown: dict[str, int] = {}
        self.unreceived: dict[str, list[str]] = {}
        self.balances = {
            ADDRESS_0: {
                ZNN: ("Zenon", "ZNN", 8, "1234567890123"),
                QSR: ("Quasar", "QSR", 8, "50000000"),
            }
        }
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def start(self) -> "FakeWalletApi":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def expire_tokens(self) -> None:
        self.tokens.clear()

    def calls(self, method: str, path: str) -> list[dict]:
        return [r for r in self.requests if r["method"] == method and r["path"] == path]

    # ----- request handling ---------------------------------------------

    def _handler(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:
                pass

            def _reply(self, status: int, body=None) -> None:
                data = b"" if body is None else json.dumps(body).encode()
                self.send_response(status)
                if data:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _problem(self, status: int, title: str, detail: str = "", errors=None) -> None:
                body = {"title": title, "status": status}
                if detail:
                    body["detail"] = detail
                if errors:
                    body["errors"] = errors
                self._reply(status, body)

            def _handle(self, method: str) -> None:
                parsed = urlparse(self.path)
                query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw) if raw else None
                api.requests.append(
                    {
                        "method": method,
                        "path": parsed.path,
                        "query": query,
                        "body": body,
                        "authorization": self.headers.get("Authorization"),
                    }
                )
                status, answer = api.route(method, parsed.path, query, body, self.headers.get("Authorization"))
                if isinstance(answer, tuple):
                    self._problem(status, *answer)
                else:
                    self._reply(status, answer)

            def do_GET(self) -> None:
                self._handle("GET")

            def do_POST(self) -> None:
                self._handle("POST")

        return Handler

    def route(self, method, path, query, body, authorization):
        if (method, path) == ("POST", "/api/users/authenticate"):
            self.logins += 1
            if ((body or {}).get("username"), (body or {}).get("password")) != ADMIN:
                return 401, None
            self.token_counter += 1
            token = f"token-{self.token_counter}"
            self.tokens.add(token)
            return 200, {"id": "0f8fad5b-d9cb-469f-a165-70867728950e", "username": ADMIN[0], "token": token}

        if not authorization or authorization.removeprefix("Bearer ") not in self.tokens:
            return 401, None

        parts = path.strip("/").split("/")[1:]  # without the leading "api"
        route = (method, parts[0], parts[-1] if len(parts) > 1 else "")

        if route == ("GET", "wallet", "status"):
            return 200, {"isInitialized": self.initialized, "isUnlocked": self.unlocked}
        if route == ("POST", "wallet", "init"):
            if self.initialized:
                return 409, ("Conflict", "Wallet is already initialized")
            self.initialized = True
            return 200, {"mnemonic": MNEMONIC}
        if route == ("POST", "wallet", "restore"):
            self.initialized = True
            return 200, None
        if route == ("POST", "wallet", "unlock"):
            if body["password"] != WALLET_PASSWORD:
                return 403, ("Forbidden", "Incorrect password")
            self.unlocked = True
            return 200, None
        if route == ("POST", "wallet", "lock"):
            self.unlocked = False
            return 200, None
        if route == ("GET", "wallet", "accounts"):
            if not self.unlocked:
                return 409, ("Conflict", "Wallet is locked")
            entries = [{"address": address, "index": index} for index, address in enumerate(self.accounts)]
            return 200, {"list": entries, "count": len(entries)}
        if route == ("POST", "wallet", "accounts"):
            start = len(self.accounts)
            for number in range(int(query.get("numberOfAccounts", 1))):
                self.accounts.append(f"z1qnewaccount{start + number:027d}")
            added = [{"address": a, "index": i} for i, a in enumerate(self.accounts)][start:]
            return 200, {"list": added, "count": len(added)}

        if parts[0] == "ledger":
            address = parts[1]
            if route[2] == "balances":
                info = {
                    zts: {
                        "token": {"name": name, "symbol": symbol, "decimals": decimals, "tokenStandard": zts},
                        "balance": balance,
                    }
                    for zts, (name, symbol, decimals, balance) in self.balances.get(address, {}).items()
                }
                return 200, {"address": address, "accountHeight": 12, "balanceInfoMap": info}
            if route[2] == "plasma":
                remaining = self._plasma_countdown.get(address)
                if remaining is not None:
                    if remaining <= 0:
                        self.plasma[address] = 84000
                        del self._plasma_countdown[address]
                    else:
                        self._plasma_countdown[address] = remaining - 1
                current = self.plasma.get(address, 0)
                return 200, {"currentPlasma": current, "maxPlasma": current, "qsrAmount": "0"}
            if route[2] == "unreceived":
                size, index = int(query["pageSize"]), int(query["pageIndex"])
                hashes = self.unreceived.get(address, [])
                page = hashes[index * size : (index + 1) * size]
                return 200, {"list": [{"hash": h} for h in page], "count": len(page), "more": False}
            if route[2] in ("received", "fused"):
                return 200, {"list": [], "count": 0}

        if parts[0] in ("transfer", "plasma"):
            if not self.unlocked:
                return 409, ("Conflict", "Wallet is locked")
            if route[2] == "send" and body["amount"] == "999999":
                return 404, ("Not Found", "You do not have enough ZNN tokens")
            if route[2] == "receive":
                for hashes in self.unreceived.values():
                    if body["blockHash"] in hashes:
                        hashes.remove(body["blockHash"])
            return 200, {"hash": f"block-{len(self.requests)}", "address": parts[1], **(body or {})}

        if route == ("POST", "utilities", "validate"):
            address = query.get("address", "")
            return 200, {"isValid": address.startswith("z1q") and len(address) == 40, "isEmbedded": False}
        if route == ("POST", "utilities", "fuse"):
            self._plasma_countdown[body["address"]] = self.plasma_delay
            return 200, None
        if parts[:3] == ["utilities", "plasma-bot", "expiration"]:
            return 200, {"expiration": "2026-01-01T00:00:00Z" if parts[3] in self.plasma else None}
        if route == ("GET", "auto-receiver", "status"):
            return 200, {"isEnabled": True}
        if route == ("GET", "broken", "text"):
            return 500, None
        return 422, ("Validation failed", "", {"Address": ["'Address' must not be empty."]})
