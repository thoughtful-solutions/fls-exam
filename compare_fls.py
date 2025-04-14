import sys

def read_fls_file(file_path: str) -> bytes:
    with open(file_path, 'rb') as f:
        return f.read()

def find_needle_offsets(data: bytes, needle: bytes) -> list[int]:
    offsets = []
    start = 0
    while True:
        offset = data.find(needle, start)
        if offset == -1:
            break
        offsets.append(offset)
        start = offset + 1
    return offsets

def extract_table(data: bytes, offset: int, rows: int, cols: int) -> list[list[str]]:
    table = []
    for _ in range(rows):
        row = []
        for _ in range(cols):
            value = int.from_bytes(data[offset:offset+2], 'little')
            row.append(str(value))
            offset += 2
        table.append(row)
    return table

def extract_map(data: bytes, offset: int, length: int) -> bytes:
    return data[offset:offset+length]

def compare_tables(table1: list[list[str]], table2: list[list[str]], name: str):
    differences = False
    for i, (row1, row2) in enumerate(zip(table1, table2)):
        if row1 != row2:
            differences = True
            print(f"{name} differs at row {i}: {row1} vs {row2}")
    if not differences:
        print(f"No differences in {name} table.")

def compare_maps(map1: bytes, map2: bytes, name: str):
    if map1 != map2:
        print(f"{name} map differs.")
    else:
        print(f"No differences in {name} map.")

def main(file1_path: str, file2_path: str):
    data1 = read_fls_file(file1_path)
    data2 = read_fls_file(file2_path)

    # Replace with actual needle patterns
    kfp_needle = b'\x01\x02\x03\x04'  # Update this
    mlhfm_needle = b'\x05\x06\x07\x08'  # Update this

    # KFPED
    kfp_offsets1 = find_needle_offsets(data1, kfp_needle)
    kfp_offsets2 = find_needle_offsets(data2, kfp_needle)
    print(f"KFPED offsets in {file1_path}: {kfp_offsets1}")
    print(f"KFPED offsets in {file2_path}: {kfp_offsets2}")

    if not kfp_offsets1 or not kfp_offsets2:
        print("Error: KFPED needle not found in one or both files.")
        return
    elif len(kfp_offsets1) > 1 or len(kfp_offsets2) > 1:
        print("Warning: Multiple KFPED needles found. Using the first one.")
    kfp_table1 = extract_table(data1, kfp_offsets1[0] + len(kfp_needle), 10, 10)
    kfp_table2 = extract_table(data2, kfp_offsets2[0] + len(kfp_needle), 10, 10)
    compare_tables(kfp_table1, kfp_table2, "KFPED")

    # MLHFM
    mlhfm_offsets1 = find_needle_offsets(data1, mlhfm_needle)
    mlhfm_offsets2 = find_needle_offsets(data2, mlhfm_needle)
    print(f"MLHFM offsets in {file1_path}: {mlhfm_offsets1}")
    print(f"MLHFM offsets in {file2_path}: {mlhfm_offsets2}")

    if not mlhfm_offsets1 or not mlhfm_offsets2:
        print("Error: MLHFM needle not found in one or both files.")
        return
    elif len(mlhfm_offsets1) > 1 or len(mlhfm_offsets2) > 1:
        print("Warning: Multiple MLHFM needles found. Using the first one.")
    mlhfm_map1 = extract_map(data1, mlhfm_offsets1[0] + len(mlhfm_needle), 256)
    mlhfm_map2 = extract_map(data2, mlhfm_offsets2[0] + len(mlhfm_needle), 256)
    compare_maps(mlhfm_map1, mlhfm_map2, "MLHFM")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_fls.py <file1.fls> <file2.fls>")
    else:
        main(sys.argv[1], sys.argv[2])