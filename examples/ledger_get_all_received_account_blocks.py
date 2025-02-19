import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    address = client.test_address

    # Ledger: Get all received account blocks by address
    ledger_received_account_blocks = client.ledger_received_account_blocks(address, pageIndex=0, pageSize=1)
    if ledger_received_account_blocks.get('status') == 200:
        logging.info(f"Received account blocks: {ledger_received_account_blocks.get('data')}")
    else:
        logging.error(f"API call failed: {ledger_received_account_blocks.get('status')}")

    client.close()