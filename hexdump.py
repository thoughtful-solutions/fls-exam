import os
import glob
import argparse

def print_hex_dump(data: bytes, start: int, end: int, label: str) -> None:
    """Print a hex dump of data from start to end with a label."""
    if start < 0 or end > len(data) or start >= end:
        print(f"Invalid range for {label}: 0x{start:x} to 0x{end:x}")
        return
    
    print(f"\n{label} (0x{start:x} to 0x{end:x}):")
    for i in range(start, end, 16):  # 16 bytes per line
        line = data[i:min(i + 16, end)]
        # Hex representation
        hex_str = ' '.join(f'{b:02x}' for b in line)
        # ASCII representation (printable chars or '.')
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in line)
        # Pad hex string for alignment if less than 16 bytes
        hex_str = hex_str.ljust(47)  # 16 * 2 (hex) + 15 (spaces) = 47
        print(f"0x{i:06x}: {hex_str}  {ascii_str}")

def dump_regions(file_path: str) -> None:
    """Dump hex for specified regions in an FLS file."""
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        print(f"\nProcessing file: {file_path}")
        print("=" * 80)
        
        # Region around 0x23d94 (0x23d00 to 0x23e00)
        print_hex_dump(data, 0x23d00, 0x23e00, "Region around 0x23d94")
        
        # Region around 0x10009 (0x10000 to 0x10064, 100 bytes)
        print_hex_dump(data, 0x10000, 0x10064, "Region around 0x10009")
        
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    """Main function to process FLS files."""
    parser = argparse.ArgumentParser(description="Generate hex dumps for FLS files.")
    parser.add_argument('files', nargs='*', help="FLS files to process (or use *.FLS)")
    parser.add_argument('--dir', default='.', help="Directory to search for FLS files")
    args = parser.parse_args()

    # If no files specified, glob for *.FLS in the directory
    if not args.files:
        args.files = glob.glob(os.path.join(args.dir, "*.FLS"))
    
    if not args.files:
        print("No FLS files found in the specified directory.")
        return
    
    for file_path in args.files:
        dump_regions(file_path)

if __name__ == "__main__":
    main()