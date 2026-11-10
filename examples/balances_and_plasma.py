"""Show the balances and plasma of ZENON_WALLET_API_ADDRESS (or an address given as argument)."""

import sys

from zenon_wallet_api import ZenonWalletClient


def main() -> None:
    with ZenonWalletClient.from_env() as client:
        address = sys.argv[1] if len(sys.argv) > 1 else client.default_address
        if not address:
            raise SystemExit("Give an address or set ZENON_WALLET_API_ADDRESS.")

        if not client.validate_address(address)["isValid"]:
            raise SystemExit(f"{address} is not a valid address.")

        print(f"Balances of {address}:")
        for balance in client.balances(address):
            print(f"  {balance}")

        plasma = client.plasma_info(address)
        print(f"Plasma: {plasma['currentPlasma']} of {plasma['maxPlasma']} (fused QSR: {plasma['qsrAmount']})")
        expiration = client.plasma_bot_expiration(address)["expiration"]
        print(f"Plasma-bot fusion expires: {expiration or 'no fusion'}")


if __name__ == "__main__":
    main()
