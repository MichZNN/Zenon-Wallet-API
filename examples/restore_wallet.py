"""Restore a wallet from ZENON_WALLET_API_MNEMONIC and unlock it.

Needs the admin user and ZENON_WALLET_API_SECRET (the wallet password).
"""

import os

from zenon_wallet_api import ZenonWalletClient


def main() -> None:
    with ZenonWalletClient.from_env(role="admin") as client:
        mnemonic = os.getenv("ZENON_WALLET_API_MNEMONIC", "")
        if not mnemonic.strip():
            raise SystemExit("Set ZENON_WALLET_API_MNEMONIC in your .env file first.")

        client.wallet_restore(mnemonic)
        client.wallet_unlock()
        print("Wallet restored and unlocked.")
        for account in client.wallet_accounts()["list"]:
            print(f"Account {account['index']}: {account['address']}")


if __name__ == "__main__":
    main()
