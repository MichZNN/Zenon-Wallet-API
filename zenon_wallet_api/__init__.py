"""Python client for the Zenon Wallet API (hypercore-one/znn_walletapi_csharp)."""

from .client import ZenonWalletClient
from .exceptions import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    ConnectionFailed,
    PlasmaTimeout,
    ZenonWalletError,
)
from .models import TokenBalance

__version__ = "1.0.0"

__all__ = [
    "ApiError",
    "AuthenticationError",
    "ConfigurationError",
    "ConnectionFailed",
    "PlasmaTimeout",
    "TokenBalance",
    "ZenonWalletClient",
    "ZenonWalletError",
    "__version__",
]
