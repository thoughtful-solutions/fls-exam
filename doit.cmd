rem example windows cmd line for executing over multiple files
rem  for %f in (*.fls) do (python romscanner.py  "%f" >>outputp )

rem ---- python vs me7tool scanner alignment
rem del outputp
rem del outputw
rem for %%f in (*.fls) do (python romscanner.py  "%%f" >>outputp )
rem for %%f in (*.fls) do ( windows-bin\me7romtool.exe -romfile "%%f" >>outputw )

rem ---- me7romtool.exe run
    for %%f in (*.fls) do ( 

    echo "####%$f##### >>ouputw
    windows-bin\me7romtool.exe -maps -romfile "%%f" >>outputw )