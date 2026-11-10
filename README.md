# Zenon Wallet API client for Python

A Python client and command line tool for the [Zenon Wallet API](https://github.com/hypercore-one/znn_walletapi_csharp), the REST service that manages a Zenon wallet and talks to a Zenon node for you.

The client covers every endpoint of the Wallet API and adds a few helpers for everyday tasks: reading balances as exact decimals, waiting for plasma, and sending tokens once the sender has plasma.

## Requirements

- Python 3.10 or newer
- A running Wallet API server and an API user for it

## Installation

```bash
pip install git+https://github.com/MichZNN/Zenon-Wallet-API.git
```

Or, from a clone of this repository:

```bash
pip install -e ".[test]"
```

## Configuration

Copy `.env.example` to `.env` and fill it in. The client reads these variables from the environment, or from the nearest `.env` file:

| Variable | Purpose |
| --- | --- |
| `ZENON_WALLET_API_URL` | Address of the Wallet API, for example `https://localhost:443` |
| `ZENON_WALLET_API_USERNAME_ADMIN`, `ZENON_WALLET_API_PASSWORD_ADMIN` | API user with the `Admin` role |
| `ZENON_WALLET_API_USERNAME_USER`, `ZENON_WALLET_API_PASSWORD_USER` | API user with the `User` role |
| `ZENON_WALLET_API_SECRET` | Password of the wallet itself (initialize, restore, unlock) |
| `ZENON_WALLET_API_ADDRESS` | Optional: the wallet address you use most |
| `ZENON_WALLET_API_MNEMONIC` | Optional: only read by `examples/restore_wallet.py` |

Only the URL and one pair of credentials are required. `from_env()` signs in with the admin credentials unless you pass `role="user"`.

The Wallet API checks roles strictly: initializing and restoring a wallet need the `Admin` role, every other call needs the `User` role. Give your admin user both roles in the Wallet API configuration if you want to do everything with one account; otherwise a call outside the account's role fails with status `403`.

The `.env` file holds the keys to your wallet. Keep it out of version control and readable only by you.

## Quick start

```python
from zenon_wallet_api import ZenonWalletClient

with ZenonWalletClient.from_env() as client:
    client.ensure_unlocked()

    for account in client.wallet_accounts()["list"]:
        print(account["index"], account["address"])

    for balance in client.balances(client.default_address):
        print(balance)                     # 12345.67890123 ZNN

    block = client.send(client.default_address, "z1q...", "1.5", "ZNN")
    print(block["hash"])
```

You can also pass the settings yourself instead of using environment variables:

```python
client = ZenonWalletClient(
    "https://localhost:443",
    username="admin",
    password="...",
    wallet_password="...",
)
```

The client signs in on the first request and signs in again by itself when the token has expired.

## Command line

Installing the package adds the `zenon-wallet-api` command (also available as `python -m zenon_wallet_api`):

```bash
zenon-wallet-api status
zenon-wallet-api unlock
zenon-wallet-api accounts
zenon-wallet-api balances                 # of ZENON_WALLET_API_ADDRESS
zenon-wallet-api balances z1q...
zenon-wallet-api plasma z1q...
zenon-wallet-api unreceived
zenon-wallet-api validate z1q...
zenon-wallet-api send z1q... 1.5 --token QSR --ensure-plasma
zenon-wallet-api lock
```

`send` asks for confirmation unless you add `--yes`. Use `--from` to send from another address or account index, `--role user` to sign in with the user credentials and `--env-file` to point at a specific `.env` file.

## Client reference

Every method returns the decoded JSON answer of the API, or `None` when the API answers without a body. An `account` is a wallet account given as its address or as its index (`0`, `1`, ...).

### Wallet

| Method | Description |
| --- | --- |
| `wallet_status()` | Whether the wallet is initialized and unlocked |
| `wallet_initialize(password=None)` | Create a new wallet; returns the mnemonic (admin) |
| `wallet_restore(mnemonic, password=None)` | Restore a wallet from its mnemonic (admin) |
| `wallet_unlock(password=None)` | Unlock the wallet |
| `wallet_lock()` | Lock the wallet |
| `wallet_accounts(page_index=0, page_size=1024)` | List the wallet accounts |
| `wallet_add_accounts(count=1)` | Add accounts to the wallet |

`password` defaults to the wallet password the client was created with.

### Ledger

| Method | Description |
| --- | --- |
| `account_info(address)` | Account height and raw token balances |
| `received_account_blocks(address, page_index=0, page_size=1024)` | Account blocks of an address |
| `unreceived_account_blocks(address, page_index=0, page_size=50)` | Blocks waiting to be received |
| `plasma_info(address)` | Current plasma, maximum plasma and fused QSR |
| `fusion_entries(address, page_index=0, page_size=1024)` | Plasma fusions made by an address |

### Transfers and plasma

| Method | Description |
| --- | --- |
| `send(account, to_address, amount, token_standard="ZNN")` | Send tokens |
| `receive(account, block_hash)` | Receive one unreceived block |
| `fuse_plasma(account, beneficiary, amount)` | Fuse QSR to give an address plasma |
| `cancel_plasma(account, id_hash)` | Cancel a fusion and get the QSR back |

Amounts are in whole tokens and are passed as `str`, `int` or `Decimal`, for example `"1.5"`. Floats are refused because they lose precision. `token_standard` is `"ZNN"`, `"QSR"` or a ZTS such as `zts1...`.

### Utilities

| Method | Description |
| --- | --- |
| `validate_address(address)` | Whether an address is valid and whether it is an embedded contract |
| `plasma_bot_fuse(address)` | Ask the community plasma bot for temporary plasma |
| `plasma_bot_expiration(address)` | When the plasma-bot fusion of an address expires |
| `auto_receiver_status()` | Whether the API receives incoming blocks by itself |

### Helpers

| Method | Description |
| --- | --- |
| `ensure_unlocked(password=None)` | Unlock the wallet only when it is locked |
| `balances(address)` | Balances as `TokenBalance` objects with exact `Decimal` values |
| `has_plasma(address)` | Whether an address currently has plasma |
| `wait_for_plasma(address, timeout=1800, interval=30)` | Wait until an address has plasma |
| `ensure_plasma(address, timeout=1800, interval=30)` | Ask the plasma bot when an address has no plasma, then wait |
| `send_with_plasma(account, to_address, amount, token_standard="ZNN")` | Make sure the sender has plasma, then send |
| `receive_all(account)` | Receive every block that is waiting for an account |
| `account_address(account)` | The address of an account given its address or index |

A send block is paid for with the plasma of the **sender**. Without plasma the Wallet API falls back to proof of work, which is slow; `send_with_plasma` avoids that by asking the plasma bot first.

## Errors

All errors derive from `ZenonWalletError`:

| Error | When |
| --- | --- |
| `ApiError` | The API answered with an error status. `status`, `title`, `detail` and `errors` hold the details |
| `AuthenticationError` | The username or password was rejected (a subclass of `ApiError`) |
| `ConnectionFailed` | The server could not be reached or did not answer in time |
| `ConfigurationError` | A required setting is missing or invalid |
| `PlasmaTimeout` | An address did not get plasma in time |

```python
from zenon_wallet_api import ApiError

try:
    client.send(0, "z1q...", "1000000")
except ApiError as error:
    print(error.status, error.detail)      # 404 You do not have enough ZNN tokens
```

Statuses you are likely to meet: `403` for a wrong wallet password or a missing role, `404` for an unknown token or insufficient balance, `409` when the wallet is locked or not initialized, and `422` when the API rejects a value.

## Examples

The `examples` folder has runnable scripts that use the `.env` file:

| Script | What it does |
| --- | --- |
| `wallet_status.py` | Show the wallet state and its accounts |
| `initialize_wallet.py` | Create a new wallet and print its mnemonic once |
| `restore_wallet.py` | Restore a wallet from `ZENON_WALLET_API_MNEMONIC` |
| `balances_and_plasma.py` | Show balances and plasma of an address |
| `send_tokens.py` | Send tokens, getting plasma from the plasma bot when needed |
| `receive_pending.py` | Receive every block waiting for your address |

## Tests

```bash
pip install -e ".[test]"
pytest
```

The tests start a small stand-in for the Wallet API (`tests/fake_api.py`) and run the client, the command line tool and every example against it over real HTTP. They do not need a Wallet API server or a Zenon node, and they do not prove that the client works against a live server: check new versions of the Wallet API against a test wallet first.

## Upgrading from the first version

Version 1.0 replaces the old `module/ZenonWalletClient.py`:

- Import with `from zenon_wallet_api import ZenonWalletClient` and create the client with `ZenonWalletClient.from_env()`.
- Methods return the data directly and raise `ApiError` on failure, instead of returning `{"status": ..., "data": ...}`.
- Renamed methods: `ledger_account_info` → `account_info`, `ledger_received_account_blocks` → `received_account_blocks`, `ledger_unreceived_account_blocks` → `unreceived_account_blocks`, `ledger_plasma_info` → `plasma_info`, `ledger_fusion_entries` → `fusion_entries`, `send_tokens` → `send`, `receive_account_block` → `receive`, `generate_plasma_qsr` → `fuse_plasma`, `cancel_plasma_fusion` → `cancel_plasma`, `generate_plasma_bot` → `plasma_bot_fuse`, `fusion_expiration` → `plasma_bot_expiration`, `get_autoreceiver_status` → `auto_receiver_status`.
- `fuse_plasma` now sends the beneficiary and amount the API requires, and `wallet_add_accounts` sends the number of accounts.
- Paging arguments are `page_index` and `page_size`.

## License

[MIT](LICENSE)
