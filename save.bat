@echo off
REM Iterate through all files in the current directory and subdirectories
for /R %%f in (*) do (
    REM Add the file to Git
    git add "%%f"
    REM Commit the file with a specific message
    git commit -m "init add:%%~nxf"
)

echo All files have been added and committed.
pause
