# 📓 NotebookLM-Mini (Local AI Edition)

NotebookLM-Mini là một trợ lý học tập cá nhân dựa trên kiến trúc **Retrieval-Augmented Generation (RAG)** cấp độ sản phẩm. Phiên bản này đã được độ lại hoàn toàn để chạy **100% Offline (Không cần Internet)** sử dụng trí tuệ nhân tạo cục bộ (Local AI), bảo mật tuyệt đối dữ liệu cá nhân của bạn.

Dự án cho phép bạn tải lên tài liệu cá nhân (PDF, DOCX, PPTX, HTML...), tự động lập chỉ mục đa chiều (Hybrid Search) và tương tác với tài liệu thông qua:
- 💬 **Hỏi đáp siêu tốc** với trích dẫn chính xác.
- 📝 **Tóm tắt thông minh** sử dụng kỹ thuật Map-Reduce.
- 🎯 **Tạo bài trắc nghiệm (Quiz) & Flashcards** tự động để ôn tập.

---

## 🌟 Tính Năng Nổi Bật

1. **🚀 1-Click Run (Chạy 1 chạm):** Tự động hóa hoàn toàn quá trình cài đặt môi trường, tải Model và cấu hình hệ thống trên cả Windows và macOS. Bạn không cần biết code vẫn chạy được!
2. **🧠 Local AI Cực Mạnh:** Sử dụng mô hình `Qwen2.5-3B-Instruct` dạng nén GGUF qua Llama.cpp. Đủ thông minh để hiểu tiếng Việt xuất sắc, nhưng đủ nhẹ để chạy trên máy RAM 8GB.
3. **⚡ Hardware Acceleration (Ép xung phần cứng):** Tự động nhận diện và tận dụng tối đa sức mạnh của **Apple Silicon (Metal)** trên Mac và **Card rời NVIDIA (CUDA 12.1)** trên Windows.
4. **🔍 Hybrid Search & Reranking:** Kết hợp tìm kiếm ngữ nghĩa (GreenNode Embedding) và từ khóa (BM25), sau đó lọc lại bằng Cross-Encoder (BAAI Reranker) để đảm bảo không trượt phát nào.

---

## 🛠️ Hướng Dẫn Sử Dụng Nhanh

### Đối với người dùng Mac (macOS)
1. Tải toàn bộ thư mục dự án này về máy.
2. Mở thư mục, tìm file có tên `run_mac.command`.
3. Nhấp đúp chuột vào file đó. Hệ thống sẽ tự động cài đặt và mở giao diện Web lên cho bạn.

*(Mẹo: Lần chạy đầu tiên sẽ mất khoảng 1-2 phút để tải "Não bộ" AI (khoảng 2GB) về máy. Từ lần thứ 2 trở đi sẽ mất chưa tới 5 giây).*

### Đối với người dùng Windows
1. Tải toàn bộ thư mục dự án này về máy.
2. Nhấp đúp vào file `run_windows.bat`.
3. Hệ thống sẽ tự động cấu hình (bao gồm cả cài NVIDIA CUDA nếu máy có Card rời) và mở trình duyệt lên cho bạn sử dụng.

---

## 🏗️ Kiến Trúc Hệ Thống (Architecture)

```text
┌─────────────────────────────────────────────────────────────────────┐
│  Tầng Giao diện & Định tuyến API                                    │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐     │
│  │  Streamlit Web UI    │◄─►│  FastAPI Backend (SSE Support)  │     │
│  └──────────────────────┘  └──────────┬───────────────────────┘     │
└───────────────────────────────────────┬─────────────────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Tầng Trí Tuệ Nhân Tạo (Local AI Engine)                            │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐     │
│  │ Llama.cpp Engine     │  │ Qwen2.5-3B-Instruct (GGUF 4-bit) │     │
│  │ (Metal / CUDA 12)    │  │ 100% Offline, Privacy First      │     │
│  └──────────┬───────────┘  └──────────────────────────────────┘     │
└─────────────┼───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Tầng Xử lý Dữ liệu & RAG Pipeline                                  │
│  ┌────────────────┐  ┌───────────────┐  ┌──────────────────────┐    │
│  │ MarkItDown     │─►│ Hybrid Search │─►│ Cross-Encoder        │    │
│  │ Parser (OCR)   │  │ (Qdrant+BM25) │  │ Reranker (BGE-m3)    │    │
│  └────────────────┘  └───────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Tùy Chỉnh (Dành cho Developer)

Bạn có thể thay đổi cách hệ thống hoạt động thông qua file `.env`:

- `RAG_LLM_PROVIDER`: Đặt là `hf_local` để dùng AI cục bộ. (Hỗ trợ cả `gemini` nếu bạn muốn xài API key).
- `RAG_LLM_TEMPERATURE`: Điều chỉnh độ sáng tạo của AI (Khuyên dùng 0.4 - 0.6).
- `RAG_HYBRID_INITIAL_K`: Số lượng đoạn văn bản lấy ra lần đầu (Mặc định: 8).
- `RAG_HYBRID_RERANK_K`: Số lượng đoạn văn bản tinh tuý nhất giữ lại đưa cho AI (Mặc định: 3 - Để tối ưu tốc độ).

### Chạy thủ công
Nếu không muốn dùng tool 1-Click:
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn src.interfaces.api:app --reload
streamlit run src/interfaces/ui.py
```

---
*Dự án được xây dựng dựa trên giáo trình AI VIET NAM (AIO2025) và tối ưu hóa trải nghiệm Local AI.*
