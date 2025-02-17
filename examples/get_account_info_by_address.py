import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    address = client.test_address

    # Ledger: Get the account info by address
    ledger_account_info = client.ledger_account_info(address)
    if ledger_account_info.get('status') == 200:
        logging.info(f"Ledger account info {address}: {ledger_account_info.get('data')}")
    else:
        logging.error(f"API call failed: {ledger_account_info.get('status')}")

    client.close()