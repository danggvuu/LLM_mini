# 📓 NotebookLM-Mini (Local AI Edition)

NotebookLM-Mini là một trợ lý học tập cá nhân dựa trên kiến trúc **Retrieval-Augmented Generation (RAG)**. Phiên bản này đã được thiết kế lại hoàn toàn để chạy **100% Offline (Không cần Internet)** sử dụng trí tuệ nhân tạo cục bộ (Local AI), đảm bảo bảo mật tuyệt đối dữ liệu cá nhân của bạn.

Dự án cho phép bạn tải lên tài liệu cá nhân (PDF, DOCX, PPTX, HTML...), tự động phân tích và tương tác qua:
- 💬 **Hỏi đáp siêu tốc** với trích dẫn chính xác.
- 📝 **Tóm tắt thông minh** sử dụng kỹ thuật Map-Reduce.
- 🎯 **Tạo bài trắc nghiệm (Quiz) & Flashcards** tự động để ôn tập.

---

## 🌟 Tính Năng Nổi Bật

1. **🚀 1-Click Run (Chạy 1 chạm):** Tự động hóa hoàn toàn quá trình tải Model và cấu hình hệ thống trên cả Windows và macOS. Không cần biết code vẫn chạy được!
2. **🧠 Local AI Cực Mạnh:** Sử dụng mô hình `Qwen2.5-3B-Instruct` dạng nén GGUF qua Llama.cpp. Đủ thông minh để hiểu tiếng Việt xuất sắc, nhưng đủ nhẹ để chạy trên máy RAM 8GB.
3. **⚡ Hardware Acceleration (Ép xung phần cứng):** Tự động nhận diện và tận dụng tối đa sức mạnh của **Apple Silicon (Metal)** trên Mac và **Card rời NVIDIA (CUDA 12.1)** trên Windows.
4. **🔍 Hybrid Search & Reranking:** Kết hợp tìm kiếm ngữ nghĩa (GreenNode) và từ khóa (BM25), sau đó lọc lại bằng Cross-Encoder (BAAI Reranker) để đảm bảo không trượt phát nào.

---

## 📖 HƯỚNG DẪN SỬ DỤNG CHI TIẾT

### 1. Yêu Cầu Cấu Hình Máy
- **RAM:** Tối thiểu 8GB (Khuyến nghị 16GB để mượt mà nhất).
- **Hệ điều hành:** Windows 10/11 hoặc macOS (Khuyên dùng dòng chip Apple M1, M2, M3...).
- **Ổ cứng:** Trống ít nhất 5GB (để lưu trữ AI Model và dữ liệu vector).
- **Mạng internet:** Chỉ cần mạng cho **lần chạy đầu tiên** để tải AI (Khoảng 2GB). Sau đó có thể tắt mạng chạy Offline hoàn toàn.

### 2. Cài Đặt & Khởi Động (Chỉ với 1 cú click)

**Đối với người dùng Mac (macOS):**
1. Giải nén/Tải thư mục dự án này về máy.
2. Tìm file có tên `run_mac.command` và **nhấp đúp chuột**.
3. Cửa sổ Terminal màu đen sẽ hiện lên. Nếu là lần đầu, hệ thống sẽ mất 1-2 phút để tải bộ não AI về máy.
4. Giao diện Web (Streamlit) sẽ tự động mở ra ở trình duyệt khi hệ thống sẵn sàng.

**Đối với người dùng Windows:**
1. Cài đặt Python 3.10+ (Nhớ tick vào ô *"Add Python to PATH"* lúc cài).
2. Giải nén/Tải thư mục dự án này về máy.
3. Tìm file có tên `run_windows.bat` và **nhấp đúp chuột**. 
4. Hệ thống sẽ tự cài cấu hình (nếu có Card NVIDIA sẽ tự kích hoạt nhân CUDA). Trình duyệt Web sẽ tự động mở lên.

---

### 3. Cách Thao Tác Trực Tiếp Trên Web

#### Bước 1: Tạo thẻ làm việc (Notebook)
- Ngay khi vào màn hình chính, gõ tên cho Thẻ (Ví dụ: *Luật Kinh Tế* hoặc *Giáo trình AI*) và ấn **+ Tạo Thẻ Mới**.
- Hệ thống hỗ trợ nhiều Thẻ (Notebook) độc lập. Dữ liệu Thẻ này không bị lẫn vào Thẻ kia.

#### Bước 2: Tải tài liệu lên
- Bấm vào tên Thẻ bạn vừa tạo.
- Ở cột menu bên tay trái, tìm khu vực **Nguồn (Tài liệu đã nạp)**.
- Kéo thả file PDF, DOCX, hoặc PPTX vào ô tải lên. Hệ thống sẽ mất vài giây để đọc, cắt nhỏ và phân tích nội dung lưu vào não bộ.

#### Bước 3: Tương tác với tài liệu
Ở giữa màn hình có 4 tab tính năng chính:

1. **💬 Hỏi đáp (Chat):**
   - Đặt bất kỳ câu hỏi nào liên quan đến tài liệu.
   - AI sẽ mất khoảng 4-8 giây để "đọc tài liệu" (xoay vòng tròn) và sau đó sẽ gõ chữ trả lời cực nhanh. Cuối câu trả lời sẽ có trích dẫn nguồn cụ thể (Trích từ file nào).
   
2. **📝 Tóm tắt:**
   - Ấn một nút, AI sẽ tự động đọc lướt toàn bộ tài liệu bạn đã tải lên, tóm tắt các ý chính và gạch đầu dòng những điểm quan trọng nhất.

3. **🧠 Trắc nghiệm (Quiz):**
   - AI sẽ tự động soi tài liệu và tạo ra 1 bộ câu hỏi trắc nghiệm A-B-C-D. Bạn có thể tự test kiến thức của mình và xem đáp án giải thích ngay bên dưới.

4. **⚡ Flashcards:**
   - Tạo ra các thẻ lật (Mặt trước câu hỏi - Mặt sau khái niệm) để bạn học thuộc lòng từ vựng hoặc khái niệm nhanh chóng.

---

### 4. Xử Lý Lỗi Thường Gặp (Troubleshooting)

- **Lỗi Terminal báo "Connection refused" / "Lỗi từ Backend":** 
  Do bạn lỡ tắt cửa sổ Terminal màu đen (cái cửa sổ đang gánh cái Backend của AI). Đừng bao giờ tắt nó khi đang xài web! Để sửa, hãy đóng web đi và nhấp đúp chạy lại file `run_mac.command` / `run_windows.bat`.
  
- **Trả lời có vẻ hơi chậm?**
  Mô hình AI này là 3 Tỷ tham số, nên quá trình "tiêu hoá" hàng nghìn chữ trong tài liệu ở 3-5 giây đầu tiên sẽ khá nặng. Hãy kiên nhẫn đợi 1 chút, khi nó đã suy nghĩ xong thì tốc độ nhả chữ sẽ rất nhanh. Trên Windows, nếu có Card NVIDIA, tốc độ sẽ khủng khiếp hơn nhiều.
  
- **Trình duyệt không tự mở?**
  Bạn hãy mở Chrome/Safari và tự gõ đường dẫn: `http://localhost:8501`.

---

## 🏗️ Kiến Trúc Hệ Thống (Dành cho Developer)

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

Bạn có thể thay đổi cách hệ thống hoạt động thông qua file `.env` ẩn:
- `RAG_LLM_TEMPERATURE`: Khuyên dùng 0.4 - 0.6.
- `RAG_HYBRID_INITIAL_K` và `RAG_HYBRID_RERANK_K`: Số đoạn văn lấy ra, giảm xuống sẽ đẩy nhanh tốc độ đọc.

---
*Dự án tối ưu hóa trải nghiệm Local AI 1-Click.*
