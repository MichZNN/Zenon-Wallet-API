"""Receive every block that is waiting for ZENON_WALLET_API_ADDRESS.

Only needed when the auto-receiver of the Wallet API is disabled.
"""

from zenon_wallet_api import ZenonWalletClient


def main() -> None:
    with ZenonWalletClient.from_env() as client:
        if not client.default_address:
            raise SystemExit("Set ZENON_WALLET_API_ADDRESS to the receiving address.")
        client.ensure_unlocked()
        received = client.receive_all(client.default_address)
        print(f"Received {len(received)} block(s).")


if __name__ == "__main__":
    main()
