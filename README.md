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

### Wallet Endpoints

- **Initialize a new wallet**  
  `client.wallet_initialize()`  

- **Get the wallet status**  
  `client.wallet_status()`  

- **Unlock the wallet**  
  `client.wallet_unlock()`  

- **Lock the wallet**  
  `client.wallet_lock()`  

- **Restore an existing wallet**  
  `client.wallet_restore()`  

- **Add wallet accounts**  
  `client.wallet_add_accounts()`  

- **Get all wallet accounts**  
  `client.wallet_accounts()`  

### Ledger Endpoints

- **Get account info by address**  
  `client.ledger_account_info(address)`  
  - `address (str, required)`

- **Get all received account blocks by address**  
  `client.ledger_received_account_blocks(address, pageIndex=0, pageSize=1024)`  
  - `address (str, required)`
  - `pageIndex (int, optional, default=0)`
  - `pageSize (int, optional, default=1024, must be between 1 and 1024)`

- **Get all unreceived account blocks by address**  
  `client.ledger_unreceived_account_blocks(address, pageIndex=0, pageSize=50)`  
  - `address (str, required)`
  - `pageIndex (int, optional, default=0)`
  - `pageSize (int, optional, default=50, must be between 1 and 50)`

- **Get plasma info by address**  
  `client.ledger_plasma_info(address)`  
  - `address (str, required)`

- **Get all fusion entries by address**  
  `client.ledger_fusion_entries(address)`  
  - `address (str, required)`

### Plasma Operations
- **Generate plasma by fusing QSR**  
  `client.generate_plasma_qsr(address)`  
  - `address (str, required)`

- **Cancel a plasma fusion**  
  `client.cancel_plasma_fusion(address, idHash)`  
  - `address (str, required)`
  - `idHash (str, required)`

### Utilities
- **Get the fusion expiration by address from the plasma-bot**  
  `client.fusion_expiration(address)`  
  - `address (str, required)`

- **Generate plasma by fusing QSR from the plasma-bot**  
  `client.generate_plasma_bot(address)`  
  - `address (str, required)`

- **Validate an address**  
  `client.validate_address(address)`  
  - `address (str, required)`

### Transfer Operations
- **Send tokens to an address**  
  `client.send_tokens(sender="", receiver="", amount="", tokenStandard="ZNN")`  
  - `sender (str, optional)`: Defaults to the wallet's primary address if not specified  
  - `receiver (str, required)`
  - `amount (str, required)`  
  - `tokenStandard (str, optional, default="ZNN")`

- **Receive an account block by block hash**  
  `client.receive_account_block(address, blockHash)`  
  - `address (str, required)`
  - `blockHash (str, required)`

### Auto Receiver
- **Get the auto-receiver status**  
  `client.get_autoreceiver_status()`  

## Configuration
The script can be configured with a custom API URL and authentication headers if required.