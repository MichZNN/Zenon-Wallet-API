import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # Wallet: Unlock the wallet
    wallet_unlock = client.wallet_unlock()
    if wallet_unlock.get("status") == 200:
        logging.info(f"Wallet successfully unlocked!")
    else:
        logging.error(f"API call failed: {wallet_unlock.get('status')}")

    client.close()