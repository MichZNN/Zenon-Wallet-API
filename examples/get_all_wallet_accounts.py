import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # Wallet: Get all wallet accounts
    # Requires Wallet to be initialized and unlocked
    wallet_accounts = client.wallet_accounts()
    if wallet_accounts.get("status") == 200:
        logging.info(f"Wallet accounts: {wallet_accounts.get('data')}")
    else:
        logging.error(f"API call failed: {wallet_accounts.get('status')}")

    client.close()