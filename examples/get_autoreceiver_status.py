import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # AutoReceiver: Get the auto-receiver status
    autoreceiver_status = client.get_autoreceiver_status()
    if autoreceiver_status.get("status") == 200:
        logging.info(f"Auto-receiver status: {autoreceiver_status.get('data')}")
    else:
        logging.error(f"API call failed: {autoreceiver_status.get('status')}")

    client.close()