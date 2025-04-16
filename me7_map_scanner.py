#!/usr/bin/env python3
"""
ME7.x ROM Map Table Scanner
A Python implementation of the ME7 map table scanner tool

This tool scans through ME7.x ROM files to identify and display
map tables used in the ECU's programming.
"""

import argparse
import struct
import os
import sys
from typing import List, Dict, Tuple, Optional, Union

# Constants
SEGMENT_SIZE = 0x4000
ROM_1MB_MASK = 0x100000
MAX_TABLE_SEARCHES = 4000
MAX_SEARCH_BACK_BYTES = 3500

# Placeholder for table definitions
class TableDef:
    """Definition of a table structure for display"""
    def __init__(self, name, desc, 
                x_num_width, y_num_width, 
                x_axis_width, y_axis_width, 
                cell_width):
        self.table_name = name
        self.table_desc = desc
        self.x_num_nwidth = x_num_width
        self.y_num_nwidth = y_num_width
        self.x_axis_nwidth = x_axis_width
        self.y_axis_nwidth = y_axis_width
        self.cell_nwidth = cell_width
        
        # Default entry definitions
        self.x_axis = {
            'field_name': 'X-axis', 
            'conv': '1.0', 
            'desc': ' ', 
            'fmt_PHY': '%8.2f ', 
            'fmt_HEX': '0x%X ', 
            'fmt_ADR': '  %#6x ',
            'otype': '/',  # Operation type
            'conv2': None  # Secondary conversion value
        }
        
        self.y_axis = {
            'field_name': 'Y-axis', 
            'conv': '1.0', 
            'desc': ' ', 
            'fmt_PHY': ' %-5.0f ', 
            'fmt_HEX': '%-#8.4x ', 
            'fmt_ADR': '%-#9.5x ',
            'otype': '/',
            'conv2': None
        }
        
        self.cell = {
            'field_name': 'Cells', 
            'conv': '1.0', 
            'desc': ' ', 
            'fmt_PHY': '%8.0f ', 
            'fmt_HEX': '  %#6x ', 
            'fmt_ADR': '%-#9.5x',
            'otype': '/',
            'conv2': None
        }

# Define default table for 2D maps
XXXX_table = TableDef(
    name="XXX Type #1",
    desc="Not yet defined.", 
    x_num_width=1, 
    y_num_width=1, 
    x_axis_width=1, 
    y_axis_width=2, 
    cell_width=2
)

# Define default table for 1D maps
XXXXB_table = TableDef(
    name="XXX Type #2",
    desc="Single X axis tables.", 
    x_num_width=1, 
    y_num_width=0, 
    x_axis_width=1, 
    y_axis_width=0, 
    cell_width=1
)

# Constants for needle patterns
SKIP = 0x00
XXXX = 0x00
MASK = 0xff

# Define needle patterns for 1D map finders
mapfinder_needle = bytearray([
    0xE6, 0xFC, XXXX, XXXX,  # mov     r12, #(MAP_X_NUM - ROM_MAP_REGION_818000)
    0xE6, 0xFD, XXXX, XXXX,  # mov     r13, #XXXXh
    0xC2, 0xFE, XXXX, XXXX,  # movbz   r14, XXXX
    0xDA, XXXX, XXXX, XXXX,  # calls   XXXXh, Lookup_Table_Data
])

mapfinder_mask = bytearray([
    MASK, MASK, XXXX, XXXX,  # mov     r12, #(MAP_X_NUM - ROM_MAP_REGION_818000)
    MASK, MASK, XXXX, XXXX,  # mov     r13, #XXXXh
    MASK, MASK, XXXX, XXXX,  # movbz   r14, XXXX
    MASK, XXXX, XXXX, XXXX,  # calls   XXXXh, Lookup_Table_Data
])

# Define needle patterns for 2D map finders
mapfinder_xy2_needle = bytearray([
    0xE6, 0xF4, XXXX, XXXX,  # mov     r4, #XXXX_DATA_TBL
    0xE6, 0xF5, XXXX, XXXX,  # mov     r5, #XXXXh
    0x88, 0x50,              # mov     [-r0], r5
    0x88, 0x40,              # mov     [-r0], r4
    0xE6, 0xF4, XXXX, XXXX,  # mov     r4, #XXXX_Y_AXIS
    0xE6, 0xF5, XXXX, XXXX,  # mov     r5, #XXXXh
    0x88, 0x50,              # mov     [-r0], r5
    0x88, 0x40,              # mov     [-r0], r4
    0xD7, 0x40, XXXX, XXXX,  # extp    #XXXXh, #1
    0xC2, 0xFC, XXXX, XXXX,  # movbz   r12, XXXX_X_NUM
    0xE6, 0xFD, XXXX, XXXX,  # mov     r13, #XXXX_X_AXIS
    0xE6, 0xFE, XXXX, XXXX,  # mov     r14, #XXXXh
    0xD7, 0x40, XXXX, XXXX,  # extp    #XXXXh, #1
    0xC2, 0xFF, XXXX, XXXX,  # movbz   r15, XXXX_Y_NUM
    0xDA, XXXX, XXXX, XXXX,  # calls   XXXXh, XXXX_Lookup_func
])

mapfinder_xy2_mask = bytearray([
    MASK, MASK, XXXX, XXXX,  # mov     r4, #XXXX_DATA_TBL
    MASK, MASK, XXXX, XXXX,  # mov     r5, #XXXXh
    MASK, MASK,              # mov     [-r0], r5
    MASK, MASK,              # mov     [-r0], r4
    MASK, MASK, XXXX, XXXX,  # mov     r4, #XXXX_Y_AXIS
    MASK, MASK, XXXX, XXXX,  # mov     r5, #XXXXh
    MASK, MASK,              # mov     [-r0], r5
    MASK, MASK,              # mov     [-r0], r4
    MASK, MASK, XXXX, XXXX,  # extp    #XXXXh, #1
    MASK, MASK, XXXX, XXXX,  # movbz   r12, XXXX_X_NUM
    MASK, MASK, XXXX, XXXX,  # mov     r13, #XXXX_X_AXIS
    MASK, MASK, XXXX, XXXX,  # mov     r14, #XXXXh
    MASK, MASK, XXXX, XXXX,  # extp    #XXXXh, #1
    MASK, MASK, XXXX, XXXX,  # movbz   r15, XXXX_Y_NUM
    MASK, XXXX, XXXX, XXXX,  # calls   XXXXh, XXXX_Lookup_func
])

# Define needle patterns for single axis map finders
mapfinder_xy3_needle = bytearray([
    0x88, 0x50,              # mov     [-r0], r5
    0xE6, 0xFC, XXXX, XXXX,  # mov     r12, #XXXX
    0xE6, 0xFD, XXXX, XXXX,  # mov     r13, #XXXXh
    0xE6, 0xFE, XXXX, XXXX,  # mov     r14, #XXXX
    0xE6, 0xFF, XXXX, XXXX,  # mov     r15, #XXXXh
    0xDA, XXXX, XXXX, XXXX,  # calls   XXXXh, Lookup_XXXX
    0x08, 0x04               # add     r0,  #4
])

mapfinder_xy3_mask = bytearray([
    MASK, MASK,              # mov     [-r0], r5
    MASK, MASK, XXXX, XXXX,  # mov     r12, #XXXX
    MASK, MASK, XXXX, XXXX,  # mov     r13, #XXXXh
    MASK, MASK, XXXX, XXXX,  # mov     r14, #XXXX
    MASK, MASK, XXXX, XXXX,  # mov     r15, #XXXXh
    MASK, XXXX, XXXX, XXXX,  # calls   XXXXh, Lookup_XXXX
    MASK, MASK
])

# Global variables for configuration
show_phy = True
show_hex = True
show_adr = True
show_diss = False
dpp1_value = 0x0205  # Default DPP1 value for segment calculations
seg_start = 0x800000  # Starting segment address for display

def get16(data: bytes, offset: int = 0) -> int:
    """Extract a 16-bit little-endian value from data."""
    if offset + 2 > len(data):
        return 0
    return struct.unpack("<H", data[offset:offset+2])[0]

def get32(data: bytes, offset: int = 0) -> int:
    """Extract a 32-bit little-endian value from data."""
    if offset + 4 > len(data):
        return 0
    return struct.unpack("<I", data[offset:offset+4])[0]

def get_nwidth(data: bytes, offset: int, nwidth: int) -> int:
    """Extract a value of specified width from data."""
    if offset >= len(data):
        return 0
        
    if nwidth == 0:
        return 0
    elif nwidth == 1:
        if offset < len(data):
            return data[offset]
        return 0
    elif nwidth == 2:
        return get16(data, offset)
    elif nwidth == 4:
        return get32(data, offset)
    else:
        return 0

def search(rom_data: bytes, needle: bytearray, mask: bytearray, start_offset: int = 0) -> Optional[int]:
    """Search for a pattern with a mask in a binary file starting from offset.
    Returns the offset where pattern is found, or None if not found.
    """
    needle_len = len(needle)
    if needle_len != len(mask):
        raise ValueError("Needle and mask must be the same length")
    
    try:
        end = len(rom_data) - needle_len
        if end <= start_offset:
            return None
            
        for i in range(start_offset, end):
            match = True
            for j in range(needle_len):
                # Only check where mask is non-zero
                if mask[j] != 0 and (rom_data[i + j] & mask[j]) != (needle[j] & mask[j]):
                    match = False
                    break
            if match:
                return i
        return None
    except Exception as e:
        print(f"Search error: {e}")
        return None

def safe_read(data: bytes, offset: int, length: int = 1) -> bytes:
    """Safely read data from a buffer with bounds checking."""
    try:
        if offset < 0 or offset + length > len(data):
            return bytes([0] * length)
        return data[offset:offset+length]
    except:
        return bytes([0] * length)

def calc_physical_address(segment: int, offset: int) -> Tuple[int, int]:
    """Calculate physical address from segment and offset"""
    physical_addr = (segment * SEGMENT_SIZE) + offset
    rom_offset = physical_addr & ~ROM_1MB_MASK
    return physical_addr, rom_offset

def is_valid_table_address(addr: int, rom_size: int) -> bool:
    """Check if a table address is valid within the ROM"""
    return 0 <= addr < rom_size

def show_entry_def(entry: Dict, nwidth: int) -> None:
    """Display entry definition information"""
    if nwidth == 0:
        return
    
    print(f"\n    {entry['field_name']}:")
    print(f"      Unit:                    {entry['desc']}")
    print(f"      Conversion name:         {entry.get('conv_name', '')}")
    
    conv_op = entry.get('otype', '/')
    conv_value = float(entry['conv'])
    conv_formula = f"f(phys) = 0.0 + {conv_value:.6f} * phys"
    if conv_op == '*':
        conv_formula = f"f(phys) = 0.0 + {conv_value:.6f} * phys"
    elif conv_op == 'x':
        conv2 = entry.get('conv2')
        if conv2:
            conv_formula = f"f(phys) = 0.0 + {conv_value:.6f} * phys - {float(conv2):.6f}"
        else:
            conv_formula = f"f(phys) = 0.0 + {conv_value:.6f} * phys"
    elif conv_op == 'd':
        conv2 = entry.get('conv2')
        if conv2:
            conv_formula = f"f(phys) = 0.0 + phys / {conv_value:.6f} - {float(conv2):.6f}"
        else:
            conv_formula = f"f(phys) = 0.0 + phys / {conv_value:.6f}"
    else:  # Default is '/'
        conv_formula = f"f(phys) = 0.0 + phys / {conv_value:.6f}"
    
    print(f"      Conversion formula:      {conv_formula}")
    
    data_type = "UNKNOWN"
    if nwidth == 1:
        data_type = "UBYTE"
    elif nwidth == 2:
        data_type = "UWORD"
    elif nwidth > 2:
        data_type = f"{nwidth} BYTES"
    
    print(f"      Data type:               {data_type}")

def dump_table(rom_data: bytes, table_addr: int, segment: int, table_def: TableDef, 
               cell_table_override_adr: int = 0) -> None:
    """Dump table information based on the address found."""
    try:
        # Calculate physical address
        rom_adr, map_table_adr = calc_physical_address(segment, table_addr)
        
        # Ensure map_table_adr is within bounds
        if not is_valid_table_address(map_table_adr, len(rom_data)):
            print(f"Warning: Table address 0x{map_table_adr:x} out of range")
            return

        # Get table start address
        table_start = map_table_adr
        
        # Use provided cell table address if available
        table_start2 = 0
        if cell_table_override_adr != 0:
            _, table_start2 = calc_physical_address(0, cell_table_override_adr & ~ROM_1MB_MASK)
            if not is_valid_table_address(table_start2, len(rom_data)):
                print(f"Warning: Cell table address 0x{table_start2:x} out of range")
                table_start2 = 0

        # Extract table structure information
        table_data_offset = 0
        x_num_data_start = table_start + table_data_offset
        
        # Validate address before reading
        if not is_valid_table_address(x_num_data_start, len(rom_data)):
            print(f"Warning: X-num address 0x{x_num_data_start:x} out of range")
            return
            
        table_data_offset += table_def.x_num_nwidth
        x_num = get_nwidth(rom_data, x_num_data_start, table_def.x_num_nwidth)
        
        # Validate x_num is reasonable
        if x_num > 50:  # Cap to prevent unreasonable values
            x_num = 20

        # Get y_num information
        y_num_data_start = table_start + table_data_offset
        if not is_valid_table_address(y_num_data_start, len(rom_data)):
            print(f"Warning: Y-num address 0x{y_num_data_start:x} out of range")
            return
            
        table_data_offset += table_def.y_num_nwidth
        y_num = get_nwidth(rom_data, y_num_data_start, table_def.y_num_nwidth)
        
        # Validate y_num is reasonable
        if y_num > 50:
            y_num = 20

        # Get x-axis data
        x_axis_header_data_start = table_start + table_data_offset
        if x_num > 0 and not is_valid_table_address(x_axis_header_data_start + (x_num * table_def.x_axis_nwidth) - 1, len(rom_data)):
            print(f"Warning: X-axis data extends beyond file boundary")
            return
            
        table_data_offset += (x_num * table_def.x_axis_nwidth)

        # Get y-axis data
        y_axis_header_data_start = table_start + table_data_offset
        if y_num > 0 and not is_valid_table_address(y_axis_header_data_start + (y_num * table_def.y_axis_nwidth) - 1, len(rom_data)):
            print(f"Warning: Y-axis data extends beyond file boundary")
            return
            
        table_data_offset += (y_num * table_def.y_axis_nwidth)

        # Get cell data
        cell_data_start = table_start + table_data_offset if cell_table_override_adr == 0 else table_start2
        
        # Verify cell data is accessible
        cell_data_size = x_num * y_num * table_def.cell_nwidth if y_num > 0 else x_num * table_def.cell_nwidth
        if not is_valid_table_address(cell_data_start + cell_data_size - 1, len(rom_data)):
            print(f"Warning: Cell data address 0x{cell_data_start:x} extends beyond file boundary")
            # Continue anyway to show what data we can

        # Print table header
        print("\n" + table_def.table_name)
        print(f"    Long identifier:           {table_def.table_desc}")
        print(f"    Display identifier:         ")
        print(f"    Address:                   0x{rom_adr:x}")
        print(f"    Value:\n")

        # Print X-axis headers
        print(" No.           | ", end="")
        for i in range(x_num):
            print(f"    {i:4d} ", end="")
        print()

        # Common conversion function with operation type handling
        def convert_value(raw_value, conv_info):
            conv_value = float(conv_info['conv'])
            operation = conv_info.get('otype', '/')
            conv2 = conv_info.get('conv2')
            
            if operation == '*':
                result = raw_value * conv_value
            elif operation == 'x':
                result = raw_value * conv_value
                if conv2:
                    result -= float(conv2)
            elif operation == 'd':
                result = raw_value / conv_value
                if conv2:
                    result -= float(conv2)
            else:  # Default is '/'
                result = raw_value / conv_value
                
            return result

        # Print X-axis values in physical format
        if show_phy:
            print("            PHY| ", end="")
            for i in range(x_num):
                try:
                    offset = x_axis_header_data_start + (i * table_def.x_axis_nwidth)
                    entry = get_nwidth(rom_data, offset, table_def.x_axis_nwidth)
                    formatted_value = convert_value(entry, table_def.x_axis)
                    print(f"{formatted_value:8.2f} ", end="")
                except Exception as e:
                    print("   ???  ", end="")
            print()

        # Print X-axis values in hex format
        if show_hex:
            print("            HEX| ", end="")
            for i in range(x_num):
                try:
                    offset = x_axis_header_data_start + (i * table_def.x_axis_nwidth)
                    entry = get_nwidth(rom_data, offset, table_def.x_axis_nwidth)
                    print(f"0x{entry:X} ", end="")
                except Exception:
                    print("   ???  ", end="")
            print()

        # Print X-axis addresses
        if show_adr:
            print("            ADR| ", end="")
            for i in range(x_num):
                addr = x_axis_header_data_start + (i * table_def.x_axis_nwidth)
                print(f"0x{addr + seg_start:X} ", end="")
            print()

        # Separator line
        print(" --------------+", end="")
        for i in range(x_num):
            print("---------", end="")
        print()

        # For 1D tables (y_num = 0), print just one row
        if y_num == 0:
            if show_phy:
                print("            PHY| ", end="")
                for i in range(x_num):
                    try:
                        # For 1D tables, the cell data often follows the x_axis data
                        offset = cell_data_start + (i * table_def.cell_nwidth)
                        if is_valid_table_address(offset, len(rom_data)):
                            entry = get_nwidth(rom_data, offset, table_def.cell_nwidth)
                            formatted_value = convert_value(entry, table_def.cell)
                            print(f"{formatted_value:8.0f} ", end="")
                        else:
                            print("   ???  ", end="")
                    except Exception as e:
                        print("   ???  ", end="")
                print()
                
            if show_hex:
                print("            HEX| ", end="")
                for i in range(x_num):
                    try:
                        offset = cell_data_start + (i * table_def.cell_nwidth)
                        if is_valid_table_address(offset, len(rom_data)):
                            entry = get_nwidth(rom_data, offset, table_def.cell_nwidth)
                            print(f"  {entry:#6x} ", end="")
                        else:
                            print("   ???  ", end="")
                    except Exception:
                        print("   ???  ", end="")
                print()
                
            if show_adr:
                print("            ADR| ", end="")
                for i in range(x_num):
                    addr = cell_data_start + (i * table_def.cell_nwidth)
                    if is_valid_table_address(addr, len(rom_data)):
                        print(f"0x{addr + seg_start:X} ", end="")
                    else:
                        print("   ???  ", end="")
                print()
        # For 2D tables, print each row
        else:
            for y_pos in range(y_num):
                try:
                    # Get y-axis header data
                    y_axis_adr = y_axis_header_data_start + (y_pos * table_def.y_axis_nwidth)
                    if not is_valid_table_address(y_axis_adr, len(rom_data)):
                        continue
                        
                    y_axis_value_raw = get_nwidth(rom_data, y_axis_adr, table_def.y_axis_nwidth)
                    y_axis_value_fmt = convert_value(y_axis_value_raw, table_def.y_axis)

                    # Print Y-axis value and row for physical values
                    if show_phy:
                        print(f" {y_axis_value_fmt:5.0f}     PHY| ", end="")
                        for x_pos in range(x_num):
                            try:
                                # Get cell data
                                cell_adr = cell_data_start + (x_pos * (y_num * table_def.cell_nwidth)) + (y_pos * table_def.cell_nwidth)
                                if is_valid_table_address(cell_adr, len(rom_data)):
                                    entry = get_nwidth(rom_data, cell_adr, table_def.cell_nwidth)
                                    formatted_value = convert_value(entry, table_def.cell)
                                    print(f"{formatted_value:8.0f} ", end="")
                                else:
                                    print("   ???  ", end="")
                            except Exception:
                                print("   ???  ", end="")
                        print()
                    
                    # Print row for hex values
                    if show_hex:
                        print(f"  {y_axis_value_raw:#8.4x} HEX| ", end="")
                        for x_pos in range(x_num):
                            try:
                                # Get cell data
                                cell_adr = cell_data_start + (x_pos * (y_num * table_def.cell_nwidth)) + (y_pos * table_def.cell_nwidth)
                                if is_valid_table_address(cell_adr, len(rom_data)):
                                    entry = get_nwidth(rom_data, cell_adr, table_def.cell_nwidth)
                                    print(f"  {entry:#6x} ", end="")
                                else:
                                    print("   ???  ", end="")
                            except Exception:
                                print("   ???  ", end="")
                        print()
                    
                    # Print row for addresses
                    if show_adr:
                        print(f"  {y_axis_adr + seg_start:#9.5x} ADR| ", end="")
                        for x_pos in range(x_num):
                            try:
                                # Get cell address
                                cell_adr = cell_data_start + (x_pos * (y_num * table_def.cell_nwidth)) + (y_pos * table_def.cell_nwidth)
                                if is_valid_table_address(cell_adr, len(rom_data)):
                                    print(f"0x{cell_adr + seg_start:X} ", end="")
                                else:
                                    print("   ???  ", end="")
                            except Exception:
                                print("   ???  ", end="")
                        print()
                except Exception as e:
                    print(f"Error processing row {y_pos}: {e}")

        # Print footer information
        print("\n\n")
        show_entry_def(table_def.cell, table_def.cell_nwidth)
        show_entry_def(table_def.x_axis, table_def.x_axis_nwidth)
        show_entry_def(table_def.y_axis, table_def.y_axis_nwidth)
        print("\n")
        
    except Exception as e:
        print(f"Error dumping table: {e}")

def find_multi_map_type1(rom_data: bytes) -> None:
    """Find and display 2D maps in the ROM (Type 1)."""
    current_offset = 0
    map_count = 0
    
    try:
        while True:
            # Search for the next occurrence of the pattern
            current_offset = search(rom_data, mapfinder_xy2_needle, mapfinder_xy2_mask, current_offset)
            if current_offset is None:
                break
                
            map_count += 1
            print(f"\n------------------------------------------------------------------")
            print(f"[Map #{map_count}] Multi Axis Map Type #1 function found at: offset=0x{current_offset:x} \n")
            
            # Extract the table address from the found pattern
            if current_offset + 34 < len(rom_data):
                # Extract table information
                table_adr = get16(rom_data, current_offset + 2)   # Table data from first mov instruction
                segment = get16(rom_data, current_offset + 6)     # Segment from second mov instruction
                
                # Dump the table
                dump_table(rom_data, table_adr, segment, XXXX_table, 0)
            
            # Continue searching from the next position
            current_offset += len(mapfinder_xy2_needle)
    except Exception as e:
        print(f"Error in find_multi_map_type1: {e}")

def find_multi_map_type2(rom_data: bytes) -> None:
    """Find and display 1D maps in the ROM (Type 2)."""
    current_offset = 0
    new_offset = 0
    map_count = 0
    
    # Search for all occurrences
    try:
        while map_count < MAX_TABLE_SEARCHES:
            # Search for the next pattern occurrence
            found_offset = search(rom_data, mapfinder_xy3_needle, mapfinder_xy3_mask, current_offset + new_offset)
            if found_offset is None:
                break
                
            map_count += 1
            addr = found_offset
            
            print(f"\n------------------------------------------------------------------")
            print(f"[Map #{map_count}] Multi Map Type #2 lookup function found @ offset: 0x{addr:x} \n")
            
            # Backtrack to try to find the start of the function
            backtrack_pos = addr
            backtrack_count = 0
            try:
                while backtrack_count < MAX_SEARCH_BACK_BYTES:
                    backtrack_count += 1
                    if backtrack_pos <= 0:
                        break
                        
                    if backtrack_pos + 1 < len(rom_data) and rom_data[backtrack_pos] == 0xDB and rom_data[backtrack_pos+1] == 0x00:  # 'rets' instruction
                        backtrack_count += 1
                        print(f"Found estimated function start address: 0x{backtrack_pos:x}")
                        break
                        
                    backtrack_pos -= 1
            except Exception as e:
                print(f"Backtrack error: {e}")
                
            print(f"Backtrack offset: 0x{addr:x} ({backtrack_count} bytes)\n")
            
            # Extract the table structure from the pattern
            try:
                if addr + 26 < len(rom_data):
                    # Extract table information from the instruction pattern
                    x_num_start_addr = get16(rom_data, addr + 4)     # r12 value (X-NUM address)
                    segment_offset = get16(rom_data, addr + 8)       # r13 value (segment)
                    y_axis_addr = get16(rom_data, addr + 14)         # r14 value (Y-AXIS address)
                    cell_table_addr = get16(rom_data, addr + 22)     # r15 value (cell data address)
                    
                    # Compute physical addresses
                    phys_x_addr, rom_x_addr = calc_physical_address(dpp1_value, x_num_start_addr)
                    x_axis_start_addr = x_num_start_addr + 1         # X-axis starts after x_num
                    
                    phys_y_addr, rom_y_addr = calc_physical_address(dpp1_value, y_axis_addr)
                    y_num_start_addr = y_axis_addr                   # Y-axis address is the same as y_num for these tables
                    y_axis_start_addr = y_num_start_addr 
                    
                    print(f"X_NUM  start address: {x_num_start_addr:08X}")
                    print(f"X_AXIS start address: {x_axis_start_addr:08X}")
                    print(f"Y_NUM  start address: {y_num_start_addr:08X}")
                    print(f"Y_AXIS start address: {y_axis_start_addr:08X}")
                    print(f"Overriding cell_data start address to {cell_table_addr:08X}")
                    
                    # Dump the table
                    dump_table(rom_data, x_num_start_addr, dpp1_value, XXXXB_table, cell_table_addr)
            except Exception as e:
                print(f"Error extracting table structure: {e}")
            
            # Continue from the next position
            new_offset += found_offset + len(mapfinder_xy3_needle) - current_offset
    except Exception as e:
        print(f"Error in find_multi_map_type2: {e}")

def find_1d_maps(rom_data: bytes) -> None:
    """Find and display 1D simple maps in the ROM."""
    current_offset = 0
    map_count = 0
    
    print("-[ Generic X-Axis MAP Table Scanner! ]---------------------------------------------------------------------\n")
    print(">>> Scanning for Map Tables #1 Checking sub-routine [map finder!] \n")
    
    try:
        while map_count < MAX_TABLE_SEARCHES:
            # Search for the pattern
            current_offset = search(rom_data, mapfinder_needle, mapfinder_mask, current_offset)
            if current_offset is None:
                break
                
            addr = current_offset
            map_count += 1
            
            # Check if we have enough data to extract map information
            if addr + 10 >= len(rom_data):
                current_offset += len(mapfinder_needle)
                continue
            
            # Extract the map information
            try:
                val = get16(rom_data, addr + 2)         # Table offset from r12 instruction
                seg = get16(rom_data, addr + 6)         # Segment from r13 instruction
                
                # Calculate physical address
                phys_addr, map_adr = calc_physical_address(seg, val)
                
                # Ensure map_adr is within range of rom_data
                if not is_valid_table_address(map_adr, len(rom_data)) or not is_valid_table_address(map_adr + 1, len(rom_data)):
                    print(f"[Map #{map_count}] 1D X-Axis  : Map function found at: offset=0x{addr:x} phy:0x{map_adr:x}, file-offset=0x{map_adr:x} x-axis=Invalid map address: 0x{map_adr:x}")
                    current_offset += len(mapfinder_needle)
                    continue
                
                x_axis = rom_data[map_adr]              # Number of entries
                table_start = map_adr + 1               # Skip first byte which is the count
                
                # Ensure x_axis is reasonable
                if x_axis > 50 or x_axis == 0:  # Cap to prevent unreasonable values
                    print(f"[Map #{map_count}] 1D X-Axis  : Map function found at: offset=0x{addr:x} phy:0x{phys_addr:x}, file-offset=0x{map_adr:x} x-axis=Invalid count: {x_axis}")
                    current_offset += len(mapfinder_needle)
                    continue
                    
                # Ensure we have enough data to read the entire table
                if not is_valid_table_address(table_start + x_axis - 1, len(rom_data)):
                    print(f"[Map #{map_count}] 1D X-Axis  : Map function found at: offset=0x{addr:x} phy:0x{phys_addr:x}, file-offset=0x{map_adr:x} x-axis=Table extends beyond file boundary")
                    current_offset += len(mapfinder_needle)
                    continue
                
                print(f"[Map #{map_count}] 1D X-Axis  : Map function found at: offset=0x{addr:x} phy:0x{phys_addr:x}, file-offset=0x{table_start:x} x-axis={x_axis}")
                
                # Display table values
                print("\t", end="")
                for x in range(x_axis):
                    if is_valid_table_address(table_start + x, len(rom_data)):
                        print(f"{rom_data[table_start + x]:02x} ", end="")
                print()
            except Exception as e:
                print(f"Error processing map #{map_count}: {e}")
            
            # Continue from the next position
            current_offset += len(mapfinder_needle)
        
        print("\n")
    except Exception as e:
        print(f"Error in find_1d_maps: {e}")

def check_dppx(rom_data: bytes) -> None:
    """Find and extract DPP0-DPP3 values from the ROM."""
    global dpp1_value
    
    print("-[ DPPx Setup Analysis ]-----------------------------------------------------------------\n")
    print(">>> Scanning for Main ROM DPPx setup #1 [to extract dpp0, dpp1, dpp2, dpp3 from rom] \n")
    
    # DPP needle pattern
    dpp_needle = bytearray([
        0xE6, 0x00, XXXX, XXXX,   # mov     DPP0, #XXXXh
        0xE6, 0x01, XXXX, XXXX,   # mov     DPP1, #XXXXh
        0xE6, 0x02, XXXX, XXXX,   # mov     DPP2, #XXXXh 
        0xE6, 0x03, XXXX, XXXX    # mov     DPP3, #XXXX
    ])
    
    dpp_mask = bytearray([
        MASK, MASK, XXXX, XXXX,   # mov     DPP0, #XXXXh
        MASK, MASK, XXXX, XXXX,   # mov     DPP1, #XXXXh
        MASK, MASK, XXXX, XXXX,   # mov     DPP2, #XXXXh 
        MASK, MASK, XXXX, XXXX    # mov     DPP3, #XXXX
    ])
    
    addr = search(rom_data, dpp_needle, dpp_mask, 0)
    
    if addr is None:
        print("\nmain rom dppX byte sequence #1 not found\nProbably not an ME7.x firmware file!\n")
        sys.exit(1)
    else:
        print(f"\nmain rom dppX byte sequence #1 found at offset=0x{addr:x}.\n")
        
        # Extract DPP values
        dpp0 = get16(rom_data, addr + 2)
        dpp1 = get16(rom_data, addr + 6)
        dpp2 = get16(rom_data, addr + 10)
        dpp3 = get16(rom_data, addr + 14)
        
        # Store dpp1_value for segment calculations
        dpp1_value = dpp1
        
        # Display DPP values
        print(f"dpp0: (seg: 0x{dpp0:04x} phy:0x{dpp0 * SEGMENT_SIZE:08x})")
        print(f"dpp1: (seg: 0x{dpp1:04x} phy:0x{dpp1 * SEGMENT_SIZE:08x})")
        print(f"dpp2: (seg: 0x{dpp2:04x} phy:0x{dpp2 * SEGMENT_SIZE:08x}) ram start address")
        print(f"dpp3: (seg: 0x{dpp3:04x} phy:0x{dpp3 * SEGMENT_SIZE:08x}) cpu registers")
        print("\nNote: dpp3 is always 3, otherwise accessing CPU register area not possible\n")

def check_basic_info(rom_data: bytes) -> None:
    """Show basic firmware information."""
    print("-[ Basic Firmware information ]-----------------------------------------------------------------\n")
    
    # This is a placeholder - in a real implementation, we would search for and display
    # firmware version and other ECU info from the ROM
    print(">>> Basic firmware information not implemented in this version\n")

def check_multimap(rom_data: bytes) -> None:
    """Main function to find and display maps in the ROM."""
    try:
        # Find 1D maps
        find_1d_maps(rom_data)
        
        # Find 2D maps (Type 1)
        find_multi_map_type1(rom_data)
        
        # Find 1D maps with a different structure (Type 2)
        find_multi_map_type2(rom_data)
    except Exception as e:
        print(f"Error in check_multimap: {e}")

def main():
    parser = argparse.ArgumentParser(description='ME7.x ECU ROM Map Table Scanner')
    parser.add_argument('romfile', help='ROM file to analyze')
    parser.add_argument('--skip', action='store_true', help='Skip basic checks and go directly to map scanner')
    parser.add_argument('--no-phy', action='store_true', help='Do not show physical values')
    parser.add_argument('--no-hex', action='store_true', help='Do not show hex values')
    parser.add_argument('--no-adr', action='store_true', help='Do not show addresses')
    parser.add_argument('--diss', action='store_true', help='Show disassembly when available')
    args = parser.parse_args()
    
    # Set global display options
    global show_phy, show_hex, show_adr, show_diss
    show_phy = not args.no_phy
    show_hex = not args.no_hex
    show_adr = not args.no_adr
    show_diss = args.diss
    
    print(f"ME7.x ROM Map Table Scanner")
    print(f"Opening '{args.romfile}' file")
    
    try:
        with open(args.romfile, 'rb') as f:
            rom_data = f.read()
        
        print(f"Succeded loading file.")
        print(f"Loaded ROM: Tool in 1Mb Mode\n")
        
        # Extract DPP values first as we need them for address calculations
        if not args.skip:
            check_dppx(rom_data)
            check_basic_info(rom_data)
        
        # Run the map scanner
        check_multimap(rom_data)
            
    except FileNotFoundError:
        print(f"Error: ROM file '{args.romfile}' not found")
    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    main()