#!/bin/bash

# ==============================================================================
# NotebookLM-Mini 1-Click Run Script for macOS
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

echo "🚀 Khởi động NotebookLM-Mini cho macOS..."

# Di chuyển đến thư mục chứa script
cd "$(dirname "$0")"

# Hàm kiểm tra command có tồn tại
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Kiểm tra Python
if ! command_exists python3; then
    echo "❌ Lỗi: Không tìm thấy Python3. Vui lòng cài đặt Python (https://www.python.org/downloads/mac-osx/)"
    exit 1
fi

# 2. Kiểm tra và cài đặt uv (Trình quản lý package siêu tốc)
if ! command_exists uv; then
    echo "📦 Đang cài đặt uv (Công cụ quản lý môi trường siêu tốc)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# 3. Khởi tạo môi trường ảo (nếu chưa có)
if [ ! -d ".venv" ]; then
    echo "🛠 Đang tạo môi trường ảo..."
    uv venv
fi

# 4. Kích hoạt môi trường ảo
source .venv/bin/activate

# 5. Cài đặt các thư viện lõi
echo "📥 Đang đồng bộ hóa thư viện..."
uv pip install -r requirements.txt

# 6. Cài đặt llama-cpp-python với cờ Metal cho Mac M-series (tối ưu tốc độ)
echo "⚡ Đang kiểm tra/cài đặt Engine AI tối ưu cho máy Mac..."
# Kiểm tra nếu chưa cài llama-cpp-python
if ! python -c "import llama_cpp" 2>/dev/null; then
    echo "🚀 Cài đặt Llama.cpp với cấu hình Apple Metal GPU..."
    CMAKE_ARGS="-DGGML_METAL=on" uv pip install llama-cpp-python --no-cache-dir
fi

# 7. Khởi động hệ thống
echo "✨ Bắt đầu chạy hệ thống..."
echo "-> Mở trình duyệt Web tại: http://localhost:8501"

# Đợi 2 giây cho Server Uvicorn khởi động, sau đó mở web
(sleep 3 && open http://localhost:8501) &

# Chạy Backend (Chạy nền)
uvicorn src.interfaces.api:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Đợi Backend nạp Model (khoảng 10-15 giây) trước khi bật giao diện
echo "⏳ Đang nạp Model AI, vui lòng đợi chút xíu..."
sleep 15

# Chạy Frontend (Streamlit)
echo "🌟 Đang mở giao diện web..."
streamlit run src/interfaces/ui.py --server.port 8501 --server.headless true

# Khi tắt Terminal, dọn dẹp Backend luôn
kill $BACKEND_PID
