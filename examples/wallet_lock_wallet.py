import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # Wallet: Lock the wallet
    wallet_lock = client.wallet_lock()
    if wallet_lock.get('status') == 200:
        logging.info("Wallet successfully locked!")
    else:
        logging.error(f"API call failed: {wallet_lock.get('status')}")

    client.close()