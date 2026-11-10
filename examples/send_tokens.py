"""Send tokens from ZENON_WALLET_API_ADDRESS, getting plasma from the plasma bot when needed.

Usage: python examples/send_tokens.py <to address> <amount> [token]
"""

import sys

from zenon_wallet_api import ApiError, PlasmaTimeout, ZenonWalletClient


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    to_address, amount = sys.argv[1], sys.argv[2]
    token = sys.argv[3] if len(sys.argv) > 3 else "ZNN"

    with ZenonWalletClient.from_env() as client:
        if not client.default_address:
            raise SystemExit("Set ZENON_WALLET_API_ADDRESS to the sending address.")
        client.ensure_unlocked()
        try:
            block = client.send_with_plasma(client.default_address, to_address, amount, token)
        except PlasmaTimeout as error:
            raise SystemExit(f"No plasma in time: {error}")
        except ApiError as error:
            raise SystemExit(f"The transfer was refused: {error}")
        print(f"Sent {amount} {token} to {to_address}. Block hash: {block['hash']}")


if __name__ == "__main__":
    main()
