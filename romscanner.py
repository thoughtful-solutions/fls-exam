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
import csv
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

# Known map definitions from table_spec.c
KNOWN_MAPS = {
    'KFAGK': {
        'desc': "Exhaust Flap Control Table",
        'x_num_width': 1,     # UBYTE
        'y_num_width': 1,     # UBYTE
        'x_axis_width': 1,    # UBYTE
        'y_axis_width': 1,    # UBYTE
        'cell_width': 1,      # UBYTE
        'x_axis_conv': 0.025, # Conversion factor
        'x_axis_desc': "Upm", # Description
        'y_axis_conv': 1.333333,
        'y_axis_desc': "%",
        'cell_conv': 1.0,
        'cell_desc': ""
    },
    'KFPED': {
        'desc': "Throttle Pedal Characteristic",
        'x_num_width': 2,     # UWORD
        'y_num_width': 2,     # UWORD 
        'x_axis_width': 2,    # UWORD
        'y_axis_width': 2,    # UWORD
        'cell_width': 2,      # UWORD
        'x_axis_conv': 655.35,
        'x_axis_desc': "% PED",
        'y_axis_conv': 4.0,
        'y_axis_desc': "U/min",
        'cell_conv': 327.68,
        'cell_desc': "%"
    },
    'KFKHFM': {
        'desc': "MAF Sensor correction by Load and RPM",
        'x_num_width': 1,     # UBYTE
        'y_num_width': 1,     # UBYTE 
        'x_axis_width': 1,    # UBYTE
        'y_axis_width': 1,    # UBYTE
        'cell_width': 1,      # UBYTE
        'x_axis_conv': 0.025,
        'x_axis_desc': "Upm",
        'y_axis_conv': 1.333333,
        'y_axis_desc': "%",
        'cell_conv': 1.0,
        'cell_desc': ""
    },
    'KFNW': {
        'desc': "Variable Camshaft Control",
        'x_num_width': 1,     # UBYTE
        'y_num_width': 1,     # UBYTE 
        'x_axis_width': 1,    # UBYTE
        'y_axis_width': 1,    # UBYTE
        'cell_width': 1,      # UBYTE
        'x_axis_conv': 0.025,
        'x_axis_desc': "Upm",
        'y_axis_conv': 1.333333,
        'y_axis_desc': "%",
        'cell_conv': 1.0,
        'cell_desc': ""
    },
    'KFZW': {
        'desc': "Ignition Timing",
        'x_num_width': 1,     # UBYTE
        'y_num_width': 1,     # UBYTE 
        'x_axis_width': 1,    # UBYTE
        'y_axis_width': 1,    # UBYTE
        'cell_width': 1,      # UBYTE
        'x_axis_conv': 0.025,
        'x_axis_desc': "Upm",
        'y_axis_conv': 1.333333,
        'y_axis_desc': "%",
        'cell_conv': 1.3333,
        'cell_desc': "grad KW"
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
        """Find map tables in the ROM and extract their structure."""
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
            
            # Try to identify map type and extract structure
            map_data = self.extract_map_data(file_offset)
            
            map_info = {
                'needle_offset': offset,
                'map_offset': map_offset,
                'segment': seg_value,
                'physical_address': phys_addr,
                'file_offset': file_offset,
                'map_data': map_data
            }
            
            maps.append(map_info)
            
            map_name = map_data.get('name', 'Unknown')
            x_size = map_data.get('x_size', '?')
            y_size = map_data.get('y_size', '?')
            print(f"Map found: '{map_name}' at 0x{file_offset:X} (phys: 0x{phys_addr:X}), size: {x_size}x{y_size}")
            
            # Continue searching from after this match
            offset += len(NEEDLE_PATTERNS['map_table']['needle'])
        
        print(f"Total maps found: {len(maps)}")
        return maps

    def extract_map_data(self, offset: int) -> Dict:
        """
        Extract and analyze map data structure.
        Based on the C implementation in show_tables.c and table_spec.c
        
        Maps commonly follow this structure:
        - X number of elements (1 byte)
        - Y number of elements (1 byte)
        - X axis data (X_num * X_width bytes)
        - Y axis data (Y_num * Y_width bytes)
        - Cell data (X_num * Y_num * cell_width bytes)
        """
        # Try to identify map type by its pattern or location
        map_type = self.identify_map_type(offset)
        
        # Get map definition or use defaults
        map_def = KNOWN_MAPS.get(map_type, {
            'desc': f"Unknown Map at 0x{offset:X}",
            'x_num_width': 1,  # UBYTE
            'y_num_width': 1,  # UBYTE
            'x_axis_width': 1, # UBYTE
            'y_axis_width': 1, # UBYTE
            'cell_width': 1,   # UBYTE
            'x_axis_conv': 1.0,
            'x_axis_desc': "",
            'y_axis_conv': 1.0,
            'y_axis_desc': "",
            'cell_conv': 1.0,
            'cell_desc': ""
        })
        
        # Extract map dimensions and structure
        try:
            x_num_width = map_def['x_num_width']
            y_num_width = map_def['y_num_width']
            x_axis_width = map_def['x_axis_width']
            y_axis_width = map_def['y_axis_width']
            cell_width = map_def['cell_width']
            
            # Read map dimensions
            if offset + x_num_width > len(self.data):
                return {'name': map_type, 'error': "Offset out of range"}
            
            if x_num_width == 1:
                x_size = self.data[offset]
            else:  # Assume 2 bytes (UWORD)
                x_size = self.get_word(offset)
                
            if y_num_width == 0:  # 1D map (no Y dimension)
                y_size = 0
            elif offset + x_num_width + y_num_width <= len(self.data):
                if y_num_width == 1:
                    y_size = self.data[offset + x_num_width]
                else:  # Assume 2 bytes (UWORD)
                    y_size = self.get_word(offset + x_num_width)
            else:
                return {'name': map_type, 'error': "Y dimension out of range"}
                
            # Sanity check on dimensions
            if x_size > 50 or y_size > 50:
                # Probably not a valid map or wrong structure
                return {
                    'name': map_type,
                    'error': f"Suspicious dimensions: {x_size}x{y_size}",
                    'x_size': x_size if x_size <= 50 else '?',
                    'y_size': y_size if y_size <= 50 else '?'
                }
                
            # Read X axis data
            x_axis_start = offset + x_num_width + y_num_width
            x_axis_data = []
            
            for i in range(x_size):
                if x_axis_start + i * x_axis_width + x_axis_width <= len(self.data):
                    if x_axis_width == 1:
                        value = self.data[x_axis_start + i]
                    else:  # Assume 2 bytes (UWORD)
                        value = self.get_word(x_axis_start + i * x_axis_width)
                    x_axis_data.append(value)
                else:
                    x_axis_data.append(0)  # Out of range
            
            # Read Y axis data (if applicable)
            y_axis_data = []
            
            if y_size > 0:
                y_axis_start = x_axis_start + (x_size * x_axis_width)
                
                for i in range(y_size):
                    if y_axis_start + i * y_axis_width + y_axis_width <= len(self.data):
                        if y_axis_width == 1:
                            value = self.data[y_axis_start + i]
                        else:  # Assume 2 bytes (UWORD)
                            value = self.get_word(y_axis_start + i * y_axis_width)
                        y_axis_data.append(value)
                    else:
                        y_axis_data.append(0)  # Out of range
            
            # Read cell data
            cell_data = []
            
            if y_size > 0:
                cell_start = y_axis_start + (y_size * y_axis_width)
                
                # 2D map: create a 2D array of cells
                for y in range(y_size):
                    row = []
                    for x in range(x_size):
                        cell_offset = cell_start + ((y * x_size) + x) * cell_width
                        if cell_offset + cell_width <= len(self.data):
                            if cell_width == 1:
                                value = self.data[cell_offset]
                            else:  # Assume 2 bytes (UWORD)
                                value = self.get_word(cell_offset)
                        else:
                            value = 0  # Out of range
                        row.append(value)
                    cell_data.append(row)
            else:
                # 1D map: create a single row
                cell_start = x_axis_start + (x_size * x_axis_width)
                row = []
                
                for x in range(x_size):
                    cell_offset = cell_start + x * cell_width
                    if cell_offset + cell_width <= len(self.data):
                        if cell_width == 1:
                            value = self.data[cell_offset]
                        else:  # Assume 2 bytes (UWORD)
                            value = self.get_word(cell_offset)
                    else:
                        value = 0  # Out of range
                    row.append(value)
                cell_data.append(row)
            
            # Convert to human-readable values
            x_axis_data_conv = [val / map_def.get('x_axis_conv', 1.0) for val in x_axis_data]
            y_axis_data_conv = [val / map_def.get('y_axis_conv', 1.0) for val in y_axis_data] if y_axis_data else []
            
            cell_data_conv = []
            for row in cell_data:
                cell_data_conv.append([val / map_def.get('cell_conv', 1.0) for val in row])
            
            return {
                'name': map_type,
                'description': map_def.get('desc', ''),
                'x_size': x_size,
                'y_size': y_size,
                'x_axis_data': x_axis_data,
                'y_axis_data': y_axis_data,
                'cell_data': cell_data,
                'x_axis_data_conv': x_axis_data_conv,
                'y_axis_data_conv': y_axis_data_conv,
                'cell_data_conv': cell_data_conv,
                'x_num_width': x_num_width,
                'y_num_width': y_num_width,
                'x_axis_width': x_axis_width,
                'y_axis_width': y_axis_width,
                'cell_width': cell_width,
                'x_axis_conv': map_def.get('x_axis_conv', 1.0),
                'x_axis_desc': map_def.get('x_axis_desc', ''),
                'y_axis_conv': map_def.get('y_axis_conv', 1.0),
                'y_axis_desc': map_def.get('y_axis_desc', ''),
                'cell_conv': map_def.get('cell_conv', 1.0),
                'cell_desc': map_def.get('cell_desc', '')
            }
            
        except Exception as e:
            return {
                'name': map_type,
                'error': str(e)
            }

    def identify_map_type(self, offset: int) -> str:
        """
        Try to identify the map type based on its location and structure.
        This is a heuristic approach that could be improved with more
        detailed pattern matching.
        """
        # Look for common signatures in nearby code that might indicate map type
        # This would require more detailed analysis of ROM patterns
        
        # For now, just create a generic name based on the offset
        map_name = f"MAP_0x{offset:X}"
        
        # In a real implementation, we would look for patterns in surrounding data
        # to identify common maps like KFAGK, KFPED, etc.
        # For demonstration, just use a basic signature approach
        
        # This is just a placeholder - actual implementation would need more ROM-specific logic
        signatures = {
            'KFAGK': b'KFAGK',
            'KFPED': b'KFPED',
            'KFKHFM': b'KFKHFM',
            'KFNW': b'KFNW',
            'KFZW': b'KFZW',
        }
        
        # Check for signatures within a reasonable range
        search_range = 256  # bytes
        start = max(0, offset - search_range)
        end = min(len(self.data), offset + search_range)
        
        for map_type, signature in signatures.items():
            if self.data.find(signature, start, end) != -1:
                return map_type
        
        return map_name

    def display_map(self, map_data: Dict, human_readable: bool = True) -> None:
        """
        Display a map in human-readable format.
        
        Args:
            map_data: The map data dictionary from extract_map_data()
            human_readable: If True, apply conversions for human-readable values
        """
        if not map_data or 'error' in map_data:
            print(f"Error displaying map: {map_data.get('error', 'Unknown error')}")
            return
        
        print(f"\n{map_data['name']}")
        if 'description' in map_data:
            print(f"{map_data['description']}")
        print("=" * len(map_data['name']))
        print(f"Size: {map_data['x_size']}x{map_data['y_size']}")
        
        # Display structure information
        print("\nMap Structure:")
        print(f"X-axis: {map_data['x_num_width']} bytes, conversion factor: {map_data['x_axis_conv']}, unit: {map_data['x_axis_desc']}")
        if map_data['y_size'] > 0:
            print(f"Y-axis: {map_data['y_num_width']} bytes, conversion factor: {map_data['y_axis_conv']}, unit: {map_data['y_axis_desc']}")
        print(f"Cell data: {map_data['cell_width']} bytes, conversion factor: {map_data['cell_conv']}, unit: {map_data['cell_desc']}")
        
        # Choose which data to display based on human_readable flag
        x_axis_values = map_data['x_axis_data_conv'] if human_readable else map_data['x_axis_data']
        y_axis_values = map_data['y_axis_data_conv'] if human_readable else map_data['y_axis_data']
        cell_values = map_data['cell_data_conv'] if human_readable else map_data['cell_data']
        
        # Display header with X-axis values
        print("\nX-axis values:")
        print("    ", end="")
        for x in range(min(10, map_data['x_size'])):  # Limit to first 10 columns for readability
            if human_readable:
                print(f"{x_axis_values[x]:8.2f}", end="")
            else:
                print(f"{x_axis_values[x]:8d}", end="")
                
        if map_data['x_size'] > 10:
            print(" ...")
        else:
            print()
        
        # Display Y-axis and cell data
        print("\nMap data (Y-axis, cells):")
        y_range = min(20, map_data['y_size']) if map_data['y_size'] > 0 else 1
        
        for y in range(y_range):
            # Display Y-axis value if available
            if map_data['y_size'] > 0:
                if human_readable:
                    print(f"{y_axis_values[y]:4.1f} |", end="")
                else:
                    print(f"{y_axis_values[y]:4d} |", end="")
            else:
                print("     |", end="")
            
            # Display cell values
            for x in range(min(10, map_data['x_size'])):
                if human_readable:
                    print(f"{cell_values[y][x]:8.2f}", end="")
                else:
                    print(f"{cell_values[y][x]:8d}", end="")
            
            if map_data['x_size'] > 10:
                print(" ...")
            else:
                print()
        
        if map_data['y_size'] > 20:
            print("...")
            
    def export_map_to_csv(self, map_data: Dict, filename: str, human_readable: bool = True) -> bool:
        """
        Export map data to a CSV file.
        
        Args:
            map_data: The map data dictionary from extract_map_data()
            filename: The file to write to
            human_readable: If True, export converted values; otherwise, raw values
            
        Returns:
            True if successful, False if there was an error
        """
        if not map_data or 'error' in map_data:
            print(f"Error exporting map: {map_data.get('error', 'Unknown error')}")
            return False
            
        try:
            # Choose which data to export based on human_readable flag
            x_axis_values = map_data['x_axis_data_conv'] if human_readable else map_data['x_axis_data']
            y_axis_values = map_data['y_axis_data_conv'] if human_readable else map_data['y_axis_data']
            cell_values = map_data['cell_data_conv'] if human_readable else map_data['cell_data']
            
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header row with map information
                writer.writerow([f"Map: {map_data['name']}", f"Description: {map_data.get('description', '')}"])
                
                if human_readable:
                    writer.writerow([
                        f"X-axis unit: {map_data.get('x_axis_desc', '')}",
                        f"Y-axis unit: {map_data.get('y_axis_desc', '')}",
                        f"Cell unit: {map_data.get('cell_desc', '')}"
                    ])
                
                # Write X-axis header
                header_row = ["Y/X"]
                for x_val in x_axis_values:
                    if human_readable:
                        header_row.append(f"{x_val:.2f}")
                    else:
                        header_row.append(str(x_val))
                writer.writerow(header_row)
                
                # Write Y-axis and cell data
                y_range = map_data['y_size'] if map_data['y_size'] > 0 else 1
                
                for y in range(y_range):
                    # Start with Y-axis value if available
                    if map_data['y_size'] > 0:
                        if human_readable:
                            row = [f"{y_axis_values[y]:.2f}"]
                        else:
                            row = [str(y_axis_values[y])]
                    else:
                        row = [""]
                    
                    # Add cell values
                    for x in range(map_data['x_size']):
                        if human_readable:
                            row.append(f"{cell_values[y][x]:.2f}")
                        else:
                            row.append(str(cell_values[y][x]))
                    
                    writer.writerow(row)
            
            return True
        except Exception as e:
            print(f"Error exporting map to CSV: {e}")
            return False
    
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
        string_info = {}
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
            "string_info": string_info
        }
        
        return results

def print_header():
    """Print the tool header information."""
    version = "1.6"
    build_date = datetime.now().strftime("%b %d %Y %H:%M:%S")
    
    print(f"romscanner.py Last Built: {build_date} v{version}")
    print("based on code from  https://github.com/360trev/ME7RomTool_Ferrari ")
  

def main():
    parser = argparse.ArgumentParser(description="Enhanced ME7 ROM Scanner")
    parser.add_argument("filename", help="ME7 ROM file to analyze")
    parser.add_argument("--maps", action="store_true", help="Scan for map tables")
    parser.add_argument("--epk", action="store_true", help="Extract EPK information")
    parser.add_argument("--all", action="store_true", help="Perform all analysis")
    parser.add_argument("--show-map", type=str, help="Display a specific map by name or address")
    parser.add_argument("--export-maps", type=str, help="Export maps to CSV files in the specified directory")
    parser.add_argument("--raw", action="store_true", help="Display/export raw values instead of human-readable values")
    
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
    
    results = None
    
    if args.all or (not args.maps and not args.epk and not args.show_map and not args.export_maps):
        results = scanner.analyze()
    else:
        # Initialize dpp values which may be needed for other operations
        scanner.get_dpp_values()
        
        if args.maps:
            maps = scanner.find_maps()
            if results is None:
                results = {"maps": maps}
            else:
                results["maps"] = maps
                
        if args.epk:
            print("\n-[ Basic Firmware information ]-----------------------------------------------------------------")
            print("")
            print(">>> Scanning for EPK information [info] ")
            print("")
            epk_info = scanner.find_epk_info()
            if results is None:
                results = {"epk_info": epk_info}
            else:
                results["epk_info"] = epk_info
    
    # Handle map display and export if requested
    if args.show_map and results and "maps" in results:
        # Find and display a specific map
        map_found = False
        for map_info in results["maps"]:
            map_name = map_info['map_data'].get('name', '')
            map_addr = f"0x{map_info['file_offset']:X}"
            
            if args.show_map.lower() in map_name.lower() or args.show_map.lower() == map_addr.lower():
                scanner.display_map(map_info['map_data'], not args.raw)
                map_found = True
        
        if not map_found:
            print(f"Map not found: {args.show_map}")
    
    if args.export_maps and results and "maps" in results:
        # Create export directory if it doesn't exist
        os.makedirs(args.export_maps, exist_ok=True)
        
        # Export all maps to CSV files
        for i, map_info in enumerate(results["maps"]):
            map_data = map_info['map_data']
            
            if 'error' in map_data:
                print(f"Skipping map {i} due to error: {map_data['error']}")
                continue
                
            map_name = map_data.get('name', f"map_{i}")
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', map_name)  # Create safe filename
            
            # Export to CSV
            filename = os.path.join(args.export_maps, f"{safe_name}.csv")
            if scanner.export_map_to_csv(map_data, filename, not args.raw):
                print(f"Exported {map_name} to {filename}")

if __name__ == "__main__":
    main()