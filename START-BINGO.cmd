@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0.deps;%PYTHONPATH%"
if exist "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
  "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m streamlit run app.py --server.address 127.0.0.1
) else (
  py -m streamlit run app.py --server.address 127.0.0.1
)
pause
