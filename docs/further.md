The example Snakefile below will write a URL from which the file `test.txt` from
the `testing` scope can be accessed. This URL can be used to stream the data
from the file if the protocol supports it, or download the file at a later stage.

```Snakefile
rule get_url:
    input:
        storage("rucio://testing/test.txt", retrieve=False)
    output:
        "results/test_url.txt"
    shell:
        "echo {input} > {output}"
```
