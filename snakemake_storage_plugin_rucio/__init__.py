import dataclasses
import inspect
from collections.abc import Iterable, Sequence
from urllib.parse import urlparse

import rucio.client
import rucio.client.baseclient
import rucio.client.downloadclient
import rucio.client.uploadclient
import rucio.common.exception
from snakemake_interface_storage_plugins.io import IOCacheStorageInterface, Mtime
from snakemake_interface_storage_plugins.settings import StorageProviderSettingsBase
from snakemake_interface_storage_plugins.storage_object import (
    StorageObjectGlob,
    StorageObjectRead,
    StorageObjectWrite,
    retry_decorator,
)
from snakemake_interface_storage_plugins.storage_provider import (
    ExampleQuery,
    Operation,
    QueryType,
    StorageProviderBase,
    StorageQueryValidationResult,
)

# Optional:
# Define settings for your storage plugin (e.g. host url, credentials).
# They will occur in the Snakemake CLI as --storage-<storage-plugin-name>-<param-name>
# Make sure that all defined fields are 'Optional' and specify a default value
# of None or anything else that makes sense in your case.
# Note that we allow storage plugin settings to be tagged by the user. That means,
# that each of them can be specified multiple times (an implicit nargs=+), and
# the user can add a tag in front of each value (e.g. tagname1:value1 tagname2:value2).
# This way, a storage plugin can be used multiple times within a workflow with different
# settings.


# Copy the available settings over from the Rucio client.
_RUCIO_CLIENT_CLS = rucio.client.baseclient.BaseClient


def _get_help(arg: str) -> str:
    """Read the help text for a Rucio client argument."""
    doc = _RUCIO_CLIENT_CLS.__init__.__doc__
    for line in doc.split("\n"):
        if arg in line:
            return line.split(f":param {arg}:", 1)[1]
    return ""


StorageProviderSettings = dataclasses.make_dataclass(
    "StorageProviderSettings",
    fields=[
        (
            f.name,
            f.annotation,
            dataclasses.field(
                default=f.default,
                metadata={"help": _get_help(f.name)},
            ),
        )
        for f in inspect.signature(_RUCIO_CLIENT_CLS).parameters.values()
    ]
    + [
        (
            "ignore_checksum",
            bool,
            dataclasses.field(
                default=False,
                metadata={
                    "help": "If true, skips the checksum validation between the downloaded file and the rucio catalouge.",
                },
            ),
        ),
        (
            "upload_rse",
            str,
            dataclasses.field(
                default=None,
                metadata={
                    "help": "Rucio Storage Element (RSE) expression to upload files to.",
                },
            ),
        ),
    ],
    bases=(StorageProviderSettingsBase,),
)


# Required:
# Implementation of your storage provider
# This class can be empty as the one below.
# You can however use it to store global information or maintain e.g. a connection
# pool.
class StorageProvider(StorageProviderBase):
    # For compatibility with future changes, you should not overwrite the __init__
    # method. Instead, use __post_init__ to set additional attributes and initialize
    # further stuff.

    def __post_init__(self) -> None:
        # This is optional and can be removed if not needed.
        # Alternatively, you can e.g. prepare a connection to your storage backend here.
        # and set additional attributes.
        valid_settings = inspect.signature(_RUCIO_CLIENT_CLS).parameters
        settings = {
            k: v
            for k, v in dataclasses.asdict(self.settings).items()
            if k in valid_settings
        }
        client = rucio.client.Client(**settings)
        self.client = client
        self.dclient = rucio.client.downloadclient.DownloadClient(client)
        self.uclient = rucio.client.uploadclient.UploadClient(client)

    @classmethod
    def example_queries(cls) -> list[ExampleQuery]:
        """Return an example queries with description for this storage provider (at
        least one).
        """
        return [
            ExampleQuery(
                query="rucio://myscope/myfile.txt",
                type=QueryType.ANY,
                description="A file in a Rucio scope.",
            ),
        ]

    def rate_limiter_key(
        self,
        query: str,  # noqa: ARG002
        operation: Operation,  # noqa: ARG002
    ) -> str:
        """Return a key for identifying a rate limiter given a query and an operation.

        This is used to identify a rate limiter for the query.
        E.g. for a storage provider like http that would be the host name.
        For s3 it might be just the endpoint URL.
        """
        return self.settings.rucio_host

    def default_max_requests_per_second(self) -> float:
        """Return the default maximum number of requests per second for this storage
        provider.
        """
        return 100

    def use_rate_limiter(self) -> bool:
        """Return False if no rate limiting is needed for this provider."""
        return False

    @classmethod
    def is_valid_query(cls, query: str) -> StorageQueryValidationResult:
        """Return whether the given query is valid for this storage provider."""
        # Ensure that also queries containing wildcards (e.g. {sample}) are accepted
        # and considered valid. The wildcards will be resolved before the storage
        # object is actually used.
        try:
            parsed = urlparse(query)
        except Exception as exc:  # noqa: BLE001
            return StorageQueryValidationResult(
                query=query,
                valid=False,
                reason=f"cannot be parsed as URL ({exc})",
            )
        if parsed.scheme != "rucio":
            return StorageQueryValidationResult(
                query=query,
                valid=False,
                reason="must start with rucio (rucio://...)",
            )
        return StorageQueryValidationResult(
            query=query,
            valid=True,
        )


# Required:
# Implementation of storage object. If certain methods cannot be supported by your
# storage (e.g. because it is read-only see
# snakemake-storage-http for comparison), remove the corresponding base classes
# from the list of inherited items.
class StorageObject(StorageObjectRead, StorageObjectWrite, StorageObjectGlob):
    # For compatibility with future changes, you should not overwrite the __init__
    # method. Instead, use __post_init__ to set additional attributes and initialize
    # further stuff.

    def __post_init__(self) -> None:
        # This is optional and can be removed if not needed.
        # Alternatively, you can e.g. prepare a connection to your storage backend here.
        # and set additional attributes.
        if not self.is_valid_query():
            raise ValueError(self.query)
        parsed = urlparse(self.query)
        self.scope = parsed.netloc
        self.file = parsed.path.lstrip("/")

    @property
    def client(self) -> rucio.client.Client:
        return self.provider.client

    async def inventory(self, cache: IOCacheStorageInterface) -> None:
        """From this file, try to find as much existence and modification date
        information as possible. Only retrieve that information that comes for free
        given the current object.
        """
        # This is optional and can be left as is

        # If this is implemented in a storage object, results have to be stored in
        # the given IOCache object, using self.cache_key() as key.
        # Optionally, this can take a custom local suffix, needed e.g. when you want
        # to cache more items than the current query: self.cache_key(local_suffix=...)
        if self.get_inventory_parent() in cache.exists_in_storage:
            # record has been inventorized before
            return

        # check if scope exists
        if self.scope not in self.client.list_scopes():
            cache.exists_in_storage[self.cache_key()] = False
        else:
            cache.exists_in_storage[self.get_inventory_parent()] = True
            files = self.client.list_dids(
                scope=self.scope,
                filters={"type": "file"},
            )
            batch_size = 500
            batch = []
            for i, file in enumerate(files, 1):
                batch.append(file)
                if i % batch_size == 0:
                    self._handle(cache, batch)
                    batch.clear()
            self._handle(cache, batch)

    def _handle(self, cache: IOCacheStorageInterface, files: Sequence[str]) -> None:
        dids = [{"scope": self.scope, "name": f} for f in files]
        for file, meta in zip(files, self.client.get_metadata_bulk(dids)):
            key = self.cache_key(f"{self.scope}/{file}")
            cache.mtime[key] = Mtime(storage=meta["updated_at"].timestamp())
            cache.size[key] = meta["bytes"]
            cache.exists_in_storage[key] = True

    def get_inventory_parent(self) -> str:
        """Return the parent directory of this object."""
        return self.scope

    def local_suffix(self) -> str:
        """Return a unique suffix for the local path, determined from self.query."""
        return f"{self.scope}/{self.file}"

    def cleanup(self) -> None:
        """Perform local cleanup of any remainders of the storage object."""
        # self.local_path() should not be removed, as this is taken care of by
        # Snakemake.

    # Fallible methods should implement some retry logic.
    # The easiest way to do this (but not the only one) is to use the retry_decorator
    # provided by snakemake-interface-storage-plugins.
    @retry_decorator
    def exists(self) -> bool:
        # return True if the object exists
        try:
            self.client.get_did(scope=self.scope, name=self.file)
        except rucio.common.exception.DataIdentifierNotFound:
            return False
        return True

    @retry_decorator
    def mtime(self) -> float:
        # return the modification time
        meta = self.client.get_metadata(scope=self.scope, name=self.file)
        return meta["updated_at"].timestamp()

    @retry_decorator
    def size(self) -> int:
        # return the size in bytes
        did = self.client.get_did(scope=self.scope, name=self.file)
        return did["bytes"]

    @retry_decorator
    def retrieve_object(self) -> None:
        # Ensure that the object is accessible locally under self.local_path()
        self.provider.dclient.download_dids(
            [
                {
                    "did": f"{self.scope}:{self.file}",
                    "base_dir": self.local_path().parent,
                    "no_subdir": True,
                    "ignore_checksum": self.provider.settings.ignore_checksum,
                },
            ],
            num_threads=1,
        )

    # The following to methods are only required if the class inherits from
    # StorageObjectReadWrite.

    @retry_decorator
    def store_object(self) -> None:
        # Ensure that the object is stored at the location specified by
        # self.local_path().
        if self.exists():
            msg = f'File "{self.scope}:{self.file}" already exists on Rucio'
            raise ValueError(msg)
        rse = self.provider.settings.upload_rse
        if rse is None:
            msg = "Please specify the `upload_rse`."
            raise ValueError(msg)
        self.provider.uclient.upload(
            [
                {
                    "path": self.local_path(),
                    "did_scope": self.scope,
                    "rse": self.provider.settings.upload_rse,
                    "register_after_upload": True,
                },
            ],
        )

    @retry_decorator
    def remove(self) -> None:
        # Remove the object from the storage.
        ...

    # The following to methods are only required if the class inherits from
    # StorageObjectGlob.

    @retry_decorator
    def list_candidate_matches(self) -> Iterable[str]:
        """Return a list of candidate matches in the storage for the query."""
        # This is used by glob_wildcards() to find matches for wildcards in the query.
        # The method has to return concretized queries without any remaining wildcards.
        # Use snakemake_executor_plugins.io.get_constant_prefix(self.query) to get the
        # prefix of the query before the first wildcard.
        return self.client.list_dids(
            scope=self.scope,
            filters={
                "name": self.file,
                "type": "file",
            },
        )
