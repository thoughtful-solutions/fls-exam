@echo off
echo Starting FLS file comparisons...
echo Results will be appended to full_output.txt

:: Clear previous output file to avoid duplication
if exist "full_output.txt" del "full_output.txt"

:: Step 1: LHS vs. RHS Stock Comparisons (check side symmetry)
echo Checking LHS vs. RHS Stock Comparisons...
for %%f in ("LHS Stock.FLS" "LHS Stock F430 142324.FLS" "LHS Stock F430 142877.FLS" "LHS Stock F430 145324.FLS" "LHS Stock 2007 F430 155283.FLS" "F430 Black 141072 LHS Stock.FLS") do (
    if exist "%%f" (
        if exist "%%~nf RHS Stock.FLS" (
            echo Comparing "%%f" with "%%~nf RHS Stock.FLS" >> "full_output.txt"
            python fls_compare.py "%%f" "%%~nf RHS Stock.FLS" >> "full_output.txt"
        ) else (
            echo Error: "%%~nf RHS Stock.FLS" not found >> "full_output.txt"
        )
    ) else (
        echo Error: "%%f" not found >> "full_output.txt"
    )
)

:: Step 2: Stock vs. Gated/Tune Comparisons (same ID, check tuning changes)
echo Checking Stock vs. Gated/Tune Comparisons...
python fls_compare.py "LHS Stock F430 142324.FLS" "LHS Gated Tuned F430 142324.FLS" >> "full_output.txt"
python fls_compare.py "RHS Stock F430 142324.FLS" "RHS Gated Tuned F430 142324.FLS" >> "full_output.txt"
python fls_compare.py "LHS Stock F430 145324.FLS" "LHS Gated F430 145324.FLS" >> "full_output.txt"
python fls_compare.py "RHS Stock F430 145324.FLS" "RHS Gated F430 145324.FLS" >> "full_output.txt"
python fls_compare.py "LHS Stock 2007 F430 155283.FLS" "LHS Gated Tune 2007 F430 155283.FLS" >> "full_output.txt"
python fls_compare.py "RHS Stock 2007 F430 155283.FLS" "RHS Gated Tune 2007 F430 155283.FLS" >> "full_output.txt"
python fls_compare.py "LHS Gated Tune 2006 F430 148508.FLS" "RHS Gated Tune 2006 F430 148508.FLS" >> "full_output.txt"

:: Step 3: Stock vs. Stock Across IDs (check variant differences)
echo Checking Stock vs. Stock Across IDs...
python fls_compare.py "LHS Stock F430 142324.FLS" "LHS Stock F430 142877.FLS" >> "full_output.txt"
python fls_compare.py "LHS Stock F430 142324.FLS" "LHS Stock F430 145324.FLS" >> "full_output.txt"
python fls_compare.py "LHS Stock F430 142324.FLS" "LHS Stock 2007 F430 155283.FLS" >> "full_output.txt"
python fls_compare.py "LHS Stock.FLS" "LHS Stock F430 142324.FLS" >> "full_output.txt"

:: Step 4: Tune vs. Tune Across Years/IDs (check tuning consistency)
echo Checking Tune vs. Tune Across Years/IDs...
python fls_compare.py "LHS Gated Tune 2006 F430 148508.FLS" "LHS Gated Tune 2007 F430 155283.FLS" >> "full_output.txt"
python fls_compare.py "LHS Gated Tuned F430 142324.FLS" "LHS Gated Tune 2007 F430 155283.FLS" >> "full_output.txt"
python fls_compare.py "LHS Gated F430 145324.FLS" "LHS Gated Tune 2007 F430 155283.FLS" >> "full_output.txt"

:: Step 5: Black Variant vs. Other Stock (check uniqueness)
echo Checking Black Variant vs. Other Stock...
python fls_compare.py "F430 Black 141072 LHS Stock.FLS" "LHS Stock F430 142324.FLS" >> "full_output.txt"

echo Comparisons complete. Check full_output.txt for results.