@echo off
rem 動物版桌寵（小狼），不跳出終端機視窗
rem 電腦上可能有多個 Python，PATH 第一個不一定裝了 PySide6，所以逐一找能 import PySide6 的那個
for /f "delims=" %%P in ('where pythonw 2^>nul') do (
  "%%~dpPpython.exe" -c "import PySide6" >nul 2>&1 && (
    start "" "%%P" "%~dp0pet.py"
    exit /b 0
  )
)
echo No Python with PySide6 found. Run: pip install -r "%~dp0requirements.txt"
pause
