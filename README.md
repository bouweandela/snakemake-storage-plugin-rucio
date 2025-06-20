[![CI](https://github.com/bouweandela/snakemake-storage-plugin-rucio/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/bouweandela/snakemake-storage-plugin-rucio/actions/workflows/ci.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/bouweandela/snakemake-storage-plugin-rucio/graph/badge.svg?token=GRYFT0TCRQ)](https://codecov.io/gh/bouweandela/snakemake-storage-plugin-rucio)
[![Docs](https://readthedocs.org/projects/snakemake/badge/?version=latest)](https://snakemake.github.io/snakemake-plugin-catalog/plugins/storage/rucio.html)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15657667.svg)](https://doi.org/10.5281/zenodo.15657667)

# snakemake-storage-plugin-rucio

A Snakemake storage plugin that handles files available through [Rucio](https://rucio.cern.ch/).

## Usage

A manual for using different storage providers with Snakemake is available
[here](https://snakemake.readthedocs.io/en/stable/snakefiles/storage.html).
Documentation for this plugin is available [here](https://snakemake.github.io/snakemake-plugin-catalog/plugins/storage/rucio.html).
Below are some examples of using the plugin in a [Snakemake rule](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html).

### Download files

Download all input files and then run the workflow.

`Snakefile` content:

```Snakemake
rule download:
    input:
        storage("rucio://test_scope/test{sample}.txt")
    output:
        "results/test{sample}.txt"
    shell:
        "mv {input} {output}"
```

This command will download files `test1.txt` and `test2.txt` from scope `test_scope`
and move them to `results/test1.txt` and `results/test2.txt` respectively.
The `--verbose` flag is useful to print debug logging information in case things
do not work on the first attempt.

```bash
snakemake --cores 2 --verbose results/test1.txt results/test2.txt
```

### Only get the URLs for later download

This is useful if the workflow processes multiple input files on multiple CPU
cores and you would like to overlap download with computations, or if there is
not enough storage space available to download all files prior to processing them.


`Snakefile` content:

```Snakemake
rule get_url:
    input:
        storage("rucio://testing/test{sample}.txt", retrieve=False)
    output:
        "results/url{sample}.txt"
    shell:
        "echo {input} > {output}"
```

This command will store the URLs to files `test1.txt` and `test2.txt` from
scope `test_scope` in files `results/url1.txt` and `results/url2.txt` respectively.
In a real workflow, these URLs would be used to download the file when it is needed.

```bash
snakemake --cores 2 results/url1.txt results/url2.txt
```

### Only get the URL and stream the data

This is useful if your input files are large and you only need part of the data or
the data does not fit in local storage.

`Snakefile` content:

```Snakemake
rule stream_file:
    input:
        storage("rucio://test_scope/test{sample}.txt", retrieve=False)
    output:
        "results/stream{sample}.txt"
    run:
        # Stream the file content into the output file.
        import gfal2
        import sys
        from pathlib import Path
        input_url  = input[0]
        output_path = output[0]
        print(f"Copying from {input_url} to {output_path}")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        ctx = gfal2.creat_context()
        size = ctx.stat(input_url).st_size
        file = ctx.open(input_url, "r")
        chunk_size = 2 # read 2 byte chunks for demonstration purposes
        n_chunks = (size // chunk_size) + 1
        with open(output_path, "w") as out_file:
            for _ in range(0, n_chunks):
                data = file.read(chunk_size)
                out_file.write(data)
```

This command retrieves the URLs to files `test1.txt` and `test2.txt` from
scope `test_scope`  and streams their content in 2 byte chunks to files
`results/stream1.txt` and `results/stream2.txt` respectively. In a real workflow,
larger chunks or a smarter access pattern that only reads the required bits are recommended.

```bash
snakemake --cores 2 --verbose results/stream1.txt results/stream2.txt
```

### Upload a file

Upload a file using Rucio.

`Snakefile` content:

```Snakemake
rule upload:
    output:
        "rucio://test_scope/test_file.txt"
    message:
        "Writing Hello world to {output} and uploading"
    shell:
        """
        echo "Hello world" > {output}
        """
```

This command will write some text to a local file `test_file.txt` and upload it
to Rucio. The file will be uploaded to a
[storage element](https://rucio.github.io/documentation/started/concepts/rucio_storage_element/)
matching the [RSE expression](https://rucio.github.io/documentation/started/concepts/rse_expressions)
TEST_RSE_EXPRESSION in the scope `test_scope` and attached to the
[dataset](https://rucio.github.io/documentation/started/concepts/file_dataset_container/)
`test_dataset`. Specifying the target `dataset` is required to avoid creating
a [replication rule](https://rucio.github.io/documentation/started/concepts/replication_rules_examples)
per file, which would make the number of replication rules unmanageable.

```
snakemake --default-storage-provider rucio --storage-rucio-upload-rse TEST_RSE_EXPRESSION --storage-rucio-upload-dataset test_dataset --cores 1 --verbose 'rucio://test_scope/test_file.txt'
```

## Contributing

Contributions are very welcome. Instructions on how to get started are available
in the [contribution guidelines](CONTRIBUTING.md).
