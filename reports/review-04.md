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

A similar command was used to extract data from stock (non-gated) files:

```
for %f in (*stock*.fls) do (echo "%f" & python extract_map_43.py "%f") >>outputw
```

## Results

### Stock Files

| FLS File | Offset | Address | X-Axis Points | Y-Axis Points | Key Characteristics |
|----------|--------|---------|---------------|---------------|---------------------|
| F430 Black 141072 LHS Stock.FLS | 0x738e2 | 0x81dd72 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros |
| F430 Black 141072 RHS Stock.FLS | 0x738e2 | 0x81dd72 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros |
| LHS Stock 2007 F430 155283.FLS | 0x7d644 | 0x81e440 | 15 (25.00-213.00) | 6 (10598-60486) | Extended X-axis range, complex data pattern |
| LHS Stock F430 142324.FLS | 0x738e2 | 0x81dd72 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros |
| LHS Stock F430 142877.FLS | 0x73d70 | 0x81dd78 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros |
| LHS Stock F430 145324.FLS | 0x76ff6 | 0x81db9a | 8 (31.00-104.00) | 8 (3-360) | Populated with varied values |
| LHS Stock.FLS | 0x7d644 | 0x81e440 | 15 (25.00-213.00) | 6 (10598-60486) | Identical to LHS Stock 2007 F430 155283.FLS |
| RHS Stock 2007 F430 155283.FLS | 0x7d644 | 0x81e440 | 15 (25.00-213.00) | 6 (10598-60486) | Identical to LHS Stock 2007 F430 155283.FLS |
| RHS Stock F430 142324.FLS | 0x738e2 | 0x81dd72 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros |
| RHS Stock F430 142877.FLS | 0x73d70 | 0x81dd78 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros |
| RHS Stock F430 145324.FLS | 0x76ff6 | 0x81db9a | 8 (31.00-104.00) | 8 (3-360) | Identical to LHS Stock F430 145324.FLS |
| RHS Stock.FLS | 0x7d644 | 0x81e440 | 15 (25.00-213.00) | 6 (10598-60486) | Identical to LHS Stock 2007 F430 155283.FLS |

### Gated Files (From Previous Analysis)

| FLS File | Offset | Address | X-Axis Points | Y-Axis Points | Key Characteristics |
|----------|--------|---------|---------------|---------------|---------------------|
| LHS Gated F430 145324.FLS | 0x76ff6 | 0x81db9a | 8 (31.00-104.00) | 8 (3-360) | Standard map with populated values |
| LHS Gated Tune 2006 F430 148508.FLS | 0x76f2c | 0x81dbb4 | 8 (31.00-104.00) | 8 (3-360) | Identical to LHS Gated F430 145324.FLS |
| LHS Gated Tune 2007 F430 155283.FLS | 0x7d644 | 0x81e440 | 15 (25.00-213.00) | 6 (10598-60486) | Extended X-axis range, different Y values |
| LHS Gated Tuned F430 142324.FLS | 0x73d70 | 0x81dd78 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros |
| RHS Gated F430 145324.FLS | 0x76ff6 | 0x81db9a | 8 (31.00-104.00) | 8 (3-360) | Identical to LHS Gated F430 145324.FLS |
| RHS Gated Tune 2006 F430 148508.FLS | 0x76f2c | 0x81dbb4 | 8 (31.00-104.00) | 8 (3-360) | Identical to LHS Gated F430 145324.FLS |
| RHS Gated Tune 2007 F430 155283.FLS | 0x7d644 | 0x81e440 | 15 (25.00-213.00) | 6 (10598-60486) | Identical to LHS Gated Tune 2007 F430 155283.FLS |
| RHS Gated Tuned F430 142324.FLS | 0x73d70 | 0x81dd78 | 12 (24.00-211.00) | 4 (45-64) | All data values are zeros |

## Key Findings

1. **Matching LHS/RHS Files**: Left-hand side (LHS) and right-hand side (RHS) versions of the same model/tune have identical Map #43 data, suggesting symmetrical engine management.

2. **Evolution Across Models**:
   - Early versions (141072, 142324, 142877) have Map #43 completely zeroed out
   - Mid-generation models (145324) have populated Map #43 with 8 X-axis points
   - 2007 models (155283) show significant restructuring with 15 X-axis points and different data patterns

3. **Stock vs. Gated Consistency**:
   - Same model numbers show identical Map #43 data regardless of stock/gated designation
   - This suggests Map #43 is not directly related to gate/non-gate operation differences

4. **Map Structure Changes**:
   - X-axis points increased from 8 → 12 → 15 across versions
   - Y-axis configurations vary from 4 → 8 → 6 points
   - Y-axis values in 2007 tunes are dramatically larger (10598-60486 vs 3-360)

5. **Data Pattern Trends**:
   - Early models: All zeros (map disabled or reset)
   - Mid-generation: Structured values with multiple peaks
   - 2007 models: Completely different data distribution with higher values

## Conclusion

Map #43 appears to be a significant control map that underwent substantial evolution across F430 ECU versions, particularly in the 2007 tune where both its structure and values were dramatically revised. The identical nature of LHS and RHS files indicates this map affects both sides of the engine equally, and the consistency between stock and gated files of the same version number suggests this map's function is independent of the gated/non-gated distinction.
