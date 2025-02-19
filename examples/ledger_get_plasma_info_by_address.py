import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    address = client.address

    # Ledger: Get plasma info by address
    ledger_plasma_info = client.ledger_plasma_info(address)
    if ledger_plasma_info.get('status') == 200:
        logging.info(f"Ledger plasma info {address}: {ledger_plasma_info.get('data')}")
    else:
        logging.error(f"API call failed: {ledger_plasma_info.get('status')}")

    client.close()