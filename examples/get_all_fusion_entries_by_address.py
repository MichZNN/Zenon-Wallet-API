import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # Ledger: Get all fusion entries by address
    fusion_entries = client.ledger_fusion_entries(client.account_address_2)
    if fusion_entries.get("status") == 200:
        logging.info(f"Fusion entries: {fusion_entries.get('data')}")
    else:
        logging.error(f"API call failed: {fusion_entries.get('status')}")

    client.close()