# Analysis Approach

## Duplicate FLS files to research directory

```
  cd C:\Users\msn\Documents\eagusa\2006 F430 Grey 145324
  copy ""LHS Stock F1\LHS Stock F430 145324.FLS" ..\research\stock.fls
  copy "LHS Gated\LHS Gated F430 145324.FLS" ..\research\updated.fls
```

## Compare checksums for each of the FLS

``` 
md5sums
md5sums - Version 4.2
Freeware written by Gerson Kurz (http://p-nand-q.com)

5F3FFD71AC58780F7F07BE409CEA2F3E - stock.fls
D95DCB7814E9D7F2FF22629321ACD5EB - updated.fls
```

## Generate hex dumps of the FLS files


```
od -Ax -tx1z stock.fls  >stock-od.hex
od -Ax -tx1z updated.fls > updated-od.hex
```


## Perform NGRAM Search

### N-Gram Analysis for ECU FLS Files
N-gram analysis is a powerful technique for examining Bosch ECU FLS files from Ferraris when you have multiple file dumps. It helps identify common patterns and structures without prior knowledge of the file format.
What It Does

Creates "sliding windows" of consecutive bytes (typically 8 bytes at a time)
Finds sequences that appear across multiple files
Records the positions where these common sequences appear
Helps identify file headers, configuration blocks, and data structures

### Why It's Useful for ECU Analysis

Identifies standard ECU components that appear in the same positions
Locates potential calibration data and configuration parameters
Finds repeated patterns that might indicate specific ECU functions
Helps discover Ferrari-specific modifications by comparing different versions

### Implementation Approach
The script analyzes your hex dumps by:

Extracting clean hex data from od command output
Creating a database of n-grams with their positions
Finding patterns common to all files
Showing where these patterns appear in each file (by byte offset)

This approach can reveal structural similarities in Bosch ECU files and help locate configuration details without requiring specialized ECU-specific tools

```
python ngram.py
```

## Binary NGRAM Search

Binary N-Gram Analyzer
The first script performs n-gram analysis directly on binary files rather than text dumps, which is more efficient and accurate:

```
python binary_ngram.py -n 8 -t 20 your_file1.fls your_file2.fls your_file3.fls
```

```
    -n, --ngram-size: Size of n-grams to analyze (default: 8)
    -t, --top: Number of top patterns to display (default: 20)
    -m, --min-files: Minimum number of files a pattern must appear in (default: 2)
    -o, --output: Output results to file (default: screen only)
```

Key features:

* Works directly with binary FLS files (no need for text dumps)
* Finds common byte sequences across multiple files
* Shows exact positions where patterns appear in each file
* Configurable n-gram size (default: 8 bytes)
* Displays both hex and ASCII representations


## Signature Finder Tool


This script reads signatures from a 'signatures.lst' file in the current directory
and searches for these signatures in FLS files specified as command-line arguments.
It reports which signatures were found and their positions within each file.

```
python signature_finder.py stock.fls updated.fls stock02.fls updated02.fls
```

## FLS File Comparison Tool

This script compares two FLS files and reports:
1. Differences in positions of signatures from signatures.lst
2. Byte sequence differences between the files, showing start positions and lengths

```
python fls_compare.py <file1.fls> <file2.fls> [min_match_length]
```

When comparing files, the tool will:

 * Consider matching regions shorter than the minimum match length
    to be part of a single difference
 * Only split differences when it finds a matching 
    region of at least the specified length
 * This results in fewer, larger difference regions instead of 
   many small fragmented differences


The improved algorithm:

* Tracks both difference regions and matching regions
* Only ends a difference when it finds a matching sequence of sufficient length
* Properly handles edge cases at file boundaries



This approach is particularly useful for firmware files where small matching sequences between modified regions don't represent meaningful separations. The default value of 16 bytes is a reasonable starting point, but you can adjust it based on your specific files:

Lower values (like 4 or 8) will result in more granular differences
Higher values (like 32 or 64) will group more differences together into larger chunks
