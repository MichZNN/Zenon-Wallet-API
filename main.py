import logging
import time
from module import ZenonWalletClient

def get_current_plasma(address):
    """Ledger: Get plasma info by address"""
    ledger_plasma_info = client.ledger_plasma_info(address)
    if ledger_plasma_info.get("status") == 200:
        logging.info(f"Ledger plasma info {address}: {ledger_plasma_info.get('data')}")
        return ledger_plasma_info.get("data", {}).get("currentPlasma")
    else:
        logging.error(f"API call failed: {ledger_plasma_info.get('status')}")
        return False

def get_balances(address):
    """Ledger: Get the account info by address"""
    start = time.time()
    ledger_account_info = client.ledger_account_info(address)
    end = time.time()

    print(f"Time to get ledger info: {end - start:.4f} seconds")

    start = time.time()

    if ledger_account_info.get('status') != 200:
        logging.error(f"API call failed: {ledger_account_info.get('status')}")
        return False

    data = ledger_account_info.get('data')
    balance_info_map = data.get('balanceInfoMap')
    token_count = len(balance_info_map)

    token_balances = []

    for token_standard, info in balance_info_map.items():
        token_name = info["token"]["name"]
        token_symbol = info["token"]["symbol"]
        token_decimals = info["token"]["decimals"]
        raw_balance_str = info["balance"]
        balance_value = int(raw_balance_str) / (10 ** token_decimals)

        token_balances.append({
            "name": token_name,
            "symbol": token_symbol,
            "decimals": token_decimals,
            "balance": balance_value
        })

    end = time.time()
    print(f"Time to parse balances: {end - start:.4f} seconds")
    return token_balances

def generate_plasma(address):
    """Utilities : Generate plasma for a limited amount of time to an address by fusing QSR from the community plasma-bot"""
    generate_plasma_bot = client.generate_plasma_bot(address)
    if generate_plasma_bot.get("status") == 200:
        logging.info(f"Generated plasma for {address}: {generate_plasma_bot.get('data')}")
        return generate_plasma_bot.get('data')
    else:
        logging.error(f"API call failed: {generate_plasma_bot.get('status')}")
        return False

def wait_for_plasma(address, timeout=1800, interval=120):
    """Wait for plasma with interval and timeout"""
    start_time = time.time()
    while True:
        if get_current_plasma(address):
            return True
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            return False
        logging.info(f"Waiting for plasma. Try again after {interval} seconds. (elapsed: {int(elapsed)} sec)")
        time.sleep(interval)

def send_tokens(**kwargs):
    """Send tokens to an address"""

    sender_address = kwargs.get("sender", client.address)
    receiver_address = kwargs.get("receiver")
    amount = kwargs.get("amount", "0.00000001")
    tokenStandard = kwargs.get("tokenStandard", "ZNN")
    
    transaction = client.send_tokens(**kwargs)
    if transaction.get("status") == 200:
        logging.info(f"Transaction: {amount} {tokenStandard} from {sender_address} to {receiver_address}")
        return transaction.get('data')
    else:
        logging.error(f"API call failed: {transaction.get('status')}")
        return False

def send_tokens_with_plasma(**kwargs):
    """Send tokens with plasma to an address"""

    receiver_address = kwargs.get("receiver")

    # First check if receiver_address has plasma
    if receiver_address:
        if get_current_plasma(receiver_address):
            # If plasma, send tokens
            if send_tokens(**kwargs):
                return True
        else:
            # If no plasma, generate plasma
            generate_plasma(receiver_address)
            # Wait for plasma
            if wait_for_plasma(receiver_address):
                # If plasma, send tokens
                if send_tokens(**kwargs):
                    return True
            else:
                # Timeout
                logging.error(f"Timeout. Transaction failed.")
    return False

if __name__ == "__main__":
    client = ZenonWalletClient()

    print(get_balances(client.test_address))

    # # Wallet: Get wallet status
    # wallet_status = client.wallet_status()
    # if wallet_status.get("status") == 200:
    #     logging.info(f"Wallet status: {wallet_status.get('data')}")
    # else:
    #     logging.error(f"API call failed: {wallet_status.get('status')}")

    # # Wallet : Unlock the wallet
    # if not wallet_status.get("data", {}).get("isUnlocked"):

    #     wallet_unlock = client.wallet_unlock()
    #     if wallet_unlock.get("status") == 200:
    #         logging.info("Wallet successfully unlocked!")
    #     else:
    #         logging.error(f"Failed to unlock wallet: {wallet_unlock.get('status')}")

    # sender = client.account_address_2
    # receiver = client.account_address_1
    # amount = "0.00000001"
    # tokenStandard = "ZNN"
    # for attempt in range(1, 11):
    #     if send_tokens_with_plasma(sender=sender, receiver=receiver, amount=amount):
    #         logging.info(f"Transaction sent: {amount} {tokenStandard} to {receiver}")
    #         break
    #     else:
    #         logging.error(f"Transaction failed. Try again after 10 seconds. (Attempt {attempt})")
    #         time.sleep(10)

    # cancel_plasma_fusion = client.cancel_plasma_fusion(client.account_address_1)
    # if cancel_plasma_fusion.get("status") == 200:
    #     logging.info(f"Plasma fusion canceled: {cancel_plasma_fusion.get('data')}")
    # else:
    #     logging.error(f"API call failed: {cancel_plasma_fusion.get('status')}")

    # hashBlock = "0f569ea4d7cb827d06ef03059556496ffb4b03bf4ee07a69be490a13ebbce3dc" # z1qr00j9wkcyvgz567sygnjxshnkq3xqxsc0t7cv
    # hashBlock = "126e53dd8a5514d67e0203e580c0d9950c9b0255618d53e87e42bdbd18246e9f" # z1qqjnwjjpnue8xmmpanz6csze6tcmtzzdtfsww7
    # address__ = "z1qqjnwjjpnue8xmmpanz6csze6tcmtzzdtfsww7"
    # receive_account_block = client.receive_account_block(address__, hashBlock)
    # if receive_account_block.get("status") == 200:
    #     logging.info(f"Receive account block: {receive_account_block.get('data')}")
    # else:
    #     logging.error(f"API call failed: {receive_account_block.get('status')}")

    client.close()