import pytest

from zenon_wallet_api import cli

from .fake_api import ADDRESS_0, ADDRESS_1, ADMIN, WALLET_PASSWORD


@pytest.fixture
def env(api, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ZENON_WALLET_API_URL", api.url)
    monkeypatch.setenv("ZENON_WALLET_API_USERNAME_ADMIN", ADMIN[0])
    monkeypatch.setenv("ZENON_WALLET_API_PASSWORD_ADMIN", ADMIN[1])
    monkeypatch.setenv("ZENON_WALLET_API_SECRET", WALLET_PASSWORD)
    monkeypatch.setenv("ZENON_WALLET_API_ADDRESS", ADDRESS_0)
    return api


def test_status_unlock_and_accounts(env, capsys):
    assert cli.main(["status"]) == 0
    assert '"isUnlocked": false' in capsys.readouterr().out

    assert cli.main(["unlock"]) == 0
    assert cli.main(["accounts"]) == 0
    out = capsys.readouterr().out
    assert f"  0  {ADDRESS_0}" in out and f"  1  {ADDRESS_1}" in out


def test_balances_use_the_default_address(env, capsys):
    assert cli.main(["balances"]) == 0

    out = capsys.readouterr().out
    assert "12345.67890123  ZNN" in out
    assert "0.50000000  QSR" in out


def test_errors_are_printed_and_give_exit_code_1(env, capsys):
    assert cli.main(["accounts"]) == 1

    assert capsys.readouterr().err == "Error: HTTP 409: Wallet is locked\n"


def test_send_asks_for_confirmation(env, capsys, monkeypatch):
    env.unlocked = True
    monkeypatch.setattr("builtins.input", lambda _question: "n")

    assert cli.main(["send", ADDRESS_1, "1.5"]) == 1
    assert env.calls("POST", f"/api/transfer/{ADDRESS_0}/send") == []

    assert cli.main(["send", ADDRESS_1, "1.5", "--token", "QSR", "--from", "1", "--yes"]) == 0
    assert env.calls("POST", "/api/transfer/1/send")[0]["body"] == {
        "address": ADDRESS_1,
        "amount": "1.5",
        "tokenStandard": "QSR",
    }
    assert "Sent. Block hash: block-" in capsys.readouterr().out


def test_missing_settings_are_reported(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    for name in ("URL", "USERNAME_ADMIN", "PASSWORD_ADMIN"):
        monkeypatch.delenv(f"ZENON_WALLET_API_{name}", raising=False)

    assert cli.main(["status"]) == 1
    assert "Missing environment variables: ZENON_WALLET_API_URL" in capsys.readouterr().err
