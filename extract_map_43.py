import subprocess
import re
import argparse
from pathlib import Path

def run_me7romtool(fls_file: str) -> str:
    """
    Run me7romtool.exe on the given FLS file and return the output.
    
    Args:
        fls_file (str): Path to the FLS file.
        
    Returns:
        str: The captured output from the command.
        
    Raises:
        FileNotFoundError: If the FLS file or executable is not found.
        subprocess.CalledProcessError: If the command fails.
    """
    # Path to the executable
    exe_path = Path("windows-bin") / "me7romtool.exe"
    
    # Verify that the executable and FLS file exist
    if not exe_path.is_file():
        raise FileNotFoundError(f"Executable not found at {exe_path}")
    if not Path(fls_file).is_file():
        raise FileNotFoundError(f"FLS file not found at {fls_file}")
    
    # Command to execute
    command = [str(exe_path), "-maps", "-romfile", fls_file]
    
    try:
        # Run the command and capture output
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise subprocess.CalledProcessError(
            e.returncode, e.cmd, output=e.output, stderr=e.stderr
        )

def extract_map_43(output: str) -> str:
    """
    Extract the Map #43 section from the me7romtool output.
    
    Args:
        output (str): The full output from me7romtool.
        
    Returns:
        str: The extracted Map #43 section, or an empty string if not found.
    """
    # Define the pattern to match Map #43 section
    # Look for the header and capture everything until the next map or end
    pattern = r"\[Map #43\].*?(?=\[Map #\d+\]|$)"
    
    # Find the Map #43 section using regex
    match = re.search(pattern, output, re.DOTALL)
    
    if match:
        return match.group(0).strip()
    else:
        return ""

def process_fls_file(fls_file: str) -> str:
    """
    Process an FLS file to extract Map #43 data.
    
    Args:
        fls_file (str): Path to the FLS file.
        
    Returns:
        str: The extracted Map #43 data.
    """
    # Run the tool and get output
    output = run_me7romtool(fls_file)
    
    # Extract Map #43
    map_43_data = extract_map_43(output)
    
    return map_43_data

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Extract Map #43 data from an FLS file using me7romtool.")
    parser.add_argument(
        "fls_file",
        type=str,
        help="Path to the FLS file to process"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Process the FLS file
    try:
        map_43 = process_fls_file(args.fls_file)
        if map_43:
            print("Extracted Map #43 Data:")
            print(map_43)
        else:
            print("Map #43 not found in the output.")
    except Exception as e:
        print(f"Error: {e}")