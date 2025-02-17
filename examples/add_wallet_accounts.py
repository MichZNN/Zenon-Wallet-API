import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # Wallet: Add wallet accounts
    # Requires Wallet to be initialized and unlocked
    wallet_add_accounts = client.wallet_add_accounts()
    if wallet_add_accounts.get('status') == 200:
        logging.info(f"Wallet add accounts: {wallet_add_accounts.get('data')}")
    else:
        logging.error(f"API call failed: {wallet_add_accounts.get('status')}")

    client.close()