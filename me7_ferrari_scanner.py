#!/usr/bin/env python3
"""
Advanced ME7 Ferrari ROM Scanner
-------------------------------
A Python command-line tool for extracting and displaying maps, tables, and ECU information
from Ferrari ME7 ECU ROM files based on the ME7RomTool_Ferrari repository.

This advanced version uses alternative approaches to find maps and tables:
1. Direct address scanning for known map/table locations
2. Binary signature detection with more flexible pattern matching
3. Structure-based analysis of the ROM file

Usage: python me7_ferrari_advanced_scanner.py rom_file.fls [--output results.json] [--verbose]
"""

import argparse
import json
import os
import re
import struct
import sys
import binascii
from typing import Dict, List, Tuple, Optional, Union, Any

# Define color codes for terminal output (with fallback for Windows)
try:
    import colorama
    colorama.init()
    class Colors:
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
except ImportError:
    class Colors:
        HEADER = ''
        BLUE = ''
        GREEN = ''
        YELLOW = ''
        RED = ''
        ENDC = ''
        BOLD = ''
        UNDERLINE = ''

# Define known map and table addresses based on ME7RomTool_Ferrari output
# These are common addresses in Ferrari ME7 ECUs (F430, 360, etc.)
KNOWN_MAPS_TABLES = [
    {
        "name": "KFMIOP",
        "description": "Main Fuel Injection Map",
        "address": 0x36A00,  # Example address, will need adjustment
        "mapType": "3D",
        "dimensions": [16, 16],
        "valueType": "uint16",
        "factor": 0.0078125,
        "units": "ms"
    },
    {
        "name": "KFZWOP",
        "description": "Ignition Timing Map",
        "address": 0x35800,  # Example address, will need adjustment
        "mapType": "3D",
        "dimensions": [16, 16],
        "valueType": "int16",
        "factor": 0.75,
        "units": "°"
    },
    {
        "name": "KFMIRL",
        "description": "Torque Limiter Map",
        "address": 0x36400,  # Example address, will need adjustment
        "mapType": "3D",
        "dimensions": [16, 12],
        "valueType": "uint16",
        "factor": 0.023438,
        "units": "Nm"
    },
    {
        "name": "KFLDRL",
        "description": "Lambda Control Table",
        "address": 0x42A00,  # Example address, will need adjustment
        "mapType": "2D",
        "dimensions": [16],
        "valueType": "uint16",
        "factor": 0.0078125,
        "units": "Lambda"
    },
    {
        "name": "MLHFM",
        "description": "MAF Sensor Transfer Function",
        "address": 0x38000,  # Example address, will need adjustment
        "mapType": "2D",
        "dimensions": [32],
        "valueType": "float32",
        "factor": 1.0,
        "units": "kg/h"
    }
]

# Address ranges to scan for potential maps/tables
# These are common regions in ME7 ECUs where maps and tables are stored
ADDRESS_RANGES = [
    (0x30000, 0x40000),  # Common map/table area 1
    (0x40000, 0x50000),  # Common map/table area 2
    (0x10000, 0x20000)   # Common calibration data area
]

# Common byte patterns that indicate the start of maps/tables
# These are signature patterns often found at the beginning of data structures
MAP_SIGNATURES = [
    # 3D map signatures (usually 16x16 or similar dimensions)
    {
        "pattern": b"\x10\x00\x10\x00",  # 16 x 16 dimension header (uint16 format)
        "description": "16x16 map header",
        "map_type": "3D",
        "dimensions": [16, 16]
    },
    {
        "pattern": b"\x10\x00\x0C\x00",  # 16 x 12 dimension header
        "description": "16x12 map header",
        "map_type": "3D",
        "dimensions": [16, 12]
    },
    {
        "pattern": b"\x08\x00\x08\x00",  # 8 x 8 dimension header
        "description": "8x8 map header",
        "map_type": "3D",
        "dimensions": [8, 8]
    },
    # 2D table signatures (usually just a dimension and data)
    {
        "pattern": b"\x10\x00\x00\x00",  # 16-element table header
        "description": "16-element table header",
        "map_type": "2D",
        "dimensions": [16]
    },
    {
        "pattern": b"\x20\x00\x00\x00",  # 32-element table header
        "description": "32-element table header",
        "map_type": "2D",
        "dimensions": [32]
    }
]

# Data type definitions
DATA_TYPES = {
    "uint8": {"size": 1, "format": "B", "signed": False},
    "int8": {"size": 1, "format": "b", "signed": True},
    "uint16": {"size": 2, "format": "H", "signed": False},
    "int16": {"size": 2, "format": "h", "signed": True},
    "uint32": {"size": 4, "format": "I", "signed": False},
    "int32": {"size": 4, "format": "i", "signed": True},
    "float32": {"size": 4, "format": "f", "signed": True}
}


class ME7RomAdvancedScanner:
    """Advanced scanner for ME7 ROM files to find maps and tables"""
    
    def __init__(self, rom_file=None, verbose=False):
        """Initialize the scanner with optional ROM file"""
        self.rom_data = None
        self.rom_size = 0
        self.verbose = verbose
        self.dpp_info = None
        self.epk_info = None
        self.maps_tables = []
        
        if rom_file:
            self.load_rom(rom_file)
    
    def load_rom(self, rom_file):
        """Load a ROM file into memory"""
        try:
            with open(rom_file, "rb") as f:
                self.rom_data = f.read()
                self.rom_size = len(self.rom_data)
            
            print(f"Loaded ROM file: {rom_file} ({self.rom_size:,} bytes)")
            
            # Determine ROM mode based on size
            if self.rom_size == 1048576:  # 1MB
                print("Loaded ROM: Tool in 1Mb Mode")
            elif self.rom_size == 2097152:  # 2MB
                print("Loaded ROM: Tool in 2Mb Mode")
            else:
                print(f"Unknown ROM size: {self.rom_size} bytes")
            
            return True
        except Exception as e:
            print(f"Error loading ROM file: {e}")
            return False
    
    def extract_data(self, address, data_type, count=1):
        """Extract data from ROM at the specified address"""
        if not self.rom_data:
            print("No ROM data loaded")
            return []
        
        type_info = DATA_TYPES.get(data_type)
        if not type_info:
            print(f"Unknown data type: {data_type}")
            return []
        
        size = type_info["size"]
        fmt = type_info["format"]
        
        values = []
        for i in range(count):
            pos = address + i * size
            if pos + size > len(self.rom_data):
                break
            
            try:
                value = struct.unpack("<" + fmt, self.rom_data[pos:pos+size])[0]
                values.append(value)
            except struct.error:
                print(f"Error unpacking data at address 0x{pos:X}")
                break
        
        return values
    
    def extract_string(self, address, max_length=128):
        """Extract a null-terminated string from the ROM"""
        if not self.rom_data:
            return ""
        
        # Extract bytes until we hit a null terminator or max length
        string_bytes = bytearray()
        for i in range(max_length):
            if address + i >= len(self.rom_data):
                break
            
            byte = self.rom_data[address + i]
            if byte == 0:
                break
            
            string_bytes.append(byte)
        
        # Try to decode as ASCII, fallback to latin-1 if needed
        try:
            return string_bytes.decode('ascii')
        except UnicodeDecodeError:
            return string_bytes.decode('latin-1')
    
    def scan_for_epk(self):
        """Scan for EPK information in ROM"""
        print(">>> Scanning for EPK information")
        
        # Look for typical EPK format: "/1/F136E/..."
        epk_prefix = b"/1/F"
        for i in range(0, len(self.rom_data) - 4):
            if self.rom_data[i:i+4] == epk_prefix:
                # Found a potential EPK string
                string = self.extract_string(i, 50)
                if "/" in string[4:] and string.count("/") >= 5:  # EPK has multiple / characters
                    epk_addr = i
                    epk_value = string
                    print(f"EPK: @ 0x{epk_addr:x} {{ {epk_value} }}")
                    
                    self.epk_info = {
                        "address": epk_addr,
                        "value": epk_value
                    }
                    return True
        
        print("EPK information not found")
        return False
    
    def find_maps_by_signature(self):
        """Find maps and tables by scanning for known binary signatures"""
        print(">>> Scanning for maps/tables by signature")
        
        maps_found = []
        
        # Check each address range for map signatures
        for start_addr, end_addr in ADDRESS_RANGES:
            if self.verbose:
                print(f"Scanning address range: 0x{start_addr:X} - 0x{end_addr:X}")
            
            for i in range(start_addr, min(end_addr, len(self.rom_data) - 8)):
                # Check each signature pattern
                for sig in MAP_SIGNATURES:
                    pattern = sig["pattern"]
                    pattern_len = len(pattern)
                    
                    if i + pattern_len > len(self.rom_data):
                        continue
                    
                    if self.rom_data[i:i+pattern_len] == pattern:
                        # Found a potential map/table
                        map_type = sig["map_type"]
                        dimensions = sig["dimensions"]
                        
                        # Try to determine the data type by analyzing the data
                        # For simplicity, we'll default to uint16 for most maps
                        value_type = "uint16"
                        
                        # Look at the data to determine if it might be signed
                        data_start = i + pattern_len
                        sample_data = self.rom_data[data_start:data_start+16]
                        if any(b > 0x80 for b in sample_data):
                            value_type = "int16"  # Might be signed
                        
                        # Create a map/table entry
                        map_entry = {
                            "name": f"MAP_{i:X}",  # Generate a name based on address
                            "description": f"Auto-detected {sig['description']}",
                            "address": i,
                            "type": map_type,
                            "dimensions": dimensions,
                            "valueType": value_type,
                            "factor": 1.0,  # Default scaling factor
                            "units": ""
                        }
                        
                        # Extract the data
                        extracted = self.extract_map_table(map_entry)
                        if extracted:
                            # Try to identify the map based on data characteristics
                            identified = self.identify_map(extracted)
                            if identified:
                                maps_found.append(identified)
                                print(f"Found {identified['name']} @ 0x{i:X} - {identified['description']}")
                            else:
                                maps_found.append(extracted)
                                print(f"Found unnamed map/table @ 0x{i:X} - {sig['description']}")
        
        return maps_found
    
    def scan_known_addresses(self):
        """Scan for maps/tables at known addresses"""
        print(">>> Scanning for maps/tables at known addresses")
        
        maps_found = []
        
        # Try each known map/table
        for map_def in KNOWN_MAPS_TABLES:
            # Check 10 addresses around the expected one
            # (to account for differences between ROM versions)
            base_addr = map_def["address"]
            found = False
            
            # Try addresses around the expected one (±512 bytes)
            for offset in range(-512, 513, 16):
                addr = base_addr + offset
                if addr < 0 or addr >= len(self.rom_data) - 8:
                    continue
                
                # Create a copy of the map definition with updated address
                map_entry = map_def.copy()
                map_entry["address"] = addr
                
                # Extract the data
                extracted = self.extract_map_table(map_entry)
                if extracted and self.is_valid_map(extracted):
                    maps_found.append(extracted)
                    print(f"Found {extracted['name']} @ 0x{addr:X} - {extracted['description']}")
                    found = True
                    break
            
            if not found and self.verbose:
                print(f"  Could not find {map_def['name']} near address 0x{base_addr:X}")
        
        return maps_found
    
    def extract_map_table(self, map_def):
        """Extract a map or table based on its definition"""
        addr = map_def["address"]
        map_type = map_def["type"] if "type" in map_def else map_def.get("mapType", "2D")
        dimensions = map_def["dimensions"]
        value_type = map_def["valueType"]
        factor = map_def.get("factor", 1.0)
        units = map_def.get("units", "")
        
        result = {
            "name": map_def["name"],
            "address": addr,
            "description": map_def.get("description", ""),
            "type": map_type,
            "dimensions": dimensions,
            "valueType": value_type,
            "factor": factor,
            "units": units
        }
        
        # Extract data based on map type
        if map_type == "3D" and len(dimensions) == 2:
            # 3D map (2D matrix)
            x_size, y_size = dimensions
            data = []
            
            # Calculate the total size needed for the data
            type_size = DATA_TYPES[value_type]["size"]
            total_cells = x_size * y_size
            total_size = total_cells * type_size
            
            # Check if we have enough data in the ROM
            if addr + total_size > len(self.rom_data):
                if self.verbose:
                    print(f"Warning: Map data for {map_def['name']} extends beyond ROM boundary")
                return None
            
            # Extract each row
            for y in range(y_size):
                row = []
                for x in range(x_size):
                    idx = y * x_size + x
                    cell_addr = addr + idx * type_size
                    raw_value = self.extract_data(cell_addr, value_type)[0]
                    # Apply scaling factor
                    value = raw_value * factor
                    row.append(value)
                data.append(row)
            
            result["data"] = data
            
        elif map_type == "2D" or len(dimensions) == 1:
            # 2D table (1D array)
            size = dimensions[0]
            
            # Calculate the total size needed for the data
            type_size = DATA_TYPES[value_type]["size"]
            total_size = size * type_size
            
            # Check if we have enough data in the ROM
            if addr + total_size > len(self.rom_data):
                if self.verbose:
                    print(f"Warning: Table data for {map_def['name']} extends beyond ROM boundary")
                return None
            
            # Extract all values
            raw_values = self.extract_data(addr, value_type, size)
            # Apply scaling factor
            values = [v * factor for v in raw_values]
            
            result["data"] = values
        
        return result
    
    def is_valid_map(self, map_data):
        """Check if extracted data looks like a valid map/table"""
        if "data" not in map_data:
            return False
            
        data = map_data["data"]
        
        # Empty data
        if not data or (isinstance(data, list) and len(data) == 0):
            return False
            
        # For 3D maps (2D matrix)
        if map_data["type"] == "3D":
            # Check that all rows have the same length
            row_lengths = [len(row) for row in data]
            if len(set(row_lengths)) != 1:
                return False
                
            # Check for reasonable values
            flat_data = [val for row in data for val in row]
            return self.has_reasonable_values(flat_data)
        else:
            # For 2D tables (1D array)
            return self.has_reasonable_values(data)
    
    def has_reasonable_values(self, values):
        """Check if values are within reasonable ranges for maps/tables"""
        if not values:
            return False
            
        # Filter out NaN and infinity
        values = [v for v in values if not (float('nan') == v or float('inf') == v or float('-inf') == v)]
        if not values:
            return False
            
        # Check for non-zero variance
        # If all values are identical, it's probably not a real map/table
        if max(values) == min(values):
            return False
            
        # Check if values are in reasonable ranges for engine maps
        # This depends on what the map represents
        # For a general check, ensure values aren't all zeros or all very large
        if all(v == 0 for v in values):
            return False
            
        if all(abs(v) > 10000 for v in values):
            return False
            
        return True
    
    def identify_map(self, map_data):
        """Try to identify a map based on its characteristics"""
        # This is a simplified version - real implementation would be more sophisticated
        if "data" not in map_data:
            return map_data
            
        data = map_data["data"]
        addr = map_data["address"]
        dimensions = map_data["dimensions"]
        
        # Clone the map data
        identified = map_data.copy()
        
        # Check map characteristics
        if map_data["type"] == "3D" and dimensions == [16, 16]:
            # Check for fuel injection map (typically 16x16 with values 0-10ms)
            if all(0 <= val <= 10 for row in data for val in row):
                identified["name"] = "KFMIOP"
                identified["description"] = "Main Fuel Injection Map"
                identified["factor"] = 0.0078125
                identified["units"] = "ms"
                return identified
                
            # Check for ignition timing map (typically 16x16 with values -20 to 60 degrees)
            if all(-20 <= val <= 60 for row in data for val in row):
                identified["name"] = "KFZWOP"
                identified["description"] = "Ignition Timing Map"
                identified["factor"] = 0.75
                identified["units"] = "°"
                return identified
                
        elif map_data["type"] == "3D" and dimensions == [16, 12]:
            # Check for torque limiter map
            if all(0 <= val <= 600 for row in data for val in row):
                identified["name"] = "KFMIRL"
                identified["description"] = "Torque Limiter Map"
                identified["factor"] = 0.023438
                identified["units"] = "Nm"
                return identified
                
        elif map_data["type"] == "2D" and dimensions == [16]:
            # Check for lambda control table (typically 16 elements with values 0.8-1.2)
            if all(0.7 <= val <= 1.3 for val in data):
                identified["name"] = "KFLDRL"
                identified["description"] = "Lambda Control Table"
                identified["factor"] = 0.0078125
                identified["units"] = "Lambda"
                return identified
                
        elif map_data["type"] == "2D" and dimensions == [32]:
            # Check for MAF sensor table (typically 32 elements)
            identified["name"] = "MLHFM"
            identified["description"] = "MAF Sensor Transfer Function"
            identified["valueType"] = "float32"
            identified["factor"] = 1.0
            identified["units"] = "kg/h"
            return identified
            
        # If no specific identification, generate a name based on address
        if map_data["name"].startswith("MAP_"):
            if map_data["type"] == "3D":
                x, y = dimensions
                identified["name"] = f"MAP3D_{addr:X}_{x}x{y}"
            else:
                identified["name"] = f"TABLE_{addr:X}_{dimensions[0]}"
                
        return identified
    
    def find_all_potential_maps(self):
        """Find all potential maps and tables using multiple methods"""
        # Scan for maps using different methods and combine results
        maps_by_addr = {}  # Use a dict to avoid duplicates
        
        # Method 1: Scan known addresses
        for map_data in self.scan_known_addresses():
            addr = map_data["address"]
            maps_by_addr[addr] = map_data
        
        # Method 2: Scan for binary signatures
        for map_data in self.find_maps_by_signature():
            addr = map_data["address"]
            # Only add if we haven't already found a map at this address
            if addr not in maps_by_addr:
                maps_by_addr[addr] = map_data
        
        # Convert back to a list
        self.maps_tables = list(maps_by_addr.values())
        
        return self.maps_tables
    
    def scan_rom(self):
        """Scan the ROM for firmware info, maps and tables"""
        if not self.rom_data:
            print("No ROM data loaded")
            return False
        
        print("-[ Basic Firmware information ]-----------------------------------------------------------------")
        self.scan_for_epk()
        
        print("-[ Maps and Tables Analysis ]-----------------------------------------------------------------")
        self.find_all_potential_maps()
        
        if not self.maps_tables:
            print("No maps or tables found")
        else:
            print(f"Found {len(self.maps_tables)} maps/tables")
            
        return True
    
    def print_compact(self):
        """Print the results in a compact format"""
        if not self.maps_tables:
            print("No maps or tables found")
            return
        
        print(f"\nFound {len(self.maps_tables)} maps/tables:")
        print("=" * 80)
        
        for idx, item in enumerate(self.maps_tables, 1):
            name = item["name"]
            addr = item["address"]
            descr = item["description"]
            dims = item["dimensions"]
            vtype = item["valueType"]
            units = item["units"]
            
            # Print basic info
            print(f"{idx}. {Colors.BOLD}{name}{Colors.ENDC} @ 0x{addr:X}")
            if descr:
                print(f"   Description: {descr}")
            
            if item["type"] == "3D":
                dim_str = f"{dims[0]}x{dims[1]}"
            else:
                dim_str = str(dims[0])
            
            print(f"   Type: {item['type']} | Dimensions: {dim_str} | Data Type: {vtype}")
            
            if units:
                print(f"   Units: {units}")
            
            # Print a sample of the data
            if item["type"] == "3D":
                data = item["data"]
                print("   Data Sample:")
                # Print first few rows/cols
                max_rows = min(3, len(data))
                max_cols = min(5, len(data[0]))
                
                for r in range(max_rows):
                    row_data = data[r][:max_cols]
                    if max_cols < len(data[r]):
                        row_str = ", ".join(f"{v:.2f}" for v in row_data) + ", ..."
                    else:
                        row_str = ", ".join(f"{v:.2f}" for v in row_data)
                    print(f"     Row {r}: [{row_str}]")
                
                if max_rows < len(data):
                    print("     ...")
            else:
                data = item["data"]
                print("   Data Sample:")
                max_items = min(10, len(data))
                if max_items < len(data):
                    data_str = ", ".join(f"{v:.2f}" for v in data[:max_items]) + ", ..."
                else:
                    data_str = ", ".join(f"{v:.2f}" for v in data)
                print(f"     [{data_str}]")
            
            print("-" * 80)
    
    def generate_xdf(self, output_file):
        """Generate an XDF file for TunerPro from the found maps/tables"""
        if not self.maps_tables:
            print("No maps or tables to export")
            return False
            
        print(f"Generating XDF file: {output_file}")
            
        # XDF file generation code would go here
        # This would convert the maps_tables data into XDF format
        # This is a simplified placeholder implementation
        
        try:
            with open(output_file, "w") as f:
                f.write("<!-- TunerPro XDF format - Generated by ME7 Ferrari Scanner -->\n")
                f.write("<XDFFORMAT version=\"1.60\">\n")
                f.write("  <XDFHEADER>\n")
                f.write("    <flags>0x1</flags>\n")
                f.write("    <description>Ferrari ME7 ECU</description>\n")
                f.write("  </XDFHEADER>\n")
                
                # Write each map/table as an XDF object
                for item in self.maps_tables:
                    f.write("  <XDFTABLE>\n")
                    f.write(f"    <title>{item['name']}</title>\n")
                    f.write(f"    <description>{item['description']}</description>\n")
                    f.write(f"    <EMBEDDEDDATA mmaddress=\"0x{item['address']:X}\" /></XDFTABLE>\n")
                
                f.write("</XDFFORMAT>\n")
                
            print(f"XDF file saved: {output_file}")
            return True
        except Exception as e:
            print(f"Error generating XDF file: {e}")
            return False


def main():
    """Main function to parse arguments and run the scanner"""
    parser = argparse.ArgumentParser(description="Advanced ME7 Ferrari ROM Scanner")
    parser.add_argument("rom_file", help="Path to the ROM binary file")
    parser.add_argument("--output", "-o", help="Save results to a JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--xdf", "-x", help="Generate an XDF file for TunerPro")
    
    args = parser.parse_args()
    
    # Print banner
    print("Advanced Ferrari ME7 ROM Tool - Python Edition")
    print("Based on ME7RomTool_Ferrari by 360trev")
    print("https://github.com/360trev/ME7RomTool_Ferrari")
    print("-" * 80)
    
    # Create scanner and load ROM
    scanner = ME7RomAdvancedScanner(verbose=args.verbose)
    if not scanner.load_rom(args.rom_file):
        return 1
    
    # Scan ROM
    scanner.scan_rom()
    
    # Print results
    if scanner.maps_tables:
        scanner.print_compact()
    
    # Generate XDF if requested
    if args.xdf and scanner.maps_tables:
        scanner.generate_xdf(args.xdf)
    
    # Save results if requested
    if args.output:
        try:
            results = {
                "epk_info": scanner.epk_info,
                "maps_tables": scanner.maps_tables
            }
            
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to {args.output}")
        except Exception as e:
            print(f"Error saving results: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())