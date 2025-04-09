#!/usr/bin/env python3
"""
FLS File Comparison Tool

This script compares two FLS files and reports:
1. Differences in positions of signatures from signatures.lst
2. Byte sequence differences between the files, showing start positions, lengths, and preceding strings

Usage: python fls_compare.py <file1.fls> <file2.fls> [min_match_length]
"""

import sys
import os
import difflib
import itertools
from typing import List, Dict, Tuple, Set


def read_signatures(filename: str = "signatures.lst") -> List[str]:
    """
    Read signature strings from a file, one per line.
    
    Args:
        filename: Path to the signature list file (default: 'signatures.lst')
        
    Returns:
        List of signature strings
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            signatures = [line.strip() for line in f if line.strip()]
        return signatures
    except FileNotFoundError:
        print(f"Error: Signature file '{filename}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading signature file: {e}")
        sys.exit(1)


def search_signatures(filepath: str, signatures: List[str]) -> Dict[str, List[Tuple[int, str]]]:
    """
    Search for signatures in the given file.
    
    Args:
        filepath: Path to the file to search
        signatures: List of signature strings to search for
        
    Returns:
        Dictionary mapping signatures to lists of tuples (position, encoding)
    """
    results = {sig: [] for sig in signatures}
    
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            
        for sig in signatures:
            ascii_sig = sig.encode('ascii', errors='ignore')
            pos = 0
            while True:
                pos = content.find(ascii_sig, pos)
                if pos == -1:
                    break
                results[sig].append((pos, 'ASCII'))
                pos += 1
                
            utf8_sig = sig.encode('utf-8')
            if utf8_sig != ascii_sig:
                pos = 0
                while True:
                    pos = content.find(utf8_sig, pos)
                    if pos == -1:
                        break
                    if not any(existing_pos == pos for existing_pos, _ in results[sig]):
                        results[sig].append((pos, 'UTF-8'))
                    pos += 1
                    
        for sig in results:
            results[sig].sort(key=lambda x: x[0])
            
    except Exception as e:
        print(f"Error processing file '{filepath}': {e}")
        
    return results


def compare_signatures(file1_results: Dict[str, List[Tuple[int, str]]], 
                      file2_results: Dict[str, List[Tuple[int, str]]]) -> Dict[str, Dict[str, List]]:
    """
    Compare signature positions between two files.
    
    Args:
        file1_results: Results from the first file
        file2_results: Results from the second file
        
    Returns:
        Dictionary containing signature comparison results
    """
    comparison = {
        'only_in_file1': {},
        'only_in_file2': {},
        'position_differences': {},
        'same': {}
    }
    
    all_signatures = set(sig for sig in file1_results if file1_results[sig]) | \
                     set(sig for sig in file2_results if file2_results[sig])
    
    for sig in all_signatures:
        file1_positions = file1_results.get(sig, [])
        file2_positions = file2_results.get(sig, [])
        
        if not file1_positions and not file2_positions:
            continue
            
        if file1_positions and not file2_positions:
            comparison['only_in_file1'][sig] = file1_positions
            continue
            
        if not file1_positions and file2_positions:
            comparison['only_in_file2'][sig] = file2_positions
            continue
            
        if file1_positions == file2_positions:
            comparison['same'][sig] = file1_positions
        else:
            comparison['position_differences'][sig] = {
                'file1': file1_positions,
                'file2': file2_positions
            }
            
    return comparison


def is_printable_ascii(byte: int) -> bool:
    """Check if a byte represents a printable ASCII character."""
    return 32 <= byte <= 126


def extract_string_before(content: bytes, offset: int, max_search: int = 50, min_length: int = 4) -> Tuple[str, int]:
    """
    Search backwards from an offset to find a printable ASCII or UTF-8 string.
    
    Args:
        content: Binary content of the file
        offset: Starting offset to search backwards from
        max_search: Maximum bytes to search backwards (default: 50)
        min_length: Minimum length of a valid string (default: 4)
        
    Returns:
        Tuple of (string, string_start_offset) or (None, None) if no string found
    """
    if offset <= 0 or offset > len(content):
        return None, None

    string_bytes = []
    i = offset - 1

    while i >= 0 and (offset - i) <= max_search:
        byte = content[i]
        
        if is_printable_ascii(byte):
            string_bytes.insert(0, byte)
        else:
            if len(string_bytes) >= min_length:
                try:
                    string = bytes(string_bytes).decode('ascii')
                    return string, i + 1
                except UnicodeDecodeError:
                    try:
                        string = bytes(string_bytes).decode('utf-8')
                        return string, i + 1
                    except UnicodeDecodeError:
                        pass
            string_bytes = []
        
        i -= 1

    if len(string_bytes) >= min_length:
        try:
            string = bytes(string_bytes).decode('ascii')
            return string, i + 1
        except UnicodeDecodeError:
            try:
                string = bytes(string_bytes).decode('utf-8')
                return string, i + 1
            except UnicodeDecodeError:
                pass

    return None, None


def find_byte_differences(file1_path: str, file2_path: str, min_match_length: int = 16) -> List[Tuple[int, int]]:
    """
    Find byte sequence differences between two files.
    
    Args:
        file1_path: Path to the first file
        file2_path: Path to the second file
        min_match_length: Minimum number of matching bytes to consider as a separate sequence
        
    Returns:
        List of tuples (start_position, length) for each different segment
    """
    differences = []
    
    try:
        with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
            content1 = f1.read()
            content2 = f2.read()
        
        min_length = min(len(content1), len(content2))
        
        diff_start = None
        match_start = None
        
        i = 0
        while i < min_length:
            if content1[i] != content2[i]:
                if diff_start is None:
                    diff_start = i
                    match_start = None
                elif match_start is not None:
                    if i - match_start < min_match_length:
                        match_start = None
            else:
                if diff_start is not None and match_start is None:
                    match_start = i
                elif diff_start is not None and match_start is not None:
                    if i - match_start >= min_match_length - 1:
                        diff_length = match_start - diff_start
                        differences.append((diff_start, diff_length))
                        diff_start = None
                        match_start = None
            i += 1
        
        if diff_start is not None:
            if match_start is not None:
                if min_length - match_start >= min_match_length:
                    diff_length = match_start - diff_start
                    differences.append((diff_start, diff_length))
                else:
                    diff_length = min_length - diff_start
                    differences.append((diff_start, diff_length))
            else:
                diff_length = min_length - diff_start
                differences.append((diff_start, diff_length))
        
        if len(content1) > len(content2):
            differences.append((min_length, len(content1) - len(content2)))
        elif len(content2) > len(content1):
            differences.append((min_length, len(content2) - len(content1)))
            
    except Exception as e:
        print(f"Error comparing file bytes: {e}")
    
    return differences


def main():
    """Main function to process command line arguments and run the comparison."""
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python fls_compare.py <file1.fls> <file2.fls> [min_match_length]")
        sys.exit(1)
        
    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    
    min_match_length = 16
    if len(sys.argv) == 4:
        try:
            min_match_length = int(sys.argv[3])
            if min_match_length < 1:
                print("Warning: min_match_length must be at least 1. Using default value of 16.")
                min_match_length = 16
        except ValueError:
            print("Warning: min_match_length must be an integer. Using default value of 16.")
    
    for filepath in [file1_path, file2_path]:
        if not os.path.exists(filepath):
            print(f"Error: File '{filepath}' does not exist.")
            sys.exit(1)
    
    print(f"Comparing '{file1_path}' with '{file2_path}'")
    print(f"Using minimum match length of {min_match_length} bytes")
    
    signatures = read_signatures()
    print(f"Loaded {len(signatures)} signatures from signatures.lst")
    
    print(f"\nSearching for signatures in '{file1_path}'...")
    file1_signatures = search_signatures(file1_path, signatures)
    
    print(f"Searching for signatures in '{file2_path}'...")
    file2_signatures = search_signatures(file2_path, signatures)
    
    comparison = compare_signatures(file1_signatures, file2_signatures)
    
    print("\n=== SIGNATURE COMPARISON RESULTS ===")
    
    if comparison['only_in_file1']:
        print(f"\nSignatures found only in '{os.path.basename(file1_path)}' ({len(comparison['only_in_file1'])}):")
        for sig, positions in comparison['only_in_file1'].items():
            positions_str = ', '.join(f"{pos} ({enc})" for pos, enc in positions[:5])
            if len(positions) > 5:
                positions_str += f"... ({len(positions) - 5} more)"
            print(f"  - '{sig}': {positions_str}")
    
    if comparison['only_in_file2']:
        print(f"\nSignatures found only in '{os.path.basename(file2_path)}' ({len(comparison['only_in_file2'])}):")
        for sig, positions in comparison['only_in_file2'].items():
            positions_str = ', '.join(f"{pos} ({enc})" for pos, enc in positions[:5])
            if len(positions) > 5:
                positions_str += f"... ({len(positions) - 5} more)"
            print(f"  - '{sig}': {positions_str}")
    
    if comparison['position_differences']:
        print(f"\nSignatures found at different positions ({len(comparison['position_differences'])}):")
        for sig, data in comparison['position_differences'].items():
            print(f"  - '{sig}':")
            file1_str = ', '.join(f"{pos} ({enc})" for pos, enc in data['file1'][:5])
            if len(data['file1']) > 5:
                file1_str += f"... ({len(data['file1']) - 5} more)"
            print(f"    * '{os.path.basename(file1_path)}': {file1_str}")
            file2_str = ', '.join(f"{pos} ({enc})" for pos, enc in data['file2'][:5])
            if len(data['file2']) > 5:
                file2_str += f"... ({len(data['file2']) - 5} more)"
            print(f"    * '{os.path.basename(file2_path)}': {file2_str}")
    
    if comparison['same']:
        print(f"\nSignatures found at identical positions ({len(comparison['same'])}):")
        for sig, positions in comparison['same'].items():
            positions_str = ', '.join(f"{pos} ({enc})" for pos, enc in positions[:3])
            if len(positions) > 3:
                positions_str += f"... ({len(positions) - 3} more)"
            print(f"  - '{sig}': {positions_str}")
    
    print("\n=== BYTE SEQUENCE DIFFERENCES ===")
    byte_differences = find_byte_differences(file1_path, file2_path, min_match_length)
    
    if not byte_differences:
        print("No byte differences found. Files are identical.")
    else:
        total_diff_bytes = sum(length for _, length in byte_differences)
        file1_size = os.path.getsize(file1_path)
        file2_size = os.path.getsize(file2_path)
        avg_size = (file1_size + file2_size) / 2
        diff_percentage = (total_diff_bytes / avg_size) * 100
        
        print(f"Found {len(byte_differences)} different byte sequences "
              f"({total_diff_bytes} bytes, {diff_percentage:.2f}% different)")
        
        byte_differences.sort(key=lambda x: x[0])
        
        print("\nDifference details:")
        with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
            content1 = f1.read()
            content2 = f2.read()
            
            for i, (start, length) in enumerate(byte_differences[:20]):
                print(f"  {i+1}. Position: {start}, Length: {length} bytes")
                
                # Search for string before the difference in file1
                string1, string1_offset = extract_string_before(content1, start)
                if string1:
                    print(f"     Preceding string (File1) at offset {string1_offset}: '{string1}'")
                else:
                    print(f"     No preceding string found in File1 within 50 bytes")
                
                # Search for string before the difference in file2
                string2, string2_offset = extract_string_before(content2, start)
                if string2:
                    print(f"     Preceding string (File2) at offset {string2_offset}: '{string2}'")
                else:
                    print(f"     No preceding string found in File2 within 50 bytes")
                
                # Hex preview
                f1.seek(start)
                f2.seek(start)
                preview_length = min(length, 16)
                bytes1 = f1.read(preview_length)
                bytes2 = f2.read(preview_length)
                
                hex1 = ' '.join(f"{b:02x}" for b in bytes1)
                hex2 = ' '.join(f"{b:02x}" for b in bytes2)
                
                print(f"     File1: {hex1}")
                print(f"     File2: {hex2}")
        
        if len(byte_differences) > 20:
            print(f"\n... and {len(byte_differences) - 20} more differences")


if __name__ == "__main__":
    main()