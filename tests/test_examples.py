"""Runs every example against the fake API, so the examples cannot go stale."""

import runpy
import sys
from pathlib import Path

import pytest

from .fake_api import ADDRESS_0, ADDRESS_1, ADMIN, MNEMONIC, WALLET_PASSWORD

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def env(api, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ZENON_WALLET_API_URL", api.url)
    monkeypatch.setenv("ZENON_WALLET_API_USERNAME_ADMIN", ADMIN[0])
    monkeypatch.setenv("ZENON_WALLET_API_PASSWORD_ADMIN", ADMIN[1])
    monkeypatch.setenv("ZENON_WALLET_API_SECRET", WALLET_PASSWORD)
    monkeypatch.setenv("ZENON_WALLET_API_MNEMONIC", MNEMONIC)
    monkeypatch.setenv("ZENON_WALLET_API_ADDRESS", ADDRESS_0)
    return api


def run(name, *arguments, monkeypatch):
    monkeypatch.setattr(sys, "argv", [name, *arguments])
    runpy.run_path(str(EXAMPLES / name), run_name="__main__")


def test_every_example_is_covered():
    tested = {"wallet_status.py", "initialize_wallet.py", "restore_wallet.py",
              "balances_and_plasma.py", "send_tokens.py", "receive_pending.py"}
    assert {path.name for path in EXAMPLES.glob("*.py")} == tested


def test_wallet_status(env, monkeypatch, capsys):
    env.unlocked = True
    run("wallet_status.py", monkeypatch=monkeypatch)
    assert f"Account 1: {ADDRESS_1}" in capsys.readouterr().out


def test_initialize_wallet(env, monkeypatch, capsys):
    run("initialize_wallet.py", monkeypatch=monkeypatch)
    assert "already initialized" in capsys.readouterr().out

    env.initialized = False
    run("initialize_wallet.py", monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert MNEMONIC in out and f"First address: {ADDRESS_0}" in out


def test_restore_wallet(env, monkeypatch, capsys):
    run("restore_wallet.py", monkeypatch=monkeypatch)
    assert "Wallet restored and unlocked." in capsys.readouterr().out
    assert env.calls("POST", "/api/wallet/restore")[0]["body"]["mnemonic"] == MNEMONIC


def test_balances_and_plasma(env, monkeypatch, capsys):
    run("balances_and_plasma.py", monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert "12345.67890123 ZNN" in out and "Plasma-bot fusion expires: no fusion" in out

    with pytest.raises(SystemExit, match="not a valid address"):
        run("balances_and_plasma.py", "nope", monkeypatch=monkeypatch)


def test_send_tokens(env, monkeypatch, capsys):
    env.plasma[ADDRESS_0] = 21000
    run("send_tokens.py", ADDRESS_1, "2", "QSR", monkeypatch=monkeypatch)
    assert f"Sent 2 QSR to {ADDRESS_1}." in capsys.readouterr().out
    assert env.unlocked

    with pytest.raises(SystemExit, match="You do not have enough ZNN tokens"):
        run("send_tokens.py", ADDRESS_1, "999999", monkeypatch=monkeypatch)


def test_receive_pending(env, monkeypatch, capsys):
    env.unreceived[ADDRESS_0] = ["hash-1", "hash-2"]
    run("receive_pending.py", monkeypatch=monkeypatch)
    assert "Received 2 block(s)." in capsys.readouterr().out
