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
        self.test_address = os.getenv("ZENON_WALLET_TEST_ADDRESS")
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
    def wallet_initialize(self):
        """Sends a request to initialize a new wallet"""
        return self.request("/api/wallet/init", method="POST", payload={"password": self.secret})

    def wallet_status(self):
        """Retrieves the wallet status."""
        return self.request("/api/wallet/status")

    def wallet_unlock(self):
        """Sends a request to unlock the wallet."""
        return self.request("/api/wallet/unlock", method="POST", payload={"password": self.secret})

    def wallet_lock(self):
        """Sends a request to lock the wallet"""
        return self.request("/api/wallet/lock", method="POST")

    def wallet_restore(self):
        """Sends a request to restore an existing wallet"""
        return self.request("/api/wallet/restore", method="POST", payload={"password": self.secret, "mnemonic": os.getenv("ZENON_WALLET_API_MNEMONIC")})

    def wallet_add_accounts(self):
        """Add new accounts to wallet."""
        return self.request("/api/wallet/accounts", method="POST")

    def wallet_accounts(self):
        """Retrieves the list of wallet accounts."""
        return self.request("/api/wallet/accounts")

    def fusion_expiration(self, address):
        """Get the fusion expiration by address from the plasma-bot"""
        return self.request(f"/api/utilities/plasma-bot/expiration/{address}")

    def ledger_account_info(self, address):
        """Get the account info by address"""
        return self.request((f"/api/ledger/{address}/balances"))

    def ledger_plasma_info(self, address):
        """Retrieves plasma information for the wallet address."""
        return self.request(f"/api/ledger/{address}/plasma")

    def generate_plasma_bot(self):
        """Generate plasma by fusing QSR from the plasma-bot"""
        return self.request("/api/utilities/plasma-bot/fuse", method="POST", payload={"address": self.address})

    def generate_plasma_qsr(self):
        """Generate plasma by fusing QSR from wallet address"""
        return self.request(f"/api/plasma/{self.address}/fuse", method="POST")

    def cancel_plasma_fusion(self):
        """Send requests to cancel plasma fusion from wallet address"""
        return self.request(f"/api/plasma/{self.address}/cancel", method="POST")

    def validate_address(self, address):
        """Validate an wallet address"""
        return self.request(f"/api/utilities/address/validate?address={address}", method="POST")

    def send_tokens(self, receiver_address=None, amount=0.00000001, tokenStandard="ZNN"):
        if receiver_address and amount >= 0.00000001:
            return self.request(f"/api/transfer/{self.address}/send", method="POST", payload={"address": receiver_address, "amount": amount, "tokenStandard": tokenStandard})
        else:
            return False

    def close(self):
        """Closes the session."""
        self.session.close()