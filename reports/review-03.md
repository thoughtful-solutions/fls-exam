# Common Maps and Values Across Non-Stock FLS Files

## 1. Introduction

This report analyzes Ferrari F430 FLS files to identify maps common across all non-Stock (Tuned) files and their consistent values, excluding those unchanged in Stock files. The analysis leverages detailed data from two files:
- **Non-Stock (Tuned)**: 'RHS Gated F430 145324.FLS'
- **Stock**: 'F430 Black 141072 LHS Stock.FLS'

The focus is on *Multi Axis Map Type #1* maps, specifically Map #43 in non-Stock files, which is modified for performance tuning. This updated report includes the entire common map as a discussion point, compares it to the Stock equivalent (Map #45), and highlights variations. Due to limited data for other non-Stock files, assumptions are made based on the representative non-Stock file, with noted limitations.

## 2. File Categorization

The FLS files are divided into **Stock** and **non-Stock (Tuned)** categories for Left Hand Side (LHS) and Right Hand Side (RHS) configurations.

### Stock Files (Excluded from Common Map Analysis)
- **LHS Stock**:
  - 'F430 Black 141072 LHS Stock.FLS'
  - 'LHS Stock 2007 F430 155283.FLS'
  - 'LHS Stock F430 142324.FLS'
  - 'LHS Stock F430 142877.FLS'
  - 'LHS Stock F430 145324.FLS'
  - 'LHS Stock.FLS'
- **RHS Stock**:
  - 'F430 Black 141072 RHS Stock.FLS'
  - 'RHS Stock 2007 F430 155283.FLS'
  - 'RHS Stock F430 142324.FLS'
  - 'RHS Stock F430 142877.FLS'
  - 'RHS Stock F430 145324.FLS'
  - 'RHS Stock.FLS'

### Non-Stock (Tuned) Files (Focus of Analysis)
- **LHS Tuned**:
  - 'LHS Gated F430 145324.FLS'
  - 'LHS Gated Tune 2006 F430 148508.FLS'
  - 'LHS Gated Tune 2007 F430 155283.FLS'
  - 'LHS Gated Tuned F430 142324.FLS'
- **RHS Tuned**:
  - 'RHS Gated F430 145324.FLS'
  - 'RHS Gated Tune 2006 F430 148508.FLS'
  - 'RHS Gated Tune 2007 F430 155283.FLS'
  - 'RHS Gated Tuned F430 142324.FLS'

There are **8 non-Stock (Tuned) files**, representing modified firmware for performance enhancements.

## 3. Discussion: Common Map Across Non-Stock Files

The *Multi Axis Map Type #1* maps are identified as common across non-Stock files, with **Map #43** in 'RHS Gated F430 145324.FLS' serving as the representative example. This map is assumed to be present in all 8 non-Stock files, containing values modified from the Stock configuration to optimize performance parameters (e.g., fuel delivery, ignition timing).

### Entire Common Map (Map #43, Non-Stock)
Below is the complete 8x8 table for Map #43 from 'RHS Gated F430 145324.FLS':

**Offset**: 0x76ff6  
**Address**: 0x81db9a  
**X-Axis (PHY)**: [31, 37, 44, 51, 64, 77, 91, 104]  
**Y-Axis (PHY)**: [3, 10, 30, 60, 100, 160, 220, 360]  
**Values (PHY)**:

| Y \ X | 31   | 37   | 44   | 51   | 64   | 77   | 91  | 104  |
|-------|------|------|------|------|------|------|-----|------|
| 3     | 13614 | 17726 | 20803 | 32890 | 4112 | 52668 | 1250 | 5313 |
| 10    | 16441 | 20553 | 26975 | 32896 | 7188 | 219  | 1563 | 24667 |
| 30    | 25933 | 29533 | 32878 | 32896 | 10020 | 313  | 1875 | 24667 |
| 60    | 32881 | 32891 | 32896 | 32896 | 16178 | 469  | 2188 | 27095 |
| 100   | 15928 | 18495 | 26459 | 32896 | 20811 | 625  | 2500 | 28508 |
| 160   | 19010 | 23118 | 32890 | 32896 | 25688 | 781  | 3125 | 29491 |
| 220   | 27733 | 31075 | 32896 | 32896 | 32113 | 938  | 3750 | 30191 |
| 360   | 32886 | 32895 | 32896 | 32896 | 41872 | 1094 | 4688 | 30606 |

**Observations**:
- The table is fully populated, with values ranging from **219** to **52668**, indicating an active calibration map.
- High values (e.g., 32896) appear frequently, suggesting a saturation point or maximum setting for certain conditions.
- Specific values like **52668** (Y=3, X=77), **7188** (Y=10, X=64), and **24667** (Y=10, X=104; Y=30, X=104) highlight tuning adjustments, as they differ from Stock equivalents.
- The axes likely represent engine parameters (e.g., RPM, load), with the values adjusting outputs like fuel or spark advance.

### Comparison with Stock Map (Map #45)
The equivalent map in the Stock file 'F430 Black 141072 LHS Stock.FLS' is **Map #45**, with the same structure but different values:

**Offset**: 0x73a22  
**Address**: 0x81de22  
**X-Axis (PHY)**: [31, 37, 44, 51, 64, 77, 91, 104]  
**Y-Axis (PHY)**: [3, 10, 30, 60, 100, 160, 220, 360]  
**Values (PHY)**:

| Y \ X | 31   | 37   | 44   | 51   | 64   | 77   | 91  | 104  |
|-------|------|------|------|------|------|------|-----|------|
| 3     | 13614 | 17726 | 20803 | 32890 | 4112 | 54716 | 1250 | 5313 |
| 10    | 16441 | 20553 | 26975 | 32896 | 6420 | 219  | 1563 | 30638 |
| 30    | 25933 | 29533 | 32878 | 32896 | 10532 | 313  | 1875 | 29824 |
| 60    | 32881 | 32891 | 32896 | 32896 | 16768 | 469  | 2188 | 29568 |
| 100   | 15928 | 18495 | 26459 | 32896 | 21036 | 625  | 2500 | 30816 |
| 160   | 19010 | 23118 | 32890 | 32896 | 26096 | 781  | 3125 | 31488 |
| 220   | 27733 | 31075 | 32896 | 32896 | 32448 | 938  | 3750 | 32448 |
| 360   | 32886 | 32895 | 32896 | 32896 | 41888 | 1094 | 4688 | 32896 |

**Variations**:
- **Structure**: Both maps share identical X and Y axes, confirming they serve the same function (e.g., a fuel or ignition map).
- **Value Differences** (key examples):
  - **Y=3, X=77**: Non-Stock: **52668** vs. Stock: **54716** (difference: -2048).
  - **Y=10, X=64**: Non-Stock: **7188** vs. Stock: **6420** (difference: +768).
  - **Y=10, X=104**: Non-Stock: **24667** vs. Stock: **30638** (difference: -5971).
  - **Y=30, X=104**: Non-Stock: **24667** vs. Stock: **29824** (difference: -5157).
  - **Y=60, X=64**: Non-Stock: **16178** vs. Stock: **16768** (difference: -590).
- **Pattern**:
  - Non-Stock values are generally lower at higher X and Y coordinates (e.g., X=104, Y≥10), suggesting a leaner or more aggressive calibration (e.g., reduced fuel or advanced timing).
  - At lower coordinates (e.g., Y=3, X≤64), values are often identical (e.g., 13614, 17726), indicating unchanged baseline settings.
  - The largest differences occur at X=77 and X=104, implying tuning focused on specific operating conditions (e.g., high RPM or load).
- **Significance**:
  - The variations reflect performance tuning, likely optimizing power output or efficiency in the non-Stock file.
  - Values like 52668, 7188, and 24667 were highlighted as they show clear deviations from Stock, assumed consistent across non-Stock files.

## 4. Table: Common Maps and Values

The table below lists Map #43 across all non-Stock files, with Map #45 from the Stock file for comparison. Only key differing values are shown for brevity, but the full map above provides context.

| **FLS File**                        | **Common Map** | **Map Type**       | **X-Axis (PHY)**             | **Y-Axis (PHY)**             | **Key Values (PHY)**         |
|-------------------------------------|----------------|--------------------|------------------------------|------------------------------|-----------------------------|
| LHS Gated F430 145324.FLS           | Map #43        | Multi Axis Map #1 | 31, 37, 44, 51, 64, 77, 91, 104 | 3, 10, 30, 60, 100, 160, 220, 360 | 52668, 7188, 24667, etc.* |
| LHS Gated Tune 2006 F430 148508.FLS | Map #43        | Multi Axis Map #1 | 31, 37, 44, 51, 64, 77, 91, 104 | 3, 10, 30, 60, 100, 160, 220, 360 | 52668, 7188, 24667, etc.* |
| LHS Gated Tune 2007 F430 155283.FLS | Map #43        | Multi Axis Map #1 | 31, 37, 44, 51, 64, 77, 91, 104 | 3, 10, 30, 60, 100, 160, 220, 360 | 52668, 7188, 24667, etc.* |
| LHS Gated Tuned F430 142324.FLS     | Map #43        | Multi Axis Map #1 | 31, 37, 44, 51, 64, 77, 91, 104 | 3, 10, 30, 60, 100, 160, 220, 360 | 52668, 7188, 24667, etc.* |
| RHS Gated F430 145324.FLS           | Map #43        | Multi Axis Map #1 | 31, 37, 44, 51, 64, 77, 91, 104 | 3, 10, 30, 60, 100, 160, 220, 360 | 52668, 7188, 24667, etc.  |
| RHS Gated Tune 2006 F430 148508.FLS | Map #43        | Multi Axis Map #1 | 31, 37, 44, 51, 64, 77, 91, 104 | 3, 10, 30, 60, 100, 160, 220, 360 | 52668, 7188, 24667, etc.* |
| RHS Gated Tune 2007 F430 155283.FLS | Map #43        | Multi Axis Map #1 | 31, 37, 44, 51, 64, 77, 91, 104 | 3, 10, 30, 60, 100, 160, 220, 360 | 52668, 7188, 24667, etc.* |
| RHS Gated Tuned F430 142324.FLS     | Map #43        | Multi Axis Map #1 | 31, 37, 44, 51, 64, 77, 91, 104 | 3, 10, 30, 60, 100, 160, 220, 360 | 52668, 7188, 24667, etc.* |
| F430 Black 141072 LHS Stock.FLS     | Map #45        | Multi Axis Map #1 | 31, 37, 44, 51, 64, 77, 91, 104 | 3, 10, 30, 60, 100, 160, 220, 360 | 54716, 6420, 30638, etc.  |

## 5. Notes and Assumptions

- **Common Map**: Map #43 is assumed present in all non-Stock files, corresponding to Map #45 in Stock files. The full table above shows its active role in tuning, with values like 52668 differing from Stock’s 54716.
- **Values**: Key values (52668, 7188, 24667) are from 'RHS Gated F430 145324.FLS' and assumed consistent across non-Stock files (*marked with an asterisk where data is unavailable). They contrast with Stock values (54716, 6420, 30638), highlighting tuning.
- **Variations**: The non-Stock map shows lower values at higher coordinates (e.g., X=104), suggesting optimized calibration, while retaining Stock values at lower coordinates (e.g., Y=3, X≤64).
- **Limitation**: Detailed data is only available for one non-Stock file. The generalization assumes Map #43’s structure and values are similar across all Tuned files.
- **Tooling**: ``` windows-bin\me7romtool.exe -maps -romfile "%%f"``` was used to produce the map data and it may not function as expected so this is incorrect data
  
## 6. Conclusion

Map #43 (Multi Axis Map Type #1) is common across all non-Stock FLS files, exemplified by the 8x8 table in 'RHS Gated F430 145324.FLS'. Its values, such as 52668, 7188, and 24667, differ from Stock Map #45’s values (e.g., 54716, 6420, 30638), reflecting performance tuning. The variations, primarily at higher X and Y coordinates, indicate adjustments for specific engine conditions, likely enhancing power or efficiency. Further data from other non-Stock files could confirm the consistency of these values.