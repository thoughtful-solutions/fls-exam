rem example windows cmd line for executing over multiple files
rem  for %f in (*.fls) do (python romscanner.py  "%f" >>outputp )
del outputp
del outputw
for %%f in (*.fls) do (python romscanner.py  "%%f" >>outputp )
for %%f in (*.fls) do ( windows-bin\me7romtool.exe -romfile "%%f" >>outputw )