@echo off
chcp 65001 >nul
title NotebookLM-Mini 1-Click Run cho Windows

echo ==============================================================================
echo 🚀 Khoi dong NotebookLM-Mini cho Windows...
echo ==============================================================================

cd /d "%~dp0"

:: 1. Kiểm tra Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [X] Loi: Khong tim thay Python! Vui long cai dat Python tu trang chu (nho tich "Add Python to PATH"): https://www.python.org/downloads/
    pause
    exit /b
)

:: 2. Kiểm tra và cài đặt uv
uv --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [i] Dang cai dat cong cu uv...
    python -m pip install uv
)

:: 3. Tạo và kích hoạt môi trường ảo
if not exist ".venv" (
    echo [i] Dang tao moi truong ao...
    uv venv
    if %ERRORLEVEL% neq 0 (
        echo [X] Loi: Khong the tao moi truong ao. 
        pause
        exit /b
    )
)
call .venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo [X] Loi: Khong the kich hoat moi truong ao.
    pause
    exit /b
)

:: 4. Cài đặt các thư viện cơ bản và AI Engine
echo [i] Dang cai dat cac thu vien...
uv pip install -r requirements.txt --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

python -c "import llama_cpp" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Cai dat voi CUDA that bai, chuyen sang cai dat ban CPU co ban...
    uv pip install llama-cpp-python
)

:: 6. Khởi động hệ thống
echo [*] Bat dau chay he thong...

:: Chạy Backend ở một cửa sổ riêng (thêm pause để xem lỗi nếu bị crash)
start "NotebookLM Backend" cmd /k "call .venv\Scripts\activate.bat && uvicorn src.interfaces.api:app --host 127.0.0.1 --port 8000"

echo [i] Dang nap Model AI, vui long doi 15 giay...
timeout /t 15 /nobreak

:: Mở web 
start "" "http://localhost:8501"

:: Chạy Frontend (giữ cửa sổ chính)
echo [*] Dang khoi dong Giao dien Web (Streamlit)...
streamlit run src\interfaces\ui.py --server.port 8501 --server.headless true

:: Nếu Streamlit bị văng thì tạm dừng để đọc lỗi
pause
