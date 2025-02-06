# ZNN Wallet API Python Script

## Overview
This project provides a Python script containing functions that interact with the [ZNN Wallet API](https://github.com/hypercore-one/znn_walletapi_csharp). The script includes various helper functions to simplify communication with the wallet API in Python applications.

## Requirements
- Python 3.8 or higher
- Requests library (`pip install requests`)
- Python-dotenv library (`pip install python-dotenv`)
- A valid connection to the ZNN Wallet API and credentials

## Environment Variables
This script requires the following environment variables to be set in a `.env` file:

```
ZENON_WALLET_API_URL="https://"
ZENON_WALLET_API_USERNAME_ADMIN=""
ZENON_WALLET_API_PASSWORD_ADMIN=""
ZENON_WALLET_API_USERNAME_USER=""
ZENON_WALLET_API_PASSWORD_USER=""
ZENON_WALLET_API_SECRET=""
ZENON_WALLET_API_MNEMONIC=""
ZENON_WALLET_API_ADDRESS=""
```

## Supported API Endpoints
The following API endpoints are covered in this script:

- **Wallet Endpoints**
  - ✅ Initialize new wallet `client.wallet_initialize()`
  - ✅ Get the wallet status `client.wallet_status()`
  - ✅ Unlock the wallet `client.wallet_unlock()`
  - ✅ Lock the wallet `client.wallet_lock()`
  - ✅ Restore an existing wallet `client.wallet_restore()`
  - ✅ Add wallet accounts `client.wallet_add_accounts()`
  - ✅ Get all wallet accounts `client.wallet_accounts()`
  
- **Ledger Endpoints**
  - ✅ Get plasma info by address `client.ledger_plasma_info(address)`
  - ✅ Get the account info by address `client.ledger.account_info(address)`
  
- **Plasma Operations**
  - ✅ Generate plasma by fusing QSR `client.generate_plasma_qsr(address)`
  - ✅ Cancel a plasma fusion `client.cancel_plasma_fusion(address)`
  
- **Utilities**
  - ✅ Get the fusion expiration by address from the plasma-bot `client.fusion_expiration(address)`
  - ✅ Generate plasma by fusing QSR from the plasma-bot `client.generate_plasma_bot(address)`
  - ✅ Validate an address `client.validate_address(address)`
  
- **Transfer Operations**
  - ✅ Send tokens to an address
    ```python
    client.send_tokens(
      sender="",  # (Optional) Default is the wallet's primary address
      receiver="",  # (Required) The recipient's wallet address
      amount="",  # (Required) The amount of tokens to send
      tokenStandard=""  # (Optional) Default is "ZNN"
    )
    ```

## Configuration
The script can be configured with a custom API URL and authentication headers if required.