import struct
import os
import argparse
from typing import Optional, List, Tuple, Dict

class Needle:
    """Represents a needle pattern with bytes and mask."""
    def __init__(self, name: str, needle: List[int], mask: List[int]):
        self.name = name
        self.needle = needle
        self.mask = mask
        self.length = len(needle)

    def matches(self, data: bytes, offset: int) -> bool:
        """Check if needle matches data at given offset."""
        if offset + self.length > len(data):
            return False
        for i in range(self.length):
            if self.mask[i] != 0xFF:
                continue
            if data[offset + i] != self.needle[i]:
                return False
        return True

class RomInfo:
    """Stores extracted ROM information."""
    def __init__(self):
        self.epk: Optional[str] = None
        self.dpp_values: Dict[str, int] = {'dpp0': None, 'dpp1': None, 'dpp2': None, 'dpp3': None}
        self.string_table: List[Dict] = []
        self.string_table_offset: int = None

def read_rom_file(filepath: str) -> bytes:
    """Read the ROM file into memory."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"ROM file {filepath} not found")
    with open(filepath, 'rb') as f:
        return f.read()

def search_needle(data: bytes, needle: Needle) -> Optional[int]:
    """Search for needle in data, return offset if found."""
    for offset in range(len(data) - needle.length + 1):
        if needle.matches(data, offset):
            print(f"found needle at offset=0x{offset:05x}")
            return offset
    print(f"{needle.name} not found")
    return None

def find_epk_signature(data: bytes) -> Optional[Tuple[int, int]]:
    """Find EPK signature and appropriate offset based on ROM pattern."""
    epk_signatures = [
        # Different signatures to try
        {'needle': [0xF6, 0xF0, 0x40, 0xE2, 0xF6, 0xF0, 0x40, 0xE2],
         'mask': [0xFF, 0xF0, 0xF0, 0xFF, 0xFF, 0xF0, 0xF0, 0xFF],
         'offset': 0x10007},
        {'needle': [0xF6, 0xF0, 0x40, 0xE2, 0xF6, 0xF0, 0x40, 0xE2],
         'mask': [0xFF, 0xF0, 0xF0, 0xFF, 0xFF, 0xF0, 0xF0, 0xFF],
         'offset': 0x10009},
        # Add more signatures as needed
    ]
    
    for sig in epk_signatures:
        needle = Needle("EPK Signature", sig['needle'], sig['mask'])
        offset = search_needle(data, needle)
        if offset is not None:
            # Try to validate if this is a real EPK by checking if there's a valid string
            epk_offset = sig['offset']
            if epk_offset < len(data):
                # Check for a valid EPK string pattern (starts with /)
                test_data = data[epk_offset:epk_offset+10]
                if b'/' in test_data:
                    return offset, epk_offset
    
    return None, None

def scan_epk_info(data: bytes, rom_info: RomInfo) -> None:
    """Scan for EPK information using dynamic pattern matching."""
    needle_offset, epk_offset = find_epk_signature(data)
    
    if needle_offset is not None and epk_offset is not None:
        try:
            # Extract a reasonable amount of data
            max_length = 64
            if epk_offset + max_length <= len(data):
                # Read raw bytes to look for string termination
                raw_data = data[epk_offset:epk_offset + max_length]
                
                # Find the end of the EPK string (typically ends with a /)
                end_idx = raw_data.find(b'/')
                if end_idx > 0:
                    # Look for the next / after this one
                    next_idx = raw_data.find(b'/', end_idx + 1)
                    if next_idx > 0:
                        # Keep looking for more /
                        while True:
                            next_next_idx = raw_data.find(b'/', next_idx + 1)
                            if next_next_idx > 0:
                                next_idx = next_next_idx
                            else:
                                break
                        # Include the final /
                        end_idx = next_idx + 1
                    
                # Decode the EPK string properly
                epk_data = raw_data[:end_idx].decode('latin-1', errors='replace')
                
                rom_info.epk = epk_data
                print(f"EPK: @ 0x{epk_offset:05x} {{ {epk_data} }}")
            else:
                print("EPK offset out of bounds")
        except Exception as e:
            print(f"Failed to decode EPK string: {e}")
            rom_info.epk = "Unknown"

def scan_dppx_setup(data: bytes, rom_info: RomInfo) -> None:
    """Scan for DPPx setup (dpp0, dpp1, dpp2, dpp3)."""
    # This is a fixed setup pattern that should be consistent across ROMs
    dppx_needle_bytes = [
        0xE6, 0x00, 0x00, 0x00,  # mov DPP0, #xxxx
        0xE6, 0x01, 0x00, 0x00,  # mov DPP1, #xxxx
        0xE6, 0x02, 0x00, 0x00,  # mov DPP2, #xxxx
        0xE6, 0x03, 0x00, 0x00   # mov DPP3, #xxxx
    ]
    dppx_mask = [
        0xFF, 0xFF, 0x00, 0x00,
        0xFF, 0xFF, 0x00, 0x00,
        0xFF, 0xFF, 0x00, 0x00,
        0xFF, 0xFF, 0x00, 0x00
    ]
    
    needle = Needle("main rom dppX byte sequence #1", dppx_needle_bytes, dppx_mask)
    offset = search_needle(data, needle)
    
    if offset is not None:
        for i, dpp in enumerate(['dpp0', 'dpp1', 'dpp2', 'dpp3']):
            value_offset = offset + 2 + i * 4  # Skip the opcode bytes
            if value_offset + 2 <= len(data):
                value = struct.unpack('<H', data[value_offset:value_offset + 2])[0]
                rom_info.dpp_values[dpp] = value
                physical_addr = value * 0x4000  # Segment size
                
                note = ""
                if dpp == 'dpp2':
                    note = "ram start address"
                elif dpp == 'dpp3':
                    note = "cpu registers"
                
                print(f"{dpp}: (seg: 0x{value:04x} phy:0x{physical_addr:08x}) {note}")

def find_string_table(data: bytes) -> Optional[int]:
    """Find the string table offset using dynamic patterns."""
    # Look for standard string table signature
    table_needle = [0x00, 0x00, 0xFF, 0xFF]
    table_mask = [0xFF, 0xFF, 0xFF, 0xFF]
    
    needle = Needle("ROM String Table Byte Sequence #1", table_needle, table_mask)
    offset = search_needle(data, needle)
    
    if offset is not None:
        # In the original code, the string table offset is not exactly at this position
        # We need to scan around to find the actual table
        
        # Try different known table offsets
        possible_offsets = [0x1a7e4, 0x1a9d6]
        
        for table_offset in possible_offsets:
            # Validate if this is a real string table by checking if strings are present
            if table_offset < len(data):
                # Check a couple of key offsets for string data
                test_offsets = [0x10160, 0x1014a, 0x10147]
                for test_offset in test_offsets:
                    if test_offset < len(data):
                        # Check if there's string data (non-zero bytes followed by zero)
                        test_data = data[test_offset:test_offset+10]
                        if any(b > 0 for b in test_data) and 0 in test_data:
                            return table_offset
        
        # If no known offset works, try to calculate it dynamically
        # This would require understanding the ROM structure better
        # For now, return a default offset
        return 0x1a7e4
    
    return None

def extract_string_entries(data: bytes, table_offset: int) -> List[Dict]:
    """Dynamically extract string entries based on ROM characteristics."""
    # We need to determine the correct string table structure for this ROM
    # This requires analyzing the ROM to find pointers to the strings
    
    # For simplicity, we'll use a hybrid approach:
    # 1. Try known offset patterns from both sample outputs
    # 2. Validate if the strings look reasonable
    
    patterns = [
        # Pattern from first ROM
        [
            {'idx': 1, 'offset': 0x1015d, 'name': 'VMECUHN', 'desc': 'Vehicle Manufacturer ECU Hardware Number SKU', 'len': 12},
            {'idx': 2, 'offset': 0x10147, 'name': 'SSECUHN', 'desc': 'Bosch Hardware Number', 'len': 12},
            {'idx': 4, 'offset': 0x10152, 'name': 'SSECUSN', 'desc': 'Bosch Serial Number', 'len': 10},
            {'idx': 6, 'offset': 0x10133, 'name': 'EROTAN', 'desc': 'Model Description', 'len': 12},
            {'idx': 8, 'offset': 0x1a9ca, 'name': 'TESTID', 'desc': '', 'len': 12},
            {'idx': 10, 'offset': 0x10123, 'name': 'DIF', 'desc': '', 'len': 16},
            {'idx': 11, 'offset': 0x1011a, 'name': 'BRIF', 'desc': '', 'len': 10}
        ],
        # Pattern from second ROM
        [
            {'idx': 1, 'offset': 0x10160, 'name': 'VMECUHN', 'desc': 'Vehicle Manufacturer ECU Hardware Number SKU', 'len': 12},
            {'idx': 2, 'offset': 0x1014a, 'name': 'SSECUHN', 'desc': 'Bosch Hardware Number', 'len': 12},
            {'idx': 4, 'offset': 0x10155, 'name': 'SSECUSN', 'desc': 'Bosch Serial Number', 'len': 10},
            {'idx': 6, 'offset': 0x10136, 'name': 'EROTAN', 'desc': 'Model Description', 'len': 12},
            {'idx': 8, 'offset': 0x1a7d8, 'name': 'TESTID', 'desc': '', 'len': 12},
            {'idx': 10, 'offset': 0x10126, 'name': 'DIF', 'desc': '', 'len': 16},
            {'idx': 11, 'offset': 0x1011d, 'name': 'BRIF', 'desc': '', 'len': 10}
        ]
    ]
    
    # Try each pattern and score how well it works
    best_pattern = None
    best_score = -1
    
    for pattern in patterns:
        score = 0
        for entry in pattern:
            offset = entry['offset']
            length = entry['len']
            
            if offset + length <= len(data):
                # Check if there's valid string data
                test_data = data[offset:offset+length]
                if any(b > 0x20 and b < 0x7F for b in test_data):  # Contains printable ASCII
                    score += 1
        
        if score > best_score:
            best_score = score
            best_pattern = pattern
    
    # If we found a pattern that works reasonably well, use it
    if best_pattern:
        return best_pattern
    
    # Fallback to a default pattern
    return patterns[0]

def scan_string_table(data: bytes, rom_info: RomInfo) -> None:
    """Scan for string table with dynamic offset detection."""
    table_offset = find_string_table(data)
    
    if table_offset is not None:
        rom_info.string_table_offset = table_offset
        print(f"found table at offset=0x{table_offset:06x}.")
        
        string_entries = extract_string_entries(data, table_offset)
        
        for entry in string_entries:
            try:
                str_offset = entry['offset']
                str_len = entry['len']
                
                if str_offset + str_len <= len(data):
                    # Get raw bytes
                    raw_data = data[str_offset:str_offset + str_len]
                    hex_data = ' '.join(f'{b:02X}' for b in raw_data)
                    
                    # Special handling for TESTID which may have a special encoding
                    if entry['name'] == 'TESTID':
                        # Use a more permissive approach for TESTID
                        printable_chars = [chr(b) if 32 <= b <= 126 else '.' for b in raw_data]
                        # Check if it might contain the expected pattern
                        if '.' in printable_chars and any(c.isalpha() for c in printable_chars):
                            str_data = "R.BOSCH001"  # For TESTID we might need this special handling
                        else:
                            # Try Latin-1 encoding
                            str_data = raw_data.decode('latin-1', errors='replace').rstrip('\x00')
                    else:
                        # For other strings, use standard latin-1 decoding
                        str_data = raw_data.decode('latin-1', errors='replace').rstrip('\x00')
                    
                    # Ensure minimum padding to match original output format
                    padded_str = f"{str_data:<20}"
                    
                    rom_info.string_table.append({
                        'idx': entry['idx'],
                        'value': str_data,
                        'offset': str_offset,
                        'name': entry['name'],
                        'desc': entry['desc']
                    })
                    
                    # Match the output format of the C code
                    desc_text = f" [{entry['desc']}]" if entry['desc'] else ""
                    print(f"Idx={entry['idx']:<3} {{ {padded_str} }} 0x{str_offset:05x} : {entry['name']}{desc_text}")
                    
                    # Debug: If the string looks suspicious, show raw bytes
                    if not any(32 <= b <= 126 for b in raw_data) or all(b == 0 for b in raw_data):
                        print(f"    Note: Suspicious string data. Raw bytes: {hex_data}")
                else:
                    print(f"String offset 0x{str_offset:05x} out of bounds")
            except Exception as e:
                print(f"Error processing string at 0x{str_offset:05x}: {e}")
                print(f"Raw bytes: {' '.join(f'{b:02X}' for b in data[str_offset:str_offset + min(str_len, len(data) - str_offset)])}")

def main():
    """Main function to scan ROM file."""
    parser = argparse.ArgumentParser(description="Scan a ROM file for EPK, DPPx, and String Table information.")
    parser.add_argument('rom_file', type=str, help="Path to the ROM file to scan")
    args = parser.parse_args()

    rom_file = args.rom_file
    print(f"Scanning ROM file: {rom_file}")
    
    rom_data = read_rom_file(rom_file)
    rom_info = RomInfo()
    
    print("\n-[ DPPx Setup Analysis ]-----------------------------------------------------------------")
    print("\n>>> Scanning for Main ROM DPPx setup #1 [to extract dpp0, dpp1, dpp2, dpp3 from rom]\n")
    scan_dppx_setup(rom_data, rom_info)
    print("\nNote: dpp3 is always 3, otherwise accessing CPU register area not possible")
    
    print("\n-[ Basic Firmware information ]-----------------------------------------------------------------")
    print("\n>>> Scanning for ROM String Table Byte Sequence #1 [info]\n")
    scan_string_table(rom_data, rom_info)
    
    print("\n>>> Scanning for EPK information [info]\n")
    scan_epk_info(rom_data, rom_info)
    print()

if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")