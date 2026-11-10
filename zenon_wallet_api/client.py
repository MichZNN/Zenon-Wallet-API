"""Client for the Zenon Wallet API.

The Wallet API is a REST service that manages a Zenon wallet and talks to a
Zenon node. This module wraps every endpoint of the API in one method and adds
a few helpers for common tasks, such as reading balances or sending tokens once
the sender has plasma.
"""

from __future__ import annotations

import logging
import os
import re
import time
from decimal import Decimal
from typing import Any, Callable
from urllib.parse import quote

import requests

from .exceptions import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    ConnectionFailed,
    PlasmaTimeout,
)
from .models import TokenBalance

logger = logging.getLogger(__name__)

# Largest page the API (and the node behind it) accepts.
MAX_PAGE_SIZE = 1024
MAX_UNRECEIVED_PAGE_SIZE = 50

# The API accepts amounts such as "1", "1.5" and ".5" (no sign, no exponent).
_AMOUNT_PATTERN = re.compile(r"^((\d+(\.\d*)?)|(\.\d+))$")


def _format_amount(amount: str | int | Decimal) -> str:
    """Return the amount as the plain decimal string the API expects."""
    if isinstance(amount, bool) or isinstance(amount, float):
        raise TypeError("amount must be a str, int or Decimal; floats lose precision")
    if isinstance(amount, Decimal):
        text = format(amount, "f")
    elif isinstance(amount, (int, str)):
        text = str(amount).strip()
    else:
        raise TypeError(f"amount must be a str, int or Decimal, got {type(amount).__name__}")
    if not _AMOUNT_PATTERN.match(text):
        raise ValueError(f"amount must be a positive decimal number, got {amount!r}")
    if Decimal(text) <= 0:
        raise ValueError("amount must be greater than zero")
    return text


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _account_segment(account: str | int) -> str:
    """An account is addressed by its address or by its index in the wallet."""
    if isinstance(account, bool):
        raise TypeError("account must be an address or an account index")
    if isinstance(account, int):
        if account < 0:
            raise ValueError("account index must be 0 or higher")
        return str(account)
    return quote(_require_text(account, "account"), safe="")


def _page_parameters(page_index: int, page_size: int, max_page_size: int) -> dict[str, int]:
    for name, value in (("page_index", page_index), ("page_size", page_size)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    if page_index < 0:
        raise ValueError("page_index must be 0 or higher")
    if not 1 <= page_size <= max_page_size:
        raise ValueError(f"page_size must be between 1 and {max_page_size}")
    return {"pageIndex": page_index, "pageSize": page_size}


class ZenonWalletClient:
    """Talks to one Wallet API server as one user.

    The client signs in on the first request and again whenever the server
    reports that the token has expired. Every method returns the decoded JSON
    answer of the API (``None`` for an empty answer) and raises
    :class:`~zenon_wallet_api.ApiError` when the API reports an error.

    Use it as a context manager to close the HTTP session when done::

        with ZenonWalletClient.from_env() as client:
            print(client.wallet_status())
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        wallet_password: str | None = None,
        default_address: str | None = None,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        """
        :param base_url: Address of the Wallet API, for example ``https://localhost:443``.
        :param username: API user to sign in with.
        :param password: Password of that API user.
        :param wallet_password: Password of the wallet itself, used to initialize,
            restore and unlock it. Can also be passed to those methods directly.
        :param default_address: Optional address of the wallet account you use most.
        :param timeout: Seconds to wait for an answer before giving up.
        :param session: Optional ``requests.Session``, for custom TLS or proxy settings.
        """
        base_url = (base_url or "").strip().rstrip("/")
        if not re.match(r"^https?://[^/]", base_url):
            raise ConfigurationError("base_url must start with http:// or https:// and name a host")
        if not username or not password:
            raise ConfigurationError("username and password are required")
        self.base_url = base_url
        self.username = username
        self._password = password
        self._wallet_password = wallet_password or None
        self.default_address = default_address or None
        self.timeout = timeout
        self._session = session or requests.Session()
        self._token: str | None = None

    # ----- construction and lifetime ------------------------------------

    @classmethod
    def from_env(cls, env_file: str | os.PathLike | None = None, *, role: str = "admin", **kwargs):
        """Create a client from ``ZENON_WALLET_API_*`` environment variables.

        A ``.env`` file is loaded first when python-dotenv is installed:
        ``env_file`` when given, otherwise the nearest ``.env`` above the
        current directory. Variables that are already set are not overwritten.

        :param role: ``"admin"`` or ``"user"``; selects which credentials are used.
            The API checks roles strictly: initializing and restoring a wallet need
            the Admin role, every other call needs the User role.
        """
        role = role.lower()
        if role not in ("admin", "user"):
            raise ConfigurationError("role must be 'admin' or 'user'")
        try:
            from dotenv import find_dotenv, load_dotenv
        except ImportError:
            if env_file is not None:
                raise ConfigurationError("python-dotenv is required to load an env file") from None
        else:
            load_dotenv(env_file if env_file is not None else find_dotenv(usecwd=True))

        suffix = role.upper()
        settings = {
            "base_url": os.getenv("ZENON_WALLET_API_URL", ""),
            "username": os.getenv(f"ZENON_WALLET_API_USERNAME_{suffix}", ""),
            "password": os.getenv(f"ZENON_WALLET_API_PASSWORD_{suffix}", ""),
        }
        missing = [
            name
            for name, value in (
                ("ZENON_WALLET_API_URL", settings["base_url"]),
                (f"ZENON_WALLET_API_USERNAME_{suffix}", settings["username"]),
                (f"ZENON_WALLET_API_PASSWORD_{suffix}", settings["password"]),
            )
            if not value.strip()
        ]
        if missing:
            raise ConfigurationError("Missing environment variables: " + ", ".join(missing))
        kwargs.setdefault("wallet_password", os.getenv("ZENON_WALLET_API_SECRET") or None)
        kwargs.setdefault("default_address", os.getenv("ZENON_WALLET_API_ADDRESS") or None)
        return cls(**settings, **kwargs)

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "ZenonWalletClient":
        return self

    def __exit__(self, *_exc_info) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"ZenonWalletClient(base_url={self.base_url!r}, username={self.username!r})"

    # ----- transport ----------------------------------------------------

    def authenticate(self) -> str:
        """Sign in and remember the bearer token for the following requests."""
        answer = self._send(
            "POST",
            "/api/users/authenticate",
            json={"username": self.username, "password": self._password},
            authenticated=False,
        )
        token = answer.get("token") if isinstance(answer, dict) else None
        if not token:
            raise AuthenticationError(200, detail="The API did not return a token")
        self._token = token
        return token

    def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        authenticated: bool = True,
    ) -> Any:
        """Send one request and return the decoded answer."""
        if authenticated and self._token is None:
            self.authenticate()

        response = self._perform(method, path, params, json, authenticated)
        if response.status_code == 401 and authenticated:
            # The token has expired (or was revoked): sign in again and retry once.
            self._token = None
            self.authenticate()
            response = self._perform(method, path, params, json, authenticated)

        logger.debug("%s %s -> %s", method, path, response.status_code)
        if not response.ok:
            raise self._error_from(response, signing_in=not authenticated)
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    def _perform(self, method, path, params, json, authenticated) -> requests.Response:
        headers = {"Accept": "application/json"}
        if authenticated and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            return self._session.request(
                method,
                self.base_url + path,
                params=params,
                json=json,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise ConnectionFailed(f"{method} {path} failed: {error}") from error

    @staticmethod
    def _error_from(response: requests.Response, *, signing_in: bool) -> ApiError:
        try:
            body = response.json()
        except ValueError:
            body = response.text
        title = detail = ""
        errors = None
        if isinstance(body, dict):
            title = str(body.get("title") or "")
            detail = str(body.get("detail") or "")
            errors = body.get("errors") if isinstance(body.get("errors"), dict) else None
        elif isinstance(body, str):
            detail = body.strip()[:300]
        if response.status_code == 401:
            detail = detail or ("Invalid username or password" if signing_in else "Not authorized")
            return AuthenticationError(401, title, detail, errors, body)
        return ApiError(response.status_code, title, detail, errors, body)

    def _wallet_password_or(self, password: str | None) -> str:
        password = password or self._wallet_password
        if not password:
            raise ConfigurationError(
                "A wallet password is required: pass it to this method, to the client "
                "(wallet_password=...) or set ZENON_WALLET_API_SECRET"
            )
        return password

    # ----- wallet -------------------------------------------------------

    def wallet_status(self) -> dict:
        """Return whether the wallet is initialized and unlocked.

        Example answer: ``{"isInitialized": True, "isUnlocked": False}``.
        """
        return self._send("GET", "/api/wallet/status")

    def wallet_initialize(self, password: str | None = None) -> str:
        """Create a new wallet and return its mnemonic. Requires the admin role.

        Store the mnemonic safely: it is the only way to restore the wallet. The
        password needs at least 8 characters with a letter, a digit and one of
        ``@$!%*#?&``.
        """
        answer = self._send("POST", "/api/wallet/init", json={"password": self._wallet_password_or(password)})
        return answer["mnemonic"]

    def wallet_restore(self, mnemonic: str, password: str | None = None) -> None:
        """Restore a wallet from its mnemonic. Requires the admin role."""
        self._send(
            "POST",
            "/api/wallet/restore",
            json={"password": self._wallet_password_or(password), "mnemonic": _require_text(mnemonic, "mnemonic")},
        )

    def wallet_unlock(self, password: str | None = None) -> None:
        """Unlock the wallet so it can sign transactions."""
        self._send("POST", "/api/wallet/unlock", json={"password": self._wallet_password_or(password)})

    def wallet_lock(self) -> None:
        """Lock the wallet."""
        self._send("POST", "/api/wallet/lock")

    def wallet_accounts(self, page_index: int = 0, page_size: int = MAX_PAGE_SIZE) -> dict:
        """Return the accounts of the wallet: ``{"list": [{"address", "index"}], "count"}``.

        The wallet has to be initialized and unlocked.
        """
        return self._send(
            "GET", "/api/wallet/accounts", params=_page_parameters(page_index, page_size, MAX_PAGE_SIZE)
        )

    def wallet_add_accounts(self, count: int = 1) -> dict:
        """Add ``count`` new accounts to the wallet and return the added accounts."""
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("count must be an integer")
        if count < 1:
            raise ValueError("count must be 1 or higher")
        return self._send("POST", "/api/wallet/accounts", params={"numberOfAccounts": count})

    # ----- ledger -------------------------------------------------------

    def account_info(self, address: str) -> dict:
        """Return the account height and the balance of every token on an address."""
        return self._send("GET", f"/api/ledger/{_account_segment(address)}/balances")

    def received_account_blocks(
        self, address: str, page_index: int = 0, page_size: int = MAX_PAGE_SIZE
    ) -> dict:
        """Return the account blocks of an address, newest first."""
        return self._send(
            "GET",
            f"/api/ledger/{_account_segment(address)}/received",
            params=_page_parameters(page_index, page_size, MAX_PAGE_SIZE),
        )

    def unreceived_account_blocks(
        self, address: str, page_index: int = 0, page_size: int = MAX_UNRECEIVED_PAGE_SIZE
    ) -> dict:
        """Return the blocks that were sent to an address but not yet received by it."""
        return self._send(
            "GET",
            f"/api/ledger/{_account_segment(address)}/unreceived",
            params=_page_parameters(page_index, page_size, MAX_UNRECEIVED_PAGE_SIZE),
        )

    def plasma_info(self, address: str) -> dict:
        """Return ``currentPlasma``, ``maxPlasma`` and ``qsrAmount`` of an address."""
        return self._send("GET", f"/api/ledger/{_account_segment(address)}/plasma")

    def fusion_entries(self, address: str, page_index: int = 0, page_size: int = MAX_PAGE_SIZE) -> dict:
        """Return the plasma fusions made by an address (QSR it fused for itself or others)."""
        return self._send(
            "GET",
            f"/api/ledger/{_account_segment(address)}/fused",
            params=_page_parameters(page_index, page_size, MAX_PAGE_SIZE),
        )

    # ----- transfers ----------------------------------------------------

    def send(
        self,
        account: str | int,
        to_address: str,
        amount: str | int | Decimal,
        token_standard: str = "ZNN",
    ) -> dict:
        """Send tokens from a wallet account and return the published account block.

        :param account: Address or index of the sending wallet account.
        :param to_address: Address that receives the tokens.
        :param amount: Amount in whole tokens, for example ``"1.5"``.
        :param token_standard: ``"ZNN"``, ``"QSR"`` or a ZTS such as ``zts1...``.

        The wallet has to be unlocked. Without plasma the API generates proof of
        work for the sender, which can take a while.
        """
        return self._send(
            "POST",
            f"/api/transfer/{_account_segment(account)}/send",
            json={
                "address": _require_text(to_address, "to_address"),
                "amount": _format_amount(amount),
                "tokenStandard": _require_text(token_standard, "token_standard"),
            },
        )

    def receive(self, account: str | int, block_hash: str) -> dict:
        """Receive one unreceived block on a wallet account.

        Only needed when the auto-receiver of the API is disabled. Block hashes
        come from :meth:`unreceived_account_blocks`.
        """
        return self._send(
            "POST",
            f"/api/transfer/{_account_segment(account)}/receive",
            json={"blockHash": _require_text(block_hash, "block_hash")},
        )

    # ----- plasma -------------------------------------------------------

    def fuse_plasma(self, account: str | int, beneficiary: str, amount: str | int | Decimal) -> dict:
        """Fuse QSR of a wallet account to give ``beneficiary`` plasma.

        :param account: Address or index of the wallet account that owns the QSR.
        :param beneficiary: Address that gets the plasma (can be the account itself).
        :param amount: Amount of QSR to fuse, in whole QSR.
        """
        return self._send(
            "POST",
            f"/api/plasma/{_account_segment(account)}/fuse",
            json={"address": _require_text(beneficiary, "beneficiary"), "amount": _format_amount(amount)},
        )

    def cancel_plasma(self, account: str | int, id_hash: str) -> dict:
        """Cancel a plasma fusion and get the QSR back.

        ``id_hash`` is the ``id`` of an entry from :meth:`fusion_entries`. A fusion
        can only be cancelled after its lock period has passed.
        """
        return self._send(
            "POST",
            f"/api/plasma/{_account_segment(account)}/cancel",
            json={"idHash": _require_text(id_hash, "id_hash")},
        )

    # ----- utilities ----------------------------------------------------

    def validate_address(self, address: str) -> dict:
        """Check an address: ``{"isValid": bool, "isEmbedded": bool}``."""
        return self._send(
            "POST", "/api/utilities/address/validate", params={"address": _require_text(address, "address")}
        )

    def plasma_bot_fuse(self, address: str) -> None:
        """Ask the community plasma bot to fuse temporary plasma for an address."""
        self._send("POST", "/api/utilities/plasma-bot/fuse", json={"address": _require_text(address, "address")})

    def plasma_bot_expiration(self, address: str) -> dict:
        """Return when the plasma-bot fusion of an address expires: ``{"expiration": str | None}``."""
        return self._send("GET", f"/api/utilities/plasma-bot/expiration/{_account_segment(address)}")

    def auto_receiver_status(self) -> dict:
        """Return whether the API receives incoming blocks by itself: ``{"isEnabled": bool}``."""
        return self._send("GET", "/api/auto-receiver/status")

    # ----- helpers built on the endpoints -------------------------------

    def ensure_unlocked(self, password: str | None = None) -> bool:
        """Unlock the wallet when it is locked. Returns True when it had to unlock."""
        status = self.wallet_status()
        if not status.get("isInitialized"):
            raise ConfigurationError("The wallet is not initialized yet")
        if status.get("isUnlocked"):
            return False
        self.wallet_unlock(password)
        return True

    def balances(self, address: str) -> list[TokenBalance]:
        """Return the token balances of an address as exact decimal values."""
        info = self.account_info(address)
        balances = []
        for token_standard, entry in (info.get("balanceInfoMap") or {}).items():
            token = entry.get("token") or {}
            balances.append(
                TokenBalance(
                    token_standard=token.get("tokenStandard") or token_standard,
                    name=str(token.get("name", "")),
                    symbol=str(token.get("symbol", "")),
                    decimals=int(token.get("decimals", 0)),
                    raw_balance=int(entry.get("balance", 0)),
                )
            )
        return balances

    def has_plasma(self, address: str) -> bool:
        """True when the address currently has plasma."""
        return int(self.plasma_info(address).get("currentPlasma") or 0) > 0

    def wait_for_plasma(
        self,
        address: str,
        timeout: float = 1800.0,
        interval: float = 30.0,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Wait until the address has plasma; raise :class:`PlasmaTimeout` after ``timeout`` seconds."""
        deadline = time.monotonic() + timeout
        while not self.has_plasma(address):
            if time.monotonic() + interval > deadline:
                raise PlasmaTimeout(f"{address} has no plasma after {int(timeout)} seconds")
            logger.info("Waiting for plasma on %s; checking again in %s seconds", address, interval)
            sleep(interval)

    def ensure_plasma(self, address: str, timeout: float = 1800.0, interval: float = 30.0, **kwargs) -> bool:
        """Make sure the address has plasma, asking the plasma bot when it has none.

        Returns True when the plasma bot had to be used.
        """
        if self.has_plasma(address):
            return False
        self.plasma_bot_fuse(address)
        self.wait_for_plasma(address, timeout, interval, **kwargs)
        return True

    def account_address(self, account: str | int) -> str:
        """Return the address of a wallet account given its address or index."""
        if isinstance(account, str):
            return _require_text(account, "account")
        _account_segment(account)
        page_index = 0
        while True:
            page = self.wallet_accounts(page_index)
            entries = page.get("list") or []
            for entry in entries:
                if entry.get("index") == account:
                    return entry["address"]
            if len(entries) < MAX_PAGE_SIZE:
                raise ValueError(f"The wallet has no account with index {account}")
            page_index += 1

    def send_with_plasma(
        self,
        account: str | int,
        to_address: str,
        amount: str | int | Decimal,
        token_standard: str = "ZNN",
        *,
        timeout: float = 1800.0,
        interval: float = 30.0,
        **kwargs,
    ) -> dict:
        """Send tokens after making sure the sending account has plasma.

        A send block is paid for with the plasma of the sender. When the sender
        has none, the plasma bot is asked for a temporary fusion first, so the
        API does not have to fall back to slow proof of work.
        """
        # Check the arguments before any waiting starts.
        _format_amount(amount)
        _require_text(to_address, "to_address")
        self.ensure_plasma(self.account_address(account), timeout, interval, **kwargs)
        return self.send(account, to_address, amount, token_standard)

    def receive_all(self, account: str | int) -> list[dict]:
        """Receive every block that is waiting for a wallet account.

        Returns the published receive blocks. Blocks that arrive while this
        runs are left for the next call.
        """
        address = self.account_address(account)
        pending: list[dict] = []
        page_index = 0
        while True:
            page = self.unreceived_account_blocks(address, page_index).get("list") or []
            pending.extend(page)
            if len(page) < MAX_UNRECEIVED_PAGE_SIZE:
                break
            page_index += 1
        return [self.receive(account, block["hash"]) for block in pending]
