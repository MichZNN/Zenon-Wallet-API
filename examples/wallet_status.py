"""Show the state of the wallet and, when it is unlocked, its accounts."""

from zenon_wallet_api import ZenonWalletClient


def main() -> None:
    with ZenonWalletClient.from_env() as client:
        status = client.wallet_status()
        print(f"Initialized: {status['isInitialized']}")
        print(f"Unlocked:    {status['isUnlocked']}")
        print(f"Auto-receiver enabled: {client.auto_receiver_status()['isEnabled']}")

        if status["isUnlocked"]:
            for account in client.wallet_accounts()["list"]:
                print(f"Account {account['index']}: {account['address']}")


if __name__ == "__main__":
    main()
