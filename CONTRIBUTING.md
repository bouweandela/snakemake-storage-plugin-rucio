# Development installation

While Rucio can be installed from PyPI, most practical use cases require
the [gfal2-python](https://pypi.org/project/gfal2-python/) package to access
the storage elements and the [voms](https://github.com/italiangrid/voms) package to
generate X509 proxy certificates for authentication with the storage elements.

An easy way to install all required software is to run
```bash
conda create -n snakemake-storage-plugin-rucio-dev -c conda-forge python-gfal2 voms poetry
conda activate snakemake-storage-plugin-rucio-dev
poetry install --extras dev
pre-commit install
```

Using poetry inside a conda environment may not work as expected as poetry
may overwrite the packages installed by conda, but the snakemake plugins use
poetry by default for managing their dependencies so this is kept for consistency.
It is not recommended to use any conda commands after the initial `conda create`,
except for `conda activate`.

# Running code quality checks and tests

The code quality checks can be run with the command:
```bash
pre-commit run --all
```

The tests can be run with the command:

```bash
pytest tests/tests.py --cov
```

If no [`RUCIO_CONFIG`](https://rucio.github.io/documentation/user/configuring_the_client#rucio_config)
environmental variable is defined, tests that require connecting to a Rucio server
will be skipped. The configuration file needs to contain information from the
[client](https://rucio.github.io/documentation/operator/configuration_parameters#client_config)
section. At least `rucio_host`, `auth_host`, `account`, and `auth_type` are required.

# Commit messages

When committing, always use [Conventional Commit Messages](https://www.conventionalcommits.org/).
These are used by the [Release Please](https://github.com/googleapis/release-please) action
to generate the changelog.

# Making a release

Merge the pull request opened by the [Release Please](https://github.com/googleapis/release-please)
[GitHub Action](.github/workflows/release-please.yml).
