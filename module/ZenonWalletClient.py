import os
import sys
import logging
import urllib.parse
import requests
import json
from dotenv import load_dotenv, find_dotenv

class ZenonWalletClient:

    def __init__(self):
        """
        Initializes the client, checks if all required environment variables are set,
        and ensures a valid session with authentication.
        """
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

        try:
            # Attempt to locate the .env file, and raise an error if it is not found.
            env_file = find_dotenv(raise_error_if_not_found=True)
            load_dotenv(env_file)
            logging.info("Environment variables loaded from .env file.")
        except Exception as e:
            logging.error(f"Failed to load environment variables from .env file: {e}")
            sys.exit(1)

        self.username = os.getenv("ZENON_WALLET_API_USERNAME_ADMIN")
        self.password = os.getenv("ZENON_WALLET_API_PASSWORD_ADMIN")
        self.api_url = os.getenv("ZENON_WALLET_API_URL")
        self.secret = os.getenv("ZENON_WALLET_API_SECRET")
        self.address = os.getenv("ZENON_WALLET_API_ADDRESS")

        self.test_address = "z1qqjnwjjpnue8xmmpanz6csze6tcmtzzdtfsww7"
        self.account_address_1 = "z1qr00j9wkcyvgz567sygnjxshnkq3xqxsc0t7cv"
        self.account_address_2 = "z1qzg4377yxss6m0duu38ntc0zu3s0thn9rwze3f"

        self.session = requests.Session()

        # Authenticate if no token is present in the session headers
        if not self.session.headers.get("Authorization"):
            self.authenticate()

    def authenticate(self):
        """
        Authenticates the user using admin credentials and updates the session headers with the token.
        """

        endpoint = "/api/users/authenticate"
        url = urllib.parse.urljoin(self.api_url, endpoint)

        payload = json.dumps({
            "username": self.username,
            "password": self.password
        })
        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = self.session.post(url, headers=headers, data=payload)
            logging.info(f"Authentication response: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            token = data.get("token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                return token
            else:
                logging.error(f"Authentication failed: {data}")
                return None

        except requests.exceptions.JSONDecodeError:
            logging.error("Failed to parse response: Invalid or unexpected JSON format")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return None

    def request(self, endpoint, method="GET", payload=None):
        """
        Performs an API request with the specified endpoint and method.
        This method builds the full URL, sends the request,
        and handles the response (including error handling and JSON decoding).
        """
        url = urllib.parse.urljoin(self.api_url, endpoint)
        try:
            if method.upper() == "POST":
                response = self.session.post(url, json=payload)
            else:
                response = self.session.get(url)
            
            logging.info(f"API Response ({method} {endpoint}): {response.status_code}")
            response.raise_for_status()

            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError:
                logging.warning(f"Response from {endpoint} is not JSON. Returning raw text.")
                data = response.text

            return {"status": response.status_code, "data": data}

        except requests.exceptions.RequestException as e:
            logging.error(f"Request to {endpoint} failed: {e}")
            return {"status": None, "data": None}

    # Specific API methods

    # AutoReceiver
    def get_autoreceiver_status(self):
        """Get the auto-receiver status"""
        return self.request(f"/api/auto-receiver/status")

    # Plasma
    def generate_plasma_qsr(self, address):
        """Generate plasma by fusing QSR from wallet address"""
        return self.request(f"/api/plasma/{address}/fuse", method="POST")

    def cancel_plasma_fusion(self, address, idHash): # Untested
        """Send requests to cancel plasma fusion from wallet address"""
        return self.request(f"/api/plasma/{address}/cancel", method="POST", payload={"idHash": idHash})

    # Ledger
    def ledger_account_info(self, address):
        """Get the account info by address"""
        return self.request(f"/api/ledger/{address}/balances")

    def ledger_received_account_blocks(self, address, **kwargs):
        """
        Get all received account blocks by address

        :param address: (str, required)
        :param pageIndex: (int, default=0)
        :param pageSize: (int, default=1024, must be between 1 and 1024 inclusive)
        """
        pageIndex = kwargs.get('pageIndex', 0)
        pageSize = kwargs.get('pageSize', 1024)

        if not isinstance(pageIndex, int):
            raise TypeError(f"pageIndex must be an integer, got {type(pageIndex).__name__}")

        if not isinstance(pageSize, int):
            raise TypeError(f"pageSize must be an integer, got {type(pageSize).__name__}")

        if not (1 <= pageSize <= 1024):
            raise ValueError("pageSize must be between 1 and 1024")

        return self.request(f"/api/ledger/{address}/received?pageIndex={pageIndex}&pageSize={pageSize}")

    def ledger_unreceived_account_blocks(self, address, **kwargs):
        """
        Get all unreceived account blocks by address

        :param address: (str, required)
        :param pageIndex: (int, default=0)
        :param pageSize: (int, default=50, must be between 1 and 50 inclusive)
        """
        pageIndex = kwargs.get('pageIndex', 0)
        pageSize = kwargs.get('pageSize', 50)

        if not isinstance(pageIndex, int):
            raise TypeError(f"pageIndex must be an integer, got {type(pageIndex).__name__}")

        if not isinstance(pageSize, int):
            raise TypeError(f"pageSize must be an integer, got {type(pageSize).__name__}")

        if not (1 <= pageSize <= 50):
            raise ValueError("pageSize must be between 1 and 50")
            
        return self.request(f"/api/ledger/{address}/unreceived?pageIndex={pageIndex}&pageSize={pageSize}")

    def ledger_plasma_info(self, address):
        """Retrieves plasma information for the wallet address."""
        return self.request(f"/api/ledger/{address}/plasma")

    def ledger_fusion_entries(self, address):
        """Get all fusion entries by address"""
        return self.request(f"/api/ledger/{address}/fused")

    # Transfer
    def send_tokens(self, **kwargs):
        """
        Send tokens to an wallet address
        :param sender: (str, optional) Defaults to the wallet's primary address
        :param receiver: (str, required) The recipient address
        :param amount: (str, optional) The amount to send; default is "0.00000001" and must be a valid float >= 0.00000001
        :param tokenStandard: (str, optional) Defaults to "ZNN"
        """
        sender_address = kwargs.get("sender", self.address)
        receiver_address = kwargs.get("receiver")
        amount = kwargs.get("amount", "0.00000001")
        tokenStandard = kwargs.get("tokenStandard", "ZNN")

        if not isinstance(amount, str):
            raise TypeError(f"amount must be a string, got {type(amount).__name__}")

        try:
            parsed_amount = float(amount)
        except ValueError:
            raise ValueError(f"amount must be a valid numeric string, got '{amount}'")

        if parsed_amount < 0.00000001:
            raise ValueError("amount must be at least 0.00000001")

        if not receiver_address:
            raise ValueError("receiver is required and must be a valid address")

        return self.request(f"/api/transfer/{sender_address}/send", method="POST", payload={"address": receiver_address, "amount": amount, "tokenStandard": tokenStandard})

    def receive_account_block(self, address, blockHash):
        """
        Receive an account block by block hash
        Requires Wallet to be initialized and unlocked
        `blockHash` can be received from `ledger_unreceived_account_blocks`. Only needed when auto-receiver is disabled
        """
        return self.request(f"/api/transfer/{address}/receive", method="POST", payload={"blockHash": blockHash})

    # Wallet
    def wallet_status(self):
        """Retrieves the wallet status."""
        return self.request("/api/wallet/status")

    def wallet_accounts(self):
        """Retrieves the list of wallet accounts."""
        return self.request("/api/wallet/accounts")

    def wallet_add_accounts(self):
        """Add new accounts to wallet."""
        return self.request("/api/wallet/accounts", method="POST")

    def wallet_initialize(self):
        """Sends a request to initialize a new wallet"""
        return self.request("/api/wallet/init", method="POST", payload={"password": self.secret})

    def wallet_restore(self):
        """Sends a request to restore an existing wallet"""
        return self.request("/api/wallet/restore", method="POST", payload={"password": self.secret, "mnemonic": os.getenv("ZENON_WALLET_API_MNEMONIC")})

    def wallet_lock(self):
        """Sends a request to lock the wallet"""
        return self.request("/api/wallet/lock", method="POST")

    def wallet_unlock(self):
        """Sends a request to unlock the wallet."""
        return self.request("/api/wallet/unlock", method="POST", payload={"password": self.secret})

    # Utilities
    def generate_plasma_bot(self, address):
        """Generate plasma by fusing QSR from the plasma-bot"""
        return self.request("/api/utilities/plasma-bot/fuse", method="POST", payload={"address": address})

    def fusion_expiration(self, address):
        """Get the fusion expiration by address from the plasma-bot"""
        return self.request(f"/api/utilities/plasma-bot/expiration/{address}")

    def validate_address(self, address):
        """Validate an wallet address"""
        return self.request(f"/api/utilities/address/validate?address={address}", method="POST")

    # Close
    def close(self):
        """Closes the session."""
        self.session.close()