"""Tests for the Rucio storage Snakemake plugin."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from snakemake_interface_storage_plugins.settings import StorageProviderSettingsBase
from snakemake_interface_storage_plugins.storage_provider import StorageProviderBase
from snakemake_interface_storage_plugins.tests import TestStorageBase

from snakemake_storage_plugin_rucio import StorageProvider, StorageProviderSettings

TEST_SCOPE = "test"
TEST_FILE = "file1"
TEST_RSE = "XRD1"


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
            download_rse=TEST_RSE,
            upload_rse=TEST_RSE,
        )


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
        return f"rucio://{TEST_SCOPE}/{TEST_FILE}"

    def get_query_not_existing(self, tmp_path: Path) -> str:  # noqa: ARG002
        """Return a query that is not present in the storage."""
        return "rucio://{TEST_SCOPE}/abc.txt"


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
        return f"rucio://{TEST_SCOPE}/{file}"

    def get_query_not_existing(self, tmp_path: Path) -> str:  # noqa: ARG002
        """Return a query that is not present in the storage."""
        return f"rucio://{TEST_SCOPE}/abc.txt"
