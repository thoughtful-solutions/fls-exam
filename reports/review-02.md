# Ferrari ME7 ROM Analysis Report
# Comparison of python and c tooling 

This report compares the outputs of the Ferrari ME7 ROM analysis tool in two different environments:
- **outputp**: Output from the tool running as romscanner.py (Python version)
- **outputw**: Output from the tool running as a Windows binary

## Overall Comparison

### Similarities
- Both versions analyze the same 16 FLS firmware files for Ferrari F430 ECUs
- Both identify and extract DPP (Data Page Pointer) setup information
- Both find and report EPK information
- Both identify the firmware as ME7.3 type

### Key Differences
- The **Python version** focuses on finding map tables (showing their locations and counts)
- The **Windows version** extracts additional details about the firmware (including metadata from string tables)

## File-by-File Analysis

| File | Version | EPK Data | DPP Setup | Maps Found | String Table |
|------|---------|----------|-----------|------------|--------------|
| F430 Black 141072 LHS Stock | Both | `/1/F136E/69/ME732//35EW2/001/080205/` | Found at 0x7746 | 13 (Python) | VMECUHN: 216391.000 (Windows) |
| F430 Black 141072 RHS Stock | Both | `/1/F136E/69/ME732//35EW2/001/080205/` | Found at 0x7746 | 13 (Python) | VMECUHN: 216391.000 (Windows) |
| LHS Gated F430 145324 | Both | `/1/F136E/69/ME732//36GW4/001/210905/` | Found at 0x7746 | 13 (Python) | VMECUHN: 222251.000 (Windows) |
| LHS Gated Tune 2006 F430 148508 | Both | `/1/F136E/69/ME732//36GW8/001/211105/` | Found at 0x7746 | 13 (Python) | VMECUHN: 222251.001 (Windows) |
| LHS Gated Tune 2007 F430 155283 | Both | `/1/F136E/69/ME732//37FW3/000/080207/` | Found at 0x7746 | 21 (Python) | VMECUHN: 236837.000 (Windows) |
| LHS Gated Tuned F430 142324 | Both | `/1/F136E/69/ME732//35EW4/001/110405/` | Found at 0x7746 | 13 (Python) | VMECUHN: 216390.001 (Windows) |
| LHS Stock 2007 F430 155283 | Both | `/1/F136E/69/ME732//37FW3/000/080207/` | Found at 0x7746 | 21 (Python) | VMECUHN: 236837.000 (Windows) |
| LHS Stock F430 142324 | Both | `/1/F136E/69/ME732//35EW2/001/080205/` | Found at 0x7746 | 13 (Python) | VMECUHN: 216391.000 (Windows) |
| LHS Stock F430 142877 | Both | `/1/F136E/69/ME732//35EW3/001/110405/` | Found at 0x7746 | 13 (Python) | VMECUHN: 216391.001 (Windows) |
| LHS Stock F430 145324 | Both | `/1/F136E/69/ME732//36GW4/001/210905/` | Found at 0x7746 | 13 (Python) | VMECUHN: 222251.000 (Windows) |
| LHS Stock | Both | `/1/F136E/69/ME732//37FW3/000/080207/` | Found at 0x7746 | 21 (Python) | VMECUHN: 236837.000 (Windows) |
| RHS Gated F430 145324 | Both | `/1/F136E/69/ME732//36GW4/001/210905/` | Found at 0x7746 | 13 (Python) | VMECUHN: 222251.000 (Windows) |
| RHS Gated Tune 2006 F430 148508 | Both | `/1/F136E/69/ME732//36GW8/001/211105/` | Found at 0x7746 | 13 (Python) | VMECUHN: 222251.001 (Windows) |
| RHS Gated Tune 2007 F430 155283 | Both | `/1/F136E/69/ME732//37FW3/000/080207/` | Found at 0x7746 | 21 (Python) | VMECUHN: 236837.000 (Windows) |
| RHS Gated Tuned F430 142324 | Both | `/1/F136E/69/ME732//35EW4/001/110405/` | Found at 0x7746 | 13 (Python) | VMECUHN: 216390.001 (Windows) |
| RHS Stock 2007 F430 155283 | Both | `/1/F136E/69/ME732//37FW3/000/080207/` | Found at 0x7746 | 21 (Python) | VMECUHN: 236837.000 (Windows) |
| RHS Stock F430 142324 | Both | `/1/F136E/69/ME732//35EW2/001/080205/` | Found at 0x7746 | 13 (Python) | VMECUHN: 216391.000 (Windows) |
| RHS Stock F430 142877 | Both | `/1/F136E/69/ME732//35EW3/001/110405/` | Found at 0x7746 | 13 (Python) | VMECUHN: 216391.001 (Windows) |
| RHS Stock F430 145324 | Both | `/1/F136E/69/ME732//36GW4/001/210905/` | Found at 0x7746 | 13 (Python) | VMECUHN: 222251.000 (Windows) |
| RHS Stock | Both | `/1/F136E/69/ME732//37FW3/000/080207/` | Found at 0x7746 | 21 (Python) | VMECUHN: 236837.000 (Windows) |

## Notable Observations

1. **Map Table Analysis**: Only the Python version reports detailed map detection, with most files having 13 identified maps, but a subset (those with EPK `/1/F136E/69/ME732//37FW3/000/080207/`) having 21 maps.

2. **Build Information**: The Windows binary output shows a build date of October 17, 2018, while the Python version appears to be reporting a more recent date (April 13, 2025 - likely the current system date).

3. **String Table**: The Windows version extracts comprehensive firmware metadata including:
   - VMECUHN: Vehicle Manufacturer ECU Hardware Number
   - SSECUHN: Bosch Hardware Number
   - SSECUSN: Bosch Serial Number
   - EROTAN: Model Description
   - TESTID: Test identifier
   - DIF and BRIF: Additional firmware identifiers

4. **Version Patterns**: Clear versioning patterns can be observed:
   - 2005 models: 35EW2
   - Early/mid 2005 updates: 35EW3, 35EW4
   - 2006 models: 36GW4
   - 2006 tuned models: 36GW8
   - 2007 models: 37FW3

5. **Hardware/Software Relationships**:
   - ECU 216391.xxx: 2005 model year (35EWx)
   - ECU 222251.xxx: 2006 model year (36GWx)
   - ECU 236837.xxx: 2007 model year (37FWx)

6. **Tuned vs. Stock**: The tool successfully identifies both factory stock ECUs and tuned variants, with tuned versions typically having incremented revision numbers.