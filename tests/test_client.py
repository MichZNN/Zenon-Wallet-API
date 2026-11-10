from decimal import Decimal

import pytest

from zenon_wallet_api import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    ConnectionFailed,
    PlasmaTimeout,
    ZenonWalletClient,
)

from .fake_api import ADDRESS_0, ADDRESS_1, ADMIN, MNEMONIC, WALLET_PASSWORD, ZNN


# ----- configuration and authentication ---------------------------------


@pytest.mark.parametrize("url", ["", "localhost:443", "ftp://host", "https://"])
def test_rejects_invalid_base_url(url):
    with pytest.raises(ConfigurationError):
        ZenonWalletClient(url, "user", "password")


def test_requires_credentials():
    with pytest.raises(ConfigurationError):
        ZenonWalletClient("https://localhost", "", "")


def test_signs_in_once_and_reuses_the_token(api, client):
    client.wallet_status()
    client.wallet_status()

    assert api.logins == 1
    assert api.calls("GET", "/api/wallet/status")[0]["authorization"] == "Bearer token-1"


def test_signs_in_again_when_the_token_has_expired(api, client):
    client.wallet_status()
    api.expire_tokens()

    assert client.wallet_status() == {"isInitialized": True, "isUnlocked": False}
    assert api.logins == 2


def test_wrong_credentials_raise_authentication_error(api):
    client = ZenonWalletClient(api.url, "admin", "wrong")

    with pytest.raises(AuthenticationError) as error:
        client.wallet_status()

    assert error.value.status == 401
    assert "Invalid username or password" in str(error.value)


def test_unreachable_server_raises_connection_failed():
    client = ZenonWalletClient("http://127.0.0.1:9", "user", "password", timeout=1)

    with pytest.raises(ConnectionFailed):
        client.wallet_status()


def test_repr_does_not_contain_secrets(client):
    assert ADMIN[1] not in repr(client)
    assert WALLET_PASSWORD not in repr(client)


def test_from_env_reads_settings_and_reports_missing_ones(api, monkeypatch, tmp_path):
    for name in ("URL", "USERNAME_ADMIN", "PASSWORD_ADMIN", "USERNAME_USER", "PASSWORD_USER", "SECRET", "ADDRESS"):
        monkeypatch.delenv(f"ZENON_WALLET_API_{name}", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        f'ZENON_WALLET_API_URL="{api.url}/"\n'
        f'ZENON_WALLET_API_USERNAME_ADMIN="{ADMIN[0]}"\n'
        f'ZENON_WALLET_API_PASSWORD_ADMIN="{ADMIN[1]}"\n'
        f'ZENON_WALLET_API_SECRET="{WALLET_PASSWORD}"\n'
        f'ZENON_WALLET_API_ADDRESS="{ADDRESS_0}"\n'
    )

    client = ZenonWalletClient.from_env(env_file)
    assert client.base_url == api.url
    assert client.default_address == ADDRESS_0
    client.wallet_unlock()
    assert api.unlocked

    with pytest.raises(ConfigurationError, match="ZENON_WALLET_API_USERNAME_USER"):
        ZenonWalletClient.from_env(env_file, role="user")


# ----- error handling ---------------------------------------------------


def test_problem_details_end_up_in_the_error(api, client):
    with pytest.raises(ApiError) as error:
        client.wallet_accounts()

    assert error.value.status == 409
    assert error.value.detail == "Wallet is locked"
    assert str(error.value) == "HTTP 409: Wallet is locked"


def test_validation_errors_list_the_fields(client):
    with pytest.raises(ApiError) as error:
        client._send("GET", "/api/unknown/route")

    assert error.value.status == 422
    assert error.value.errors == {"Address": ["'Address' must not be empty."]}
    assert "'Address' must not be empty." in str(error.value)


def test_error_without_body(client):
    with pytest.raises(ApiError) as error:
        client._send("GET", "/api/broken/text")

    assert str(error.value) == "HTTP 500"


# ----- wallet -----------------------------------------------------------


def test_wallet_lifecycle(api, client):
    api.initialized = False

    assert client.wallet_initialize() == MNEMONIC
    assert api.calls("POST", "/api/wallet/init")[0]["body"] == {"password": WALLET_PASSWORD}

    client.wallet_restore(MNEMONIC, "Other#456")
    assert api.calls("POST", "/api/wallet/restore")[0]["body"] == {"password": "Other#456", "mnemonic": MNEMONIC}

    assert client.ensure_unlocked() is True
    assert client.ensure_unlocked() is False
    client.wallet_lock()
    assert client.wallet_status()["isUnlocked"] is False


def test_wrong_wallet_password_is_an_api_error_not_a_login_problem(client):
    with pytest.raises(ApiError) as error:
        client.wallet_unlock("wrong")

    assert error.value.status == 403
    assert not isinstance(error.value, AuthenticationError)


def test_wallet_password_is_required(api):
    client = ZenonWalletClient(api.url, *ADMIN)

    with pytest.raises(ConfigurationError, match="wallet password"):
        client.wallet_unlock()


def test_ensure_unlocked_needs_an_initialized_wallet(api, client):
    api.initialized = False

    with pytest.raises(ConfigurationError, match="not initialized"):
        client.ensure_unlocked()


def test_accounts_can_be_listed_and_added(api, unlocked):
    assert [a["address"] for a in unlocked.wallet_accounts()["list"]] == [ADDRESS_0, ADDRESS_1]
    assert api.calls("GET", "/api/wallet/accounts")[0]["query"] == {"pageIndex": "0", "pageSize": "1024"}

    added = unlocked.wallet_add_accounts(2)
    assert added["count"] == 2
    assert api.calls("POST", "/api/wallet/accounts")[0]["query"] == {"numberOfAccounts": "2"}

    with pytest.raises(ValueError):
        unlocked.wallet_add_accounts(0)
    with pytest.raises(TypeError):
        unlocked.wallet_add_accounts("2")


def test_account_address_resolves_an_index(unlocked):
    assert unlocked.account_address(1) == ADDRESS_1
    assert unlocked.account_address(ADDRESS_0) == ADDRESS_0
    with pytest.raises(ValueError, match="index 7"):
        unlocked.account_address(7)
    with pytest.raises(ValueError):
        unlocked.account_address(-1)


# ----- ledger -----------------------------------------------------------


def test_balances_are_exact_decimals(client):
    balances = {balance.symbol: balance for balance in client.balances(ADDRESS_0)}

    assert balances["ZNN"].balance == Decimal("12345.67890123")
    assert balances["ZNN"].token_standard == ZNN
    assert str(balances["QSR"]) == "0.50000000 QSR"
    assert client.balances(ADDRESS_1) == []


@pytest.mark.parametrize(
    "method, path, largest",
    [
        ("received_account_blocks", "received", 1024),
        ("unreceived_account_blocks", "unreceived", 50),
        ("fusion_entries", "fused", 1024),
    ],
)
def test_paged_ledger_endpoints(api, client, method, path, largest):
    getattr(client, method)(ADDRESS_0, 2, largest)

    call = api.calls("GET", f"/api/ledger/{ADDRESS_0}/{path}")[0]
    assert call["query"] == {"pageIndex": "2", "pageSize": str(largest)}

    with pytest.raises(ValueError):
        getattr(client, method)(ADDRESS_0, 0, largest + 1)
    with pytest.raises(ValueError):
        getattr(client, method)(ADDRESS_0, -1)
    with pytest.raises(TypeError):
        getattr(client, method)(ADDRESS_0, "0")


def test_address_in_the_path_is_escaped(api, client):
    client.account_info("../wallet/status")

    assert api.requests[-1]["path"] == "/api/ledger/..%2Fwallet%2Fstatus/balances"


# ----- transfers and plasma --------------------------------------------


def test_send_posts_the_documented_body(api, unlocked):
    block = unlocked.send(0, ADDRESS_1, Decimal("1.50"), "QSR")

    call = api.calls("POST", "/api/transfer/0/send")[0]
    assert call["body"] == {"address": ADDRESS_1, "amount": "1.50", "tokenStandard": "QSR"}
    assert block["hash"].startswith("block-")


@pytest.mark.parametrize("amount", ["0", "-1", "1e5", "abc", "", "1,5", Decimal("0")])
def test_send_rejects_invalid_amounts(unlocked, amount):
    with pytest.raises(ValueError):
        unlocked.send(ADDRESS_0, ADDRESS_1, amount)


def test_send_rejects_floats(unlocked):
    with pytest.raises(TypeError, match="floats lose precision"):
        unlocked.send(ADDRESS_0, ADDRESS_1, 0.1)


def test_send_reports_insufficient_balance(unlocked):
    with pytest.raises(ApiError, match="You do not have enough ZNN tokens"):
        unlocked.send(ADDRESS_0, ADDRESS_1, "999999")


def test_receive_and_receive_all(api, unlocked):
    api.unreceived[ADDRESS_1] = [f"hash-{number}" for number in range(53)]

    unlocked.receive(ADDRESS_1, "hash-0")
    assert api.calls("POST", f"/api/transfer/{ADDRESS_1}/receive")[0]["body"] == {"blockHash": "hash-0"}

    received = unlocked.receive_all(1)
    assert len(received) == 52
    assert api.unreceived[ADDRESS_1] == []


def test_fuse_and_cancel_plasma(api, unlocked):
    unlocked.fuse_plasma(ADDRESS_0, ADDRESS_1, 100)
    unlocked.cancel_plasma(ADDRESS_0, "abc123")

    assert api.calls("POST", f"/api/plasma/{ADDRESS_0}/fuse")[0]["body"] == {"address": ADDRESS_1, "amount": "100"}
    assert api.calls("POST", f"/api/plasma/{ADDRESS_0}/cancel")[0]["body"] == {"idHash": "abc123"}
    with pytest.raises(ValueError):
        unlocked.cancel_plasma(ADDRESS_0, " ")


def test_send_with_plasma_asks_the_bot_for_the_sender_and_waits(api, unlocked):
    api.plasma_delay = 2
    naps = []

    block = unlocked.send_with_plasma(0, ADDRESS_1, "1", interval=5, sleep=naps.append)

    assert api.calls("POST", "/api/utilities/plasma-bot/fuse")[0]["body"] == {"address": ADDRESS_0}
    assert naps == [5, 5]
    assert api.calls("POST", "/api/transfer/0/send")[0]["body"]["address"] == ADDRESS_1
    assert block["hash"].startswith("block-")


def test_send_with_plasma_skips_the_bot_when_plasma_is_present(api, unlocked):
    api.plasma[ADDRESS_0] = 21000

    unlocked.send_with_plasma(ADDRESS_0, ADDRESS_1, "1")

    assert api.calls("POST", "/api/utilities/plasma-bot/fuse") == []


def test_send_with_plasma_validates_before_waiting(api, unlocked):
    with pytest.raises(ValueError):
        unlocked.send_with_plasma(ADDRESS_0, ADDRESS_1, "nothing")

    assert api.calls("POST", "/api/utilities/plasma-bot/fuse") == []


def test_wait_for_plasma_times_out(client):
    with pytest.raises(PlasmaTimeout):
        client.wait_for_plasma(ADDRESS_1, timeout=0.05, interval=0.01)


# ----- utilities --------------------------------------------------------


def test_utilities(api, client):
    assert client.validate_address(ADDRESS_0) == {"isValid": True, "isEmbedded": False}
    assert api.calls("POST", "/api/utilities/address/validate")[0]["query"] == {"address": ADDRESS_0}
    assert client.validate_address("nope")["isValid"] is False
    assert client.plasma_bot_expiration(ADDRESS_1) == {"expiration": None}
    assert client.auto_receiver_status() == {"isEnabled": True}
    assert client.plasma_bot_fuse(ADDRESS_1) is None
