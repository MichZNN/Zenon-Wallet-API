import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # Wallet: Get wallet status
    wallet_status = client.wallet_status()
    if wallet_status.get("status") == 200:
        logging.info(f"Wallet status: {wallet_status.get('data')}")
    else:
        logging.error(f"API call failed: {wallet_status.get('status')}")

    # Wallet : Unlock the wallet
    if not wallet_status.get("data", {}).get("isUnlocked"):
        wallet_unlock = client.wallet_unlock()
        if wallet_unlock.get("status") == 200:
            logging.info("Wallet successfully unlocked!")
        else:
            logging.error(f"Failed to unlock wallet: {wallet_unlock.get('status')}")

    # Wallet: Get all wallet accounts
    wallet_accounts = client.wallet_accounts()
    if wallet_accounts.get("status") == 200:
        logging.info(f"Wallet accounts: {wallet_accounts.get('data')}")
        try:
            first_account = wallet_accounts.get("data", {}).get("list", [])[0]
            first_address = first_account.get("address", "")
            if first_address != client.address:
                logging.error(f"Wrong wallet unlocked: {first_address}. Expected: {client.address}")
        except (IndexError, AttributeError):
            logging.error("No wallet accounts found.")
    else:
        logging.error(f"API call failed: {wallet_accounts.get('status')}")

    # Ledger: Get plasma info
    ledger_plasma = client.ledger_plasma_info()
    if ledger_plasma.get("status") == 200:
        logging.info(f"Ledger plasma info {client.address}: {ledger_plasma.get('data')}")
        if not ledger_plasma.get("data", {}).get("currentPlasma"):
            plasma_response = client.fuse_plasma()
            if plasma_response.get("status") == 200:
                logging.info(f"Generated plasma for {client.address}: {plasma_response.get('data')}")
            else:
                logging.error(f"API call failed: {plasma_response.get('status')}")
    else:
        logging.error(f"API call failed: {ledger_plasma.get('status')}")

    client.close()