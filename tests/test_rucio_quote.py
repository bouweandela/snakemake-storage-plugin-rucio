"""Tests for the rucio_quote encoding/decoding module."""

from __future__ import annotations

import doctest

import snakemake_storage_plugin_rucio.rucio_quote as rucio_quote


def test_doctests() -> None:
    """Run all doctests embedded in rucio_quote."""
    results = doctest.testmod(rucio_quote, verbose=False)
    assert results.failed == 0, f"{results.failed} doctest(s) failed"
