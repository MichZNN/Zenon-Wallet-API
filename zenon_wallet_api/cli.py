"""Command line interface: ``python -m zenon_wallet_api <command>``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import __version__
from .client import ZenonWalletClient
from .exceptions import ZenonWalletError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zenon-wallet-api",
        description="Work with a Zenon Wallet API server. Settings come from ZENON_WALLET_API_* "
        "environment variables or a .env file.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--env-file", help="path of the .env file (default: nearest .env)")
    parser.add_argument(
        "--role", choices=("admin", "user"), default="admin", help="credentials to sign in with (default: admin)"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    commands.add_parser("status", help="show whether the wallet is initialized and unlocked")
    commands.add_parser("accounts", help="list the accounts of the wallet")
    commands.add_parser("unlock", help="unlock the wallet with ZENON_WALLET_API_SECRET")
    commands.add_parser("lock", help="lock the wallet")
    commands.add_parser("auto-receiver", help="show whether the auto-receiver is enabled")

    for name, text in (
        ("balances", "show the token balances of an address"),
        ("plasma", "show the plasma of an address"),
        ("unreceived", "list the blocks waiting to be received by an address"),
        ("validate", "check whether an address is valid"),
    ):
        command = commands.add_parser(name, help=text)
        command.add_argument(
            "address", nargs="?" if name != "validate" else None, help="address (default: ZENON_WALLET_API_ADDRESS)"
        )

    send = commands.add_parser("send", help="send tokens from a wallet account")
    send.add_argument("to_address", help="address that receives the tokens")
    send.add_argument("amount", help="amount in whole tokens, for example 1.5")
    send.add_argument("--token", default="ZNN", help="ZNN, QSR or a token standard (default: ZNN)")
    send.add_argument("--from", dest="account", help="sending address or account index (default: ZENON_WALLET_API_ADDRESS)")
    send.add_argument("--ensure-plasma", action="store_true", help="ask the plasma bot first when the sender has no plasma")
    send.add_argument("--yes", action="store_true", help="send without asking for confirmation")
    return parser


def _print_json(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _address(client: ZenonWalletClient, given: str | None) -> str:
    address = given or client.default_address
    if not address:
        raise ZenonWalletError("Give an address or set ZENON_WALLET_API_ADDRESS")
    return address


def _account(value: str) -> str | int:
    return int(value) if value.isdigit() else value


def _run(client: ZenonWalletClient, args: argparse.Namespace) -> int:
    command = args.command
    if command == "status":
        _print_json(client.wallet_status())
    elif command == "accounts":
        for account in client.wallet_accounts().get("list") or []:
            print(f"{account['index']:>3}  {account['address']}")
    elif command == "unlock":
        client.wallet_unlock()
        print("Wallet unlocked.")
    elif command == "lock":
        client.wallet_lock()
        print("Wallet locked.")
    elif command == "auto-receiver":
        _print_json(client.auto_receiver_status())
    elif command == "balances":
        balances = client.balances(_address(client, args.address))
        if not balances:
            print("No balances.")
        for balance in balances:
            print(f"{balance.balance:>24f}  {balance.symbol:<8} {balance.name}")
    elif command == "plasma":
        _print_json(client.plasma_info(_address(client, args.address)))
    elif command == "unreceived":
        _print_json(client.unreceived_account_blocks(_address(client, args.address)))
    elif command == "validate":
        _print_json(client.validate_address(args.address))
    elif command == "send":
        account = _account(_address(client, args.account))
        if not args.yes:
            question = f"Send {args.amount} {args.token} from {account} to {args.to_address}? [y/N] "
            if input(question).strip().lower() not in ("y", "yes"):
                print("Cancelled.")
                return 1
        send = client.send_with_plasma if args.ensure_plasma else client.send
        block = send(account, args.to_address, args.amount, args.token)
        print(f"Sent. Block hash: {block.get('hash', 'unknown')}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        with ZenonWalletClient.from_env(args.env_file, role=args.role) as client:
            return _run(client, args)
    except (ZenonWalletError, ValueError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
