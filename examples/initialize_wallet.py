"""Create a new wallet and print its mnemonic once.

Needs the admin user and ZENON_WALLET_API_SECRET (the wallet password).
Write the mnemonic down: it is the only way to restore the wallet.
"""

from zenon_wallet_api import ZenonWalletClient


def main() -> None:
    with ZenonWalletClient.from_env(role="admin") as client:
        if client.wallet_status()["isInitialized"]:
            print("The wallet is already initialized; nothing was changed.")
            return

        mnemonic = client.wallet_initialize()
        client.wallet_unlock()
        first_account = client.wallet_accounts()["list"][0]

        print("Wallet created. Store this mnemonic in a safe place:")
        print(mnemonic)
        print(f"First address: {first_account['address']}")


if __name__ == "__main__":
    main()
