import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # Wallet: Initializing a wallet creates a new encrypted wallet file with a random seed
    # Returns mnemonic
    wallet_initialize = client.wallet_initialize()
    if wallet_initialize.get('status') == 200:
        logging.info("New wallet successfully initialized!")
    else:
        logging.error(f"API call failed: {wallet_initialize.get('status')}")

    client.close()