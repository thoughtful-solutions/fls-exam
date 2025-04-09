#!/usr/bin/env python3
"""
Binary N-Gram Analyzer for ECU FLS Files
----------------------------------------
This script analyzes multiple binary FLS files to find common byte patterns
and their positions, helping to identify structures and configuration data.

Usage:
    python binary_ngram.py -n 8 -t 3 path/to/file1.fls path/to/file2.fls [...]
    
    -n, --ngram-size: Size of n-grams to analyze (default: 8)
    -t, --top: Number of top patterns to display (default: 20)
    -m, --min-files: Minimum number of files a pattern must appear in (default: 2)
    -o, --output: Output results to file (default: screen only)
"""

import os
import sys
import argparse
import binascii
from collections import Counter, defaultdict

def extract_ngrams_from_binary(file_path, n=8):
    """Extract n-byte sequences from a binary file with their positions."""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Dictionary to store ngrams and their positions
        ngrams_with_positions = defaultdict(list)
        
        # Generate ngrams
        for i in range(len(content) - n + 1):
            ngram = content[i:i+n]
            # Store as hex string for easier comparison
            hex_ngram = binascii.hexlify(ngram).decode('ascii')
            ngrams_with_positions[hex_ngram].append(i)
        
        return ngrams_with_positions
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return {}

def byte_to_ascii(byte_val):
    """Convert a byte to ASCII character if printable, or dot if not."""
    if 32 <= byte_val <= 126:
        return chr(byte_val)
    return '.'

def format_pattern(hex_pattern):
    """Format a hex pattern for display with hex and ASCII representation."""
    # Split into pairs for readability
    byte_pairs = [hex_pattern[i:i+2] for i in range(0, len(hex_pattern), 2)]
    hex_repr = ' '.join(byte_pairs)
    
    # Convert to bytes then to ASCII representation
    bytes_array = binascii.unhexlify(hex_pattern)
    ascii_repr = ''.join(byte_to_ascii(b) for b in bytes_array)
    
    return hex_repr, ascii_repr

def format_position(pos):
    """Format a position as a hexadecimal address."""
    return f"0x{pos:08x}"

def analyze_files(file_list, ngram_size=8, top_count=20, min_files=2, output_file=None):
    """Analyze a list of files for common n-grams."""
    # Dictionary to store results for each file
    all_files_ngrams = {}
    ngrams_with_positions = {}
    
    # Process all files
    for file_path in file_list:
        file_name = os.path.basename(file_path)
        print(f"Processing {file_name}...")
        
        ngrams_pos = extract_ngrams_from_binary(file_path, ngram_size)
        ngrams_with_positions[file_name] = ngrams_pos
        all_files_ngrams[file_name] = set(ngrams_pos.keys())
    
    # Find patterns that appear in at least min_files files
    pattern_counts = Counter()
    all_patterns = set()
    
    for file_name, ngrams in all_files_ngrams.items():
        all_patterns.update(ngrams)
    
    for pattern in all_patterns:
        count = sum(1 for file_ngrams in all_files_ngrams.values() if pattern in file_ngrams)
        if count >= min_files:
            pattern_counts[pattern] = count
    
    # Prepare output
    output_lines = []
    output_lines.append(f"\nTop {top_count} common patterns found in at least {min_files} files:")
    
    # Set up output destination
    output_dest = open(output_file, 'w') if output_file else sys.stdout
    
    # Display results
    for pattern, count in pattern_counts.most_common(top_count):
        hex_repr, ascii_repr = format_pattern(pattern)
        
        output_lines.append(f"Pattern: {hex_repr} | ASCII: {ascii_repr} | Found in {count} files")
        
        # Show positions in each file
        for file_name in sorted(all_files_ngrams.keys()):
            if pattern in ngrams_with_positions[file_name]:
                positions = ngrams_with_positions[file_name][pattern]
                
                # Get the first 5 positions
                hex_positions = [format_position(pos) for pos in positions[:5]]
                
                # Indicate if there are more
                if len(positions) > 5:
                    hex_positions.append(f"... ({len(positions) - 5} more)")
                
                output_lines.append(f"  - {file_name}: {', '.join(hex_positions)}")
        
        output_lines.append("")  # Add a blank line between patterns
    
    # Write or print output
    for line in output_lines:
        print(line, file=output_dest)
    
    if output_file:
        output_dest.close()
        print(f"Results written to {output_file}")
    
    # Return statistics
    return {
        "files_analyzed": len(file_list),
        "common_patterns": len(pattern_counts),
        "top_patterns_shown": min(top_count, len(pattern_counts))
    }

def main():
    parser = argparse.ArgumentParser(description='Analyze binary FLS files for common n-grams')
    parser.add_argument('files', nargs='+', help='FLS files to analyze')
    parser.add_argument('-n', '--ngram-size', type=int, default=8, help='Size of n-grams to analyze')
    parser.add_argument('-t', '--top', type=int, default=20, help='Number of top patterns to display')
    parser.add_argument('-m', '--min-files', type=int, default=2, 
                        help='Minimum number of files a pattern must appear in')
    parser.add_argument('-o', '--output', help='Output file for results')
    
    args = parser.parse_args()
    
    # Verify files exist
    valid_files = []
    for file_path in args.files:
        if os.path.isfile(file_path):
            valid_files.append(file_path)
        else:
            print(f"Warning: File not found: {file_path}")
    
    if not valid_files:
        print("Error: No valid files to analyze")
        return 1
    
    # Run analysis
    stats = analyze_files(
        valid_files, 
        ngram_size=args.ngram_size, 
        top_count=args.top, 
        min_files=args.min_files,
        output_file=args.output
    )
    
    print(f"Analysis complete. Processed {stats['files_analyzed']} files, "
          f"found {stats['common_patterns']} common patterns, "
          f"showing top {stats['top_patterns_shown']}.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())