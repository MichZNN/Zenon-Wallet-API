import pytest

from zenon_wallet_api import ZenonWalletClient

from .fake_api import ADMIN, WALLET_PASSWORD, FakeWalletApi


@pytest.fixture
def api():
    server = FakeWalletApi().start()
    yield server
    server.stop()


@pytest.fixture
def client(api):
    with ZenonWalletClient(api.url, *ADMIN, wallet_password=WALLET_PASSWORD, timeout=5) as client:
        yield client


@pytest.fixture
def unlocked(api, client):
    api.unlocked = True
    return client
