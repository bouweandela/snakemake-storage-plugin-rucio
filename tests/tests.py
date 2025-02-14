from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from snakemake_interface_storage_plugins.settings import StorageProviderSettingsBase
from snakemake_interface_storage_plugins.storage_provider import StorageProviderBase
from snakemake_interface_storage_plugins.tests import TestStorageBase

from snakemake_storage_plugin_rucio import StorageProvider, StorageProviderSettings


class TestStorageRucioBase(TestStorageBase):
    __test__ = False

    def get_storage_provider_cls(self) -> type[StorageProviderBase]:
        # Return the StorageProvider class of this plugin
        return StorageProvider

    def get_storage_provider_settings(
        self,
    ) -> StorageProviderSettingsBase | None:
        # instantiate StorageProviderSettings of this plugin as appropriate
        return StorageProviderSettings(upload_rse="NIKHEF")


@pytest.mark.skipif(
    "RUCIO_CONFIG" not in os.environ,
    reason="requires a Rucio configuration",
)
class TestStorageRead(TestStorageRucioBase):
    __test__ = True
    retrieve_only = True  # set to True if the storage is read-only
    store_only = False  # set to True if the storage is write-only
    delete = False  # set to False if the storage does not support deletion

    def get_query(self, tmp_path: Path) -> str:  # noqa: ARG002
        # Return a query. If retrieve_only is True, this should be a query that
        # is present in the storage, as it will not be created.
        return "rucio://testing/test5.txt"

    def get_query_not_existing(self, tmp_path: Path) -> str:  # noqa: ARG002
        # Return a query that is not present in the storage.
        return "rucio://testing/test0.txt"


@pytest.mark.skipif(
    "RUCIO_CONFIG" not in os.environ,
    reason="requires a Rucio configuration",
)
class TestStorageWrite(TestStorageRucioBase):
    __test__ = True
    retrieve_only = False  # set to True if the storage is read-only
    store_only = True  # set to True if the storage is write-only
    delete = False  # set to False if the storage does not support deletion

    def get_query(self, tmp_path: Path) -> str:  # noqa: ARG002
        # Return a query. If retrieve_only is True, this should be a query that
        # is present in the storage, as it will not be created.
        scope = "testing"
        file = f"test-{datetime.now(timezone.utc).isoformat()}.txt"
        return f"rucio://{scope}/{file}.txt"

    def get_query_not_existing(self, tmp_path: Path) -> str:  # noqa: ARG002
        # Return a query that is not present in the storage.
        return "rucio://testing/test0.txt"
