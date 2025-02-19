import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    address = client.test_address

    # Utilities : Get the fusion expiration by address from the plasma-bot
    fusion_expiration = client.fusion_expiration(address)
    if fusion_expiration.get('status') == 200:
        logging.info(f"Fusion expiration {address}: {fusion_expiration.get('data')}")
    else:
        logging.error(f"API call failed: {fusion_expiration.get('status')}")

    client.close()