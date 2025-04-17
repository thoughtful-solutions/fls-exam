# Ferrari F430 ECU Map #43 Analysis

## Overview
This document analyzes Map #43 data extracted from various Ferrari F430 ECU files (.FLS) to identify patterns and differences across different tunes and configurations.

## Extraction Method
Data was extracted using the following Windows command line:

```
for %f in (*gate*.fls) do (echo "%f" & python extract_map_43.py "%f") >>outputw
```

This command:
1. Iterates through all .FLS files with "gate" in their filename
2. Echoes the filename
3. Runs a Python script to extract Map #43 data from each file
4. Appends all output to a file called "outputw"

## Results

| FLS File | Offset | Address | X-Axis Points | Y-Axis Points | Key Characteristics |
|----------|--------|---------|---------------|---------------|---------------------|
| LHS Gated F430 145324.FLS | 0x76ff6 | 0x81db9a | 8 (31.00-104.00) | 8 (3-360) | Standard map with populated values |
| LHS Gated Tune 2006 F430 148508.FLS | 0x76f2c | 0x81dbb4 | 8 (31.00-104.00) | 8 (3-360) | Identical to LHS Gated F430 145324 |
| LHS Gated Tune 2007 F430 155283.FLS | 0x7d644 | 0x81e440 | 15 (25.00-213.00) | 6 (10598-60486) | Extended X-axis range, different Y values, completely different data pattern |
| LHS Gated Tuned F430 142324.FLS | 0x73d70 | 0x81dd78 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros |
| RHS Gated F430 145324.FLS | 0x76ff6 | 0x81db9a | 8 (31.00-104.00) | 8 (3-360) | Identical to LHS Gated F430 145324 |
| RHS Gated Tune 2006 F430 148508.FLS | 0x76f2c | 0x81dbb4 | 8 (31.00-104.00) | 8 (3-360) | Identical to LHS Gated F430 145324 |
| RHS Gated Tune 2007 F430 155283.FLS | 0x7d644 | 0x81e440 | 15 (25.00-213.00) | 6 (10598-60486) | Identical to LHS Gated Tune 2007, extended range |
| RHS Gated Tuned F430 142324.FLS | 0x73d70 | 0x81dd78 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros, same as LHS version |

## Key Findings

1. **Matching LHS/RHS Files**: Left-hand side (LHS) and right-hand side (RHS) versions of the same model/tune have identical Map #43 data, suggesting symmetrical engine management.

2. **Evolution Across Models**:
   - Base tuned versions (142324.FLS) have Map #43 completely zeroed out
   - Standard F430 (145324.FLS) and 2006 tunes (148508.FLS) share identical Map #43 data
   - 2007 tunes (155283.FLS) show significant restructuring with expanded parameters

3. **Map Structure Changes**:
   - X-axis points increased from 8 → 12 → 15 across versions
   - Y-axis configurations vary from 4 → 8 → 6 points
   - Y-axis values in 2007 tunes are dramatically larger (10598-60486 vs 3-360)

4. **Data Pattern Trends**:
   - Base tuned: All zeros (map disabled or reset)
   - Standard/2006: Structured values with multiple peaks
   - 2007: Completely different data distribution with higher values

## Conclusion

Map #43 appears to be a significant control map that underwent substantial evolution across F430 ECU versions, particularly in the 2007 tune where both its structure and values were dramatically revised. The identical nature of LHS and RHS files indicates this map affects both sides of the engine equally.
