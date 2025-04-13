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

## Search for strings in the FLS files

Using the binutils strings command

```
strings -el  *.fls  |sort | uniq -c | sort | tail -10
strings -es -Ud *.fls  |sort | uniq -c | sort | tail -10
strings -eB *.fls  |sort | uniq -c | sort | tail -10
```
---

# Perform NGRAM Search

## N-Gram Analysis for ECU FLS Files
N-gram analysis is a powerful technique for examining Bosch ECU FLS files from Ferraris when you have multiple file dumps. It helps identify common patterns and structures without prior knowledge of the file format.
What It Does

Creates "sliding windows" of consecutive bytes (typically 8 bytes at a time)
Finds sequences that appear across multiple files
Records the positions where these common sequences appear
Helps identify file headers, configuration blocks, and data structures

## Why It's Useful for ECU Analysis

Identifies standard ECU components that appear in the same positions
Locates potential calibration data and configuration parameters
Finds repeated patterns that might indicate specific ECU functions
Helps discover Ferrari-specific modifications by comparing different versions

## Implementation Approach
The script analyzes your hex dumps by:

Extracting clean hex data from od command output
Creating a database of n-grams with their positions
Finding patterns common to all files
Showing where these patterns appear in each file (by byte offset)

This approach can reveal structural similarities in Bosch ECU files and help locate configuration details without requiring specialized ECU-specific tools

```
python ngram.py
```
---

# Binary NGRAM Search

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

---

# Signature Finder Tool


This script reads signatures from a 'signatures.lst' file in the current directory
and searches for these signatures in FLS files specified as command-line arguments.
It reports which signatures were found and their positions within each file.

```
python signature_finder.py stock.fls updated.fls stock02.fls updated02.fls
```

---

# FLS File Comparison Tool

`fls_compare.py` is a Python script designed to compare two `.FLS` files (binary firmware files commonly used for Engine Control Units, or ECUs). It provides detailed insights into differences between the files in two key areas:

1. **Signature Comparison**: Identifies and compares the positions of predefined strings (signatures) listed in a `signatures.lst` file.
2. **Byte Sequence Differences**: Detects regions where the byte sequences differ, including a hex preview and any ASCII/UTF-8 strings immediately preceding each difference.

This tool is useful for engineers, developers, or hobbyists analyzing firmware updates, debugging ECU configurations, or reverse-engineering binary files.

## Features

- **Signature Search**:
  - Reads signatures from `signatures.lst` (one per line).
  - Searches for each signature in both files as ASCII and UTF-8 encoded strings.
  - Reports:
    - Signatures unique to each file.
    - Signatures present in both files but at different positions.
    - Signatures at identical positions.

- **Byte Sequence Comparison**:
  - Identifies all regions where the files differ in their byte sequences.
  - Groups small differences into larger segments based on a configurable `min_match_length` (default: 16 bytes).
  - For each difference:
    - Shows the starting position and length.
    - Provides a hex preview of the first 16 bytes.
    - Searches backwards (up to 50 bytes) for a preceding ASCII or UTF-8 string (minimum 4 characters) in both files.

- **Output**:
  - Structured console output with summaries and detailed sections.
  - Includes total differing bytes and percentage difference relative to file size.


```bash
python fls_compare.py <file1.fls> <file2.fls> [min_match_length]
```

- `<file1.fls>`: Path to the first `.FLS` file.
- `<file2.fls>`: Path to the second `.FLS` file.
- `[min_match_length]`: Optional integer specifying the minimum number of matching bytes to split differences (default: 16).

## How It Works

1. **Signature Comparison**:
   - Loads signatures from `signatures.lst`.
   - Searches both files for each signature and compares their positions.
   - Categorizes results into unique, differing, or matching signatures.

2. **Byte Difference Analysis**:
   - Compares files byte-by-byte, grouping differences based on `min_match_length`.
   - For each difference:
     - Searches backwards (up to 50 bytes) for a printable string in both files.
     - Displays the string (if found) with its offset, followed by a hex dump of the differing bytes.

## Customization

- **Signature File**: Edit `signatures.lst` to include strings relevant to your `.FLS` files.
- **Search Parameters**: Modify `max_search` (default 50) or `min_length` (default 4) in `extract_string_before()` to adjust string detection.
- **Output Limits**: Change the script to show more/fewer differences or hex bytes (currently capped at 20 differences, 16 bytes each).

## Limitations

- Requires a `signatures.lst` file to exist.
- String search is limited to ASCII and UTF-8 encodings, with a 50-byte backward search range.
- Does not validate `.FLS` file format—assumes they are binary.

---
# romscanner.py

romscanner is a specialized tool designed to analyze Bosch ME7.x engine control unit (ECU) firmware files. It's based on the original [ME7RomTool_Ferrari project](https://github.com/360trev/ME7RomTool_Ferrari), reimplementing the C functionality in Python while maintaining the same needle pattern detection system. The tool scans firmware files to identify common structures and patterns using predefined needle patterns from the C implementation's needles.c file.

Key features of ROMScanner include:

* DPP (Data Page Pointer) register extraction - helps identify memory segments in the firmware
* EPK (Electronic Product Code) information extraction - shows details about the ECU hardware/software
* String table analysis - locates and extracts important strings from the firmware
* Map table detection - finds parameter tables used for engine management

## Usage

```
python romscanner.py [filename] [options]
Options include:

--maps: Focus on scanning for map tables
--epk: Extract only EPK information
--all: Perform all analysis types (default behavior)
```
