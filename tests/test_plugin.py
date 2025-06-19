"""Tests for the Rucio storage Snakemake plugin."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from snakemake_interface_storage_plugins.settings import StorageProviderSettingsBase
from snakemake_interface_storage_plugins.storage_provider import (
    StorageProviderBase,
    StorageQueryValidationResult,
)
from snakemake_interface_storage_plugins.tests import TestStorageBase, logger

from snakemake_storage_plugin_rucio import StorageProvider, StorageProviderSettings


def _load_site_config() -> dict:
    """Load site specific configuration from site-config.json.

    The file should be located in the same directory as this module and allows
    for testing with a different Rucio server than the Rucio demo deployment
    used in CI.
    """
    # Default values as provided by the Rucio demo deployment.
    config = {
        "scope": "test",
        "file": "file1",
        "download_rse": "XRD1",
        "upload_rse": "XRD1",
        "streaming_protocol": "root",
    }
    traversible = Path(__file__).parent / "site-config.json"

    try:
        site_config = json.loads(traversible.read_text(encoding="utf-8"))
    except FileNotFoundError:
        pass
    else:
        for key, value in site_config.items():
            if key not in config:
                msg = f"Unknown key {key} in site-config.json"
                raise ValueError(msg)
            config[key] = value
    return config


SITE_CONFIG = _load_site_config()


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("rucio://test/file1.txt", True),
        ("rucio:/test/file1.txt", True),
        ("/scope/file1.txt", True),
        ("scope/file1.txt", True),
        ("root://xrd1:1094//rucio/test/7c/69/file1.txt", True),
        ("x:/y/z", False),
        ("rucio://scope", False),
    ],
)
def test_query_validation(query: str, expected: bool) -> None:  # noqa: FBT001
    """Test query validation."""
    res = StorageProvider.is_valid_query(query)
    assert isinstance(res, StorageQueryValidationResult)
    assert bool(res) == expected


class TestStorageRucioBase(TestStorageBase):
    """Base class configuring the tests."""

    __test__ = False

    def get_storage_provider_cls(self) -> type[StorageProviderBase]:
        """Return the StorageProvider class of this plugin."""
        return StorageProvider

    def get_storage_provider_settings(
        self,
    ) -> StorageProviderSettingsBase | None:
        """Create StorageProviderSettings of this plugin for testing."""
        return StorageProviderSettings(
            download_rse=SITE_CONFIG["download_rse"],
            upload_rse=SITE_CONFIG["upload_rse"],
        )


@pytest.mark.skipif(
    "RUCIO_CONFIG" not in os.environ,
    reason="requires a Rucio configuration",
)
class TestStorageNoRetrieve(TestStorageRucioBase):
    """Read tests."""

    __test__ = True
    retrieve_only = True  # set to True if the storage is read-only
    store_only = False  # set to True if the storage is write-only
    delete = False  # set to False if the storage does not support deletion

    def get_query(self, tmp_path: Path) -> str:  # noqa: ARG002
        """Return a query."""
        # If retrieve_only is True, this should be a query that
        # is present in the storage, as it will not be created.
        return f"rucio://{SITE_CONFIG['scope']}/{SITE_CONFIG['file']}"

    def get_query_not_existing(self, tmp_path: Path) -> str:  # noqa: ARG002
        """Return a query that is not present in the storage."""
        return f"rucio://{SITE_CONFIG['scope']}/abc.txt"

    def test_storage(self, tmp_path: Path) -> None:
        """Override the test_storage method to test just getting the URL."""
        provider = self.get_storage_provider_cls()(
            logger=logger,
            local_prefix=Path(tmp_path) / "local_prefix",
            settings=self.get_storage_provider_settings(),
            retrieve=False,
        )

        obj = provider.object(self.get_query(tmp_path))
        assert obj.query.startswith(f"{SITE_CONFIG['streaming_protocol']}://")
        assert obj.query.endswith(f"{SITE_CONFIG['file']}")
        assert obj.local_path() == obj.query


@pytest.mark.skipif(
    "RUCIO_CONFIG" not in os.environ,
    reason="requires a Rucio configuration",
)
class TestStorageRead(TestStorageRucioBase):
    """Read tests."""

    __test__ = True
    retrieve_only = True  # set to True if the storage is read-only
    store_only = False  # set to True if the storage is write-only
    delete = False  # set to False if the storage does not support deletion

    def get_query(self, tmp_path: Path) -> str:  # noqa: ARG002
        """Return a query."""
        # If retrieve_only is True, this should be a query that
        # is present in the storage, as it will not be created.
        return f"rucio://{SITE_CONFIG['scope']}/{SITE_CONFIG['file']}"

    def get_query_not_existing(self, tmp_path: Path) -> str:  # noqa: ARG002
        """Return a query that is not present in the storage."""
        return f"rucio://{SITE_CONFIG['scope']}/abc.txt"


@pytest.mark.skipif(
    "RUCIO_CONFIG" not in os.environ,
    reason="requires a Rucio configuration",
)
class TestStorageWrite(TestStorageRucioBase):
    """Write tests."""

    __test__ = True
    retrieve_only = False  # set to True if the storage is read-only
    store_only = True  # set to True if the storage is write-only
    delete = False  # set to False if the storage does not support deletion

    def get_query(self, tmp_path: Path) -> str:  # noqa: ARG002
        """Return a query for a new file with a unique name."""
        file = f"snakemake-storage-plugin-test-{datetime.now(UTC):%Y%m%dT%H%M%S%f}.txt"
        return f"rucio://{SITE_CONFIG['scope']}/{file}"

    def get_query_not_existing(self, tmp_path: Path) -> str:  # noqa: ARG002
        """Return a query that is not present in the storage."""
        return f"rucio://{SITE_CONFIG['scope']}/abc.txt"
