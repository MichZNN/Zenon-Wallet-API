import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # Wallet: Get all wallet accounts
    wallet_accounts = client.wallet_accounts()
    if wallet_accounts.get("status") == 200:
        logging.info(f"Wallet accounts: {wallet_accounts.get('data')}")
        try:
            # Get first account
            first_account = wallet_accounts.get("data", {}).get("list", [])[0]
            # Get first address
            first_address = first_account.get("address", "")
            # Check if address is the same as defined as client address
            if first_address != client.address:
                logging.error(f"Wrong wallet unlocked: {first_address}. Expected: {client.address}")
        except (IndexError, AttributeError):
            logging.error("No wallet accounts found.")
    else:
        logging.error(f"API call failed: {wallet_accounts.get('status')}")

    client.close()