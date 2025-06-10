"""
Professional Async PocketOption API - Core module
Fully async implementation with modern Python practices
"""

from .client import AsyncPocketOptionClient
from .exceptions import (
    PocketOptionError,
    ConnectionError,
    AuthenticationError,
    OrderError,
    TimeoutError
)
from .models import (
    Balance,
    Candle,
    Order,
    OrderResult,
    OrderStatus,
    OrderDirection,
    Asset,
    ConnectionStatus
)
from .constants import ASSETS, Regions

# Create REGIONS instance
REGIONS = Regions()

__version__ = "2.0.0"
__author__ = "PocketOptionAPI Team"

__all__ = [
    "AsyncPocketOptionClient",
    "PocketOptionError",
    "ConnectionError", 
    "AuthenticationError",
    "OrderError",
    "TimeoutError",
    "Balance",
    "Candle",
    "Order",
    "OrderResult",
    "OrderStatus",
    "OrderDirection",
    "Asset",
    "ConnectionStatus",
    "ASSETS",
    "REGIONS"
]
