import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    address = client.address

    # Ledger: Get all unreceived account blocks by address
    ledger_unreceived_account_blocks = client.ledger_unreceived_account_blocks(address, pageIndex=0, pageSize=1)
    if ledger_unreceived_account_blocks.get('status') == 200:
        logging.info(f"Unreceived account blocks: {ledger_unreceived_account_blocks.get('data')}")
    else:
        logging.error(f"API call failed: {ledger_unreceived_account_blocks.get('status')}")

    client.close()