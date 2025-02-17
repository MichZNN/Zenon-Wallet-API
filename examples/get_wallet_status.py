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

    client.close()