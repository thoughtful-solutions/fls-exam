#!/usr/bin/env python3
"""
Enhanced ME7 ROM Scanner

This script scans Bosch ME7.x firmware files to identify common structures
using predefined needle patterns from the needles.c file. It provides improved
pattern matching and extraction of ECU-specific information.

Built with insights from the C implementation's needle pattern system.
"""

import sys
import os
import struct
import argparse
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Union, BinaryIO

# Constants based on the original code
SEGMENT_SIZE = 0x4000
ROM_1MB_MASK = 0xF00000
MASK = 0xFF
XXXX = 0x00

# Define needle patterns from needles.c
NEEDLE_PATTERNS = {
    # DPP Setup Needle
    'dpp_setup': {
        'needle': bytes([
            0xE6, 0x00, XXXX, XXXX,   # mov     DPP0, #XXXXh
            0xE6, 0x01, XXXX, XXXX,   # mov     DPP1, #XXXXh
            0xE6, 0x02, XXXX, XXXX,   # mov     DPP2, #XXXXh 
            0xE6, 0x03, XXXX, XXXX    # mov     DPP3, #XXXX
        ]),
        'mask': bytes([
            MASK, MASK, XXXX, XXXX,   # mov     DPP0, #XXXXh
            MASK, MASK, XXXX, XXXX,   # mov     DPP1, #XXXXh
            MASK, MASK, XXXX, XXXX,   # mov     DPP2, #XXXXh 
            MASK, MASK, XXXX, XXXX    # mov     DPP3, #XXXX
        ]),
    },
    
    # EPK Information Needle
    'epk_info': {
        'needle': bytes([
            0xF3, 0xF8, XXXX, XXXX,   # movb    rl4, EPKFZ     
            0x0D, 0x0D,               # jmpr    cc_UC, loc_XXXX
            0xF3, 0xF8, XXXX, XXXX,   # movb    rl4, EPKZUFZ   
            0x0D, 0x08,               # jmpr    cc_UC, loc_XXXX
            0xF3, 0xF8, XXXX, XXXX,   # movb    rl4, EPKEQ     
            0x0D, 0x03,               # jmpr    cc_UC, loc_XXXX
            0xF0, 0x44                # mov     r4, r4
        ]),
        'mask': bytes([
            MASK, MASK, XXXX, XXXX,
            MASK, MASK,
            MASK, MASK, XXXX, XXXX,
            MASK, MASK,
            MASK, MASK, XXXX, XXXX,
            MASK, MASK,
            MASK, MASK
        ]),
    },
    
    # KWP2000 ECU Needle (from rominfo.c)
    'kwp2000_ecu': {
        'needle': bytes([
            0xC2, 0xF4, XXXX, XXXX,     # movbz   r4, XXXX
            0xC2, 0xF5, XXXX, XXXX,     # movbz   r5, XXXX
            0x00, 0x45,                 # add     r4, r5
            0x46, 0xF4, XXXX, XXXX,     # cmp     r4, #32h 
            0xDD, 0x0C,                 # jmpr    cc_SGE, XXXX
            0xC2, 0xF4, XXXX, XXXX,     # movbz   r4, XXXX
            0xC2, 0xF5, XXXX, XXXX,     # movbz   r5, XXXX
            0x00, 0x45,                 # add     r4, r5
            0xF4, 0xA4, XXXX, XXXX      # movb    rl5, [r4+29h]
        ]),
        'mask': bytes([
            MASK, MASK, XXXX, XXXX,     # movbz   r4, XXXX
            MASK, MASK, XXXX, XXXX,     # movbz   r5, XXXX
            MASK, MASK,                 # add     r4, r5
            MASK, MASK, XXXX, XXXX,     # cmp     r4, #32h
            MASK, MASK,                 # jmpr    cc_SGE, XXXX
            MASK, MASK, XXXX, XXXX,     # movbz   r4, XXXX
            MASK, MASK, XXXX, XXXX,     # movbz   r5, XXXX
            MASK, MASK,                 # add     r4, r5
            MASK, MASK, XXXX, XXXX      # movb    rl5, [r4+XXXXh]
        ]),
    },
    
    # String Table Needle
    'string_table': {
        'needle': bytes([
            0xE6, 0xFC, XXXX, XXXX,   # mov     r12, #string_table
            0xE6, 0xFD, XXXX, XXXX,   # mov     r13, #segment
            0xDA, XXXX, XXXX, XXXX,   # calls   function, address
        ]),
        'mask': bytes([
            MASK, MASK, XXXX, XXXX,
            MASK, MASK, XXXX, XXXX,
            MASK, XXXX, XXXX, XXXX,
        ]),
    },
    
    # Map Table Needle (generic finder)
    'map_table': {
        'needle': bytes([
            0xE6, 0xFC, XXXX, XXXX,  # mov     r12, #table_address
            0xE6, 0xFD, XXXX, XXXX,  # mov     r13, #segment
            0xC2, 0xFE, XXXX, XXXX,  # movbz   r14, parameter1
            0xC2, 0xFF, XXXX, XXXX,  # movbz   r15, parameter2
            0xDA, XXXX, XXXX, XXXX,  # calls   function, address
        ]),
        'mask': bytes([
            MASK, MASK, XXXX, XXXX,  
            MASK, MASK, XXXX, XXXX,  
            MASK, MASK, XXXX, XXXX,  
            MASK, MASK, XXXX, XXXX,  
            MASK, XXXX, XXXX, XXXX,  
        ]),
    },
}

class ME7Scanner:
    def __init__(self, filename: str):
        self.filename = filename
        self.basename = os.path.basename(filename)
        self.data = self._load_file()
        self.rom_size = len(self.data)
        self.dpp_values = {
            0: None, 1: None, 2: None, 3: None
        }
        
    def _load_file(self) -> bytes:
        """Load the firmware file into memory."""
        try:
            with open(self.filename, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading file {self.filename}: {e}")
            sys.exit(1)
    
    def search_pattern(self, needle: bytes, mask: bytes, start_offset: int = 0) -> Optional[int]:
        """
        Search for a pattern in the ROM data with a mask.
        
        Args:
            needle: The byte pattern to search for
            mask: The mask to apply to the needle (0xFF = compare, 0x00 = ignore)
            start_offset: The offset to start searching from
            
        Returns:
            The offset where the pattern was found or None if not found
        """
        needle_len = len(needle)
        
        for i in range(start_offset, len(self.data) - needle_len):
            match = True
            for j in range(needle_len):
                if mask[j] == MASK and needle[j] != self.data[i + j]:
                    match = False
                    break
            if match:
                return i
        return None
    
    def get_word(self, offset: int) -> int:
        """Extract a 16-bit word from ROM data."""
        return struct.unpack("<H", self.data[offset:offset+2])[0]
    
    def get_dpp_values(self) -> Dict[int, int]:
        """Extract DPP register values from the ROM."""
        offset = self.search_pattern(
            NEEDLE_PATTERNS['dpp_setup']['needle'],
            NEEDLE_PATTERNS['dpp_setup']['mask']
        )
        
        if offset is not None:
            print(f"DPP setup found at offset: 0x{offset:X}")
            
            # Extract DPP values from the pattern
            for i in range(4):
                dpp_value = self.get_word(offset + 2 + i*4)
                phys_addr = dpp_value * SEGMENT_SIZE
                self.dpp_values[i] = dpp_value
                
                role = ""
                if i == 2:
                    role = "ram start address"
                elif i == 3:
                    role = "cpu registers"
                    
                print(f"dpp{i}: (seg: 0x{dpp_value:04X} phy:0x{phys_addr:08X}) {role}")
                
            if self.dpp_values[3] != 3:
                print("Warning: dpp3 is not 3. This may cause issues with CPU register access.")
        else:
            print("DPP setup not found. This may not be an ME7.x firmware file.")
        
        return self.dpp_values
    
    def _extract_string(self, offset: int, max_length: int = 30) -> str:
        """Extract a null-terminated string from ROM data."""
        result = ""
        for i in range(max_length):
            if offset + i >= len(self.data):
                break
            char = self.data[offset + i]
            if char == 0:
                break
            if 32 <= char <= 126:  # ASCII printable
                result += chr(char)
            else:
                result += '.'
        return result
    
    def find_epk_info(self) -> Optional[str]:
        """
        Find and extract the EPK information from the ROM using techniques
        from the C implementation in rominfo.c
        """
        # First try to find the EPK info needle
        epk_offset = self.search_pattern(
            NEEDLE_PATTERNS['epk_info']['needle'],
            NEEDLE_PATTERNS['epk_info']['mask']
        )
        
        if epk_offset is not None:
            print(f"found needle at offset=0x{epk_offset:X}.")
        
        # Following rominfo.c approach, use the KWP2000 ECU needle pattern
        kwp_offset = self.search_pattern(
            NEEDLE_PATTERNS['kwp2000_ecu']['needle'],
            NEEDLE_PATTERNS['kwp2000_ecu']['mask']
        )
        
        if kwp_offset is not None:
            print(f"found KWP2000 ECU pattern at offset=0x{kwp_offset:X}.")
            
            # Extract the address pointer to the EPK data - offset +28 bytes in the pattern
            val = self.get_word(kwp_offset + 28)
            
            # Use dpp1 value (segment pointer) as in the C code
            if self.dpp_values[1] is None:
                # Try to get DPP values if not already done
                if all(v is None for v in self.dpp_values.values()):
                    self.get_dpp_values()
                    
            seg = self.dpp_values[1] - 1 if self.dpp_values[1] is not None else 0
            
            # Calculate physical address and file offset as in the C code
            phys_addr = (seg * SEGMENT_SIZE) + val
            file_offset = phys_addr & ~ROM_1MB_MASK
            
            # Extract EPK string data
            epk_data = ""
            try:
                # Extract the string using approach from rominfo.c
                addr = file_offset
                if addr < len(self.data):
                    # Skip first two bytes (length indicator)
                    i = 2
                    max_len = 64  # Safety limit
                    while i < max_len and addr + i < len(self.data):
                        ch = self.data[addr + i]
                        if ch == 0:
                            break
                        if 32 <= ch <= 126:  # ASCII printable
                            epk_data += chr(ch)
                        else:
                            break
                        i += 1
                        
                    print(f"EPK: @ 0x{addr:X} {{ {epk_data} }}")
                    return epk_data
                else:
                    print(f"EPK address (0x{addr:X}) out of range")
            except Exception as e:
                print(f"Error extracting EPK data: {e}")
        else:
            # Fallback: Look for EPK data based on common patterns
            if epk_offset is not None:
                # Look for EPK data around the found needle
                # Common locations are around offset 0x10000-0x11000
                epk_region_start = 0x10000
                epk_region_end = 0x11000
                
                for i in range(epk_region_start, epk_region_end):
                    # Look for typical EPK start markers
                    if i < len(self.data) and (self.data[i] == ord('/') or self.data[i] == ord('3')) and i+1 < len(self.data) and self.data[i+1] == ord('/'):
                        epk_data = self._extract_string(i, 50)
                        if len(epk_data) > 10 and ('ME7' in epk_data or 'F136E' in epk_data):
                            print(f"EPK: @ 0x{i:X} {{ {epk_data} }}")
                            return epk_data
            
            print("EPK info pattern not found")
        
        return None
    
    def find_string_table(self) -> Dict[str, str]:
        """Find and extract the ROM string table information."""
        string_table_offset = None
        string_table = {}
        
        # Search for the string table needle
        offset = self.search_pattern(
            NEEDLE_PATTERNS['string_table']['needle'],
            NEEDLE_PATTERNS['string_table']['mask']
        )
        
        if offset is None:
            print("String table needle not found")
            return {}
            
        print(f"found needle at offset=0x{offset:X}")
        
        # Extract table address from needle
        table_offset = self.get_word(offset + 2)
        segment = self.get_word(offset + 6)
        
        # Calculate physical address
        table_addr = (segment * SEGMENT_SIZE) + table_offset
        file_offset = table_addr & ~ROM_1MB_MASK
        
        print(f"found table at offset={file_offset:08X}.")
        
        # Common string IDs and their meaning
        id_meanings = {
            'VMECUHN': "Vehicle Manufacturer ECU Hardware Number SKU",
            'SSECUHN': "Bosch Hardware Number",
            'SSECUSN': "Bosch Serial Number",
            'EROTAN': "Model Description",
            'TESTID': "TESTID",
            'DIF': "DIF",
            'BRIF': "BRIF"
        }
        
        # Search for common string identifiers
        common_ids = ['VMECUHN', 'SSECUHN', 'SSECUSN', 'EROTAN', 'TESTID', 'DIF', 'BRIF']
        found_ids = {}
        
        # Search in a range around the string table
        search_start = max(0, file_offset - 0x1000)
        search_end = min(len(self.data), file_offset + 0x1000)
        
        # Find the string entries
        idx = 1
        for i in range(search_start, search_end, 4):
            for id_str in common_ids:
                id_pos = self.data.find(id_str.encode('ascii'), i, i + 200)
                if id_pos != -1 and id_str not in found_ids:
                    # Look for string data before the ID
                    string_pos = id_pos - 50
                    if string_pos > 0:
                        # Find a null-terminated string before the ID
                        for j in range(string_pos, id_pos):
                            if self.data[j] == 0:
                                string_start = j + 1
                                string_value = self._extract_string(string_start, 30)
                                if string_value and len(string_value) > 3:
                                    string_value = string_value.ljust(22)
                                    addr_hex = 0x10000 + (string_start % 0x10000)
                                    print(f"Idx={idx}   {{ {string_value} }} 0x{addr_hex:X} : {id_str} [{id_meanings.get(id_str, '')}]")
                                    found_ids[id_str] = string_value
                                    idx += 1
                                break
        
        return found_ids
    
    def find_maps(self) -> List[Dict]:
        """Find map tables in the ROM."""
        maps = []
        offset = 0
        
        print("\nScanning for map tables...")
        
        while True:
            offset = self.search_pattern(
                NEEDLE_PATTERNS['map_table']['needle'],
                NEEDLE_PATTERNS['map_table']['mask'],
                offset
            )
            
            if offset is None or offset >= len(self.data) - 20:
                break
                
            # Extract map information
            map_offset = self.get_word(offset + 2)  # Offset in the "mov r12, #XXXX" instruction
            seg_value = self.get_word(offset + 6)   # Segment value in the "mov r13, #XXXX" instruction
            
            # Calculate physical address
            phys_addr = (seg_value * SEGMENT_SIZE) + map_offset
            file_offset = phys_addr & ~ROM_1MB_MASK
            
            map_info = {
                'needle_offset': offset,
                'map_offset': map_offset,
                'segment': seg_value,
                'physical_address': phys_addr,
                'file_offset': file_offset
            }
            
            maps.append(map_info)
            print(f"Map found: needle at 0x{offset:X}, table at 0x{file_offset:X} (phys: 0x{phys_addr:X})")
            
            # Continue searching from after this match
            offset += len(NEEDLE_PATTERNS['map_table']['needle'])
        
        print(f"Total maps found: {len(maps)}")
        return maps
    
    def analyze(self) -> Dict:
        """Perform a comprehensive analysis of the ROM file."""
        print(f"Analyzing {self.basename}...")
        print(f"ROM size: {self.rom_size:,} bytes")
        
        # Get DPP values
        self.get_dpp_values()
        
        # Get EPK info
        print("\n>>> Scanning for EPK information [info] \n")
        epk_info = self.find_epk_info()
        
        # Get string table info if EPK found
        if epk_info or True:  # Always try to find string table for compatibility
            print("\n>>> Scanning for ROM String Table Byte Sequence #1 [info] \n")
            string_info = self.find_string_table()
        
        # Find maps
        maps = self.find_maps()
        
        results = {
            "filename": self.filename,
            "size": self.rom_size,
            "dpp_values": self.dpp_values,
            "epk_info": epk_info,
            "maps": maps,
            "string_info": string_info if 'string_info' in locals() else {}
        }
        
        return results

def print_header():
    """Print the tool header information."""
    version = "1.6"
    build_date = datetime.now().strftime("%b %d %Y %H:%M:%S")
    
    print(f"Ferrari 360 ME7.3H4 Rom Tool. *BETA TEST* Last Built: {build_date} v{version}")
    print("by 360trev.  Needle lookup function borrowed from nyet (Thanks man!) from")
    print("the ME7sum tool development (see github). ")
    print("")
    print("..Now fixed and working on 64-bit hosts, Linux, Apple and Android devices ;)")
    print("")

def main():
    parser = argparse.ArgumentParser(description="Enhanced ME7 ROM Scanner")
    parser.add_argument("filename", help="ME7 ROM file to analyze")
    parser.add_argument("--maps", action="store_true", help="Scan for map tables")
    parser.add_argument("--epk", action="store_true", help="Extract EPK information")
    parser.add_argument("--all", action="store_true", help="Perform all analysis")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.filename):
        print(f"File not found: {args.filename}")
        sys.exit(1)
    
    print_header()
    print(f"þ Opening '{os.path.basename(args.filename)}' file")
    print("Succeded loading file.")
    print("")
    print("Loaded ROM: Tool in 1Mb Mode")
    print("")
    
    print("-[ DPPx Setup Analysis ]-----------------------------------------------------------------")
    print("")
    print(">>> Scanning for Main ROM DPPx setup #1 [to extract dpp0, dpp1, dpp2, dpp3 from rom] ")
    print("")
    
    scanner = ME7Scanner(args.filename)
    
    if args.all or (not args.maps and not args.epk):
        scanner.analyze()
    else:
        if args.maps:
            scanner.find_maps()
        if args.epk:
            print("\n-[ Basic Firmware information ]-----------------------------------------------------------------")
            print("")
            print(">>> Scanning for EPK information [info] ")
            print("")
            scanner.find_epk_info()

if __name__ == "__main__":
    main()