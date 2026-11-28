@echo off
pip install pyinstaller
pyinstaller --noconsole --onefile --windowed --icon=logo.ico --name adm_hospeda main.py
echo Executavel em dist\adm_hospeda.exe
pause
