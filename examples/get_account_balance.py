import logging
from module import ZenonWalletClient

if __name__ == "__main__":
    client = ZenonWalletClient()

    # address = client.test_address
    address = "z1qp7qzapasd2ausazxw65m2hv7f4g4u8eg244qs"

    # Ledger: Get the account info by address
    ledger_account_info = client.ledger_account_info(address)
    if ledger_account_info.get('status') == 200:
        data = ledger_account_info.get('data')
        balance_info_map = data.get('balanceInfoMap')
        token_count = len(balance_info_map)

        print("Number of tokens:", token_count)

        for token_standard, info in balance_info_map.items():
            token_name = info["token"]["name"]
            token_symbol = info["token"]["symbol"]
            token_decimals = info["token"]["decimals"]
            raw_balance_str = info["balance"]
            balance_value = int(raw_balance_str) / (10 ** token_decimals)
            
            print("---")
            print(f"Token Standard: {token_standard}")
            print(f"  Name: {token_name}")
            print(f"  Symbol: {token_symbol}")
            print(f"  Decimals: {token_decimals}")
            print(f"  Balance: {balance_value}")


    else:
        logging.error(f"API call failed: {ledger_account_info.get('status')}")

    client.close()