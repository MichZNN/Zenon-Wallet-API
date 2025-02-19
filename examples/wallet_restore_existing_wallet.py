import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # Wallet: Restore an existing wallet
    wallet_restore = client.wallet_restore()
    if wallet_restore.get('status') == 200:
        logging.info("Wallet successfully restored!")
    else:
        logging.error(f"API call failed: {wallet_restore.get('status')}")

    client.close()