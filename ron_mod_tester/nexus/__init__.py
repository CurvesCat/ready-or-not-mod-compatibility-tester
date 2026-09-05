"""Nexus Mods integration for RoNCT (read-only metadata lookups)."""

from .cache import Md5Cache, default_nexus_cache_path
from .client import (
    NexusAuthError,
    NexusClient,
    NexusError,
    NexusNetworkError,
    NexusRateLimitError,
)
from .identify import Identification, identify_paks
from .mapping import confirm_md5, ignore_md5, load_user_mapping, save_user_mapping
from .requirements import build_dependency_report

__all__ = [
    "Identification",
    "Md5Cache",
    "NexusAuthError",
    "NexusClient",
    "NexusError",
    "NexusNetworkError",
    "NexusRateLimitError",
    "build_dependency_report",
    "confirm_md5",
    "default_nexus_cache_path",
    "identify_paks",
    "ignore_md5",
    "load_user_mapping",
    "save_user_mapping",
]
