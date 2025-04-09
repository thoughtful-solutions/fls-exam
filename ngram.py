import os
import re
from collections import Counter

def extract_ngrams_with_positions(file_path, n=8):
    """Extract n-byte sequences from a hex dump file with their positions."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Extract only valid hex pairs
        hex_bytes = re.findall(r'[0-9a-f]{2}', content.lower())
        
        # Extract n-byte sequences (n hex bytes) with positions
        ngrams_with_positions = {}
        for i in range(len(hex_bytes) - n + 1):
            ngram = ''.join(hex_bytes[i:i+n])
            if ngram in ngrams_with_positions:
                ngrams_with_positions[ngram].append(i)
            else:
                ngrams_with_positions[ngram] = [i]
        
        return ngrams_with_positions
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return {}

# Process all hex files
files = [f for f in os.listdir('.') if f.endswith('.hex')]
all_ngrams = {}
ngrams_with_positions = {}

for file in files:
    print(f"Processing {file}...")
    ngrams_with_pos = extract_ngrams_with_positions(file)
    ngrams_with_positions[file] = ngrams_with_pos
    all_ngrams[file] = set(ngrams_with_pos.keys()) if ngrams_with_pos else set()

# Find common patterns across all files
if len(files) > 0 and all(len(ngrams) > 0 for ngrams in all_ngrams.values()):
    common_patterns = set.intersection(*all_ngrams.values())
    
    # Sort by frequency across all files
    pattern_counts = Counter()
    for file, ngrams in all_ngrams.items():
        for pattern in common_patterns:
            pattern_counts[pattern] += 1
    
    print("\nTop common patterns found across all files:")
    for pattern, count in pattern_counts.most_common(20):
        # Convert back to bytes for readability
        byte_repr = ' '.join(pattern[i:i+2] for i in range(0, len(pattern), 2))
        
        # Safely convert to ASCII where possible
        ascii_repr = ''
        for i in range(0, len(pattern), 2):
            try:
                byte_val = int(pattern[i:i+2], 16)
                if 32 <= byte_val <= 126:
                    ascii_repr += chr(byte_val)
                else:
                    ascii_repr += '.'
            except ValueError:
                ascii_repr += '?'
        
        print(f"Pattern: {byte_repr} | ASCII: {ascii_repr} | Found in {count} files")
        
        # Show positions in each file
        for file in files:
            if pattern in ngrams_with_positions[file]:
                positions = ngrams_with_positions[file][pattern]
                hex_positions = [f"0x{pos*2:x}" for pos in positions[:5]]  # Show first 5 positions in hex
                if len(positions) > 5:
                    hex_positions.append(f"... ({len(positions) - 5} more)")
                print(f"  - {file}: {', '.join(hex_positions)}")
else:
    print("No common patterns found or error in processing files.")