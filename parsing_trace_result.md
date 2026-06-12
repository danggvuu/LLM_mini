# TRUY VẾT QUÁ TRÌNH GẮN METADATA CHO FILE PDF
File gốc: first_page_only.pdf
Mã định danh sinh ra (doc_id): f6b95ddb72dfe25b

--- GIAI ĐOẠN 1 & 2: MarkItDown + MarkdownHeaderTextSplitter ---
Số lượng túi (chunks) sau GĐ 1 & 2: 1

**Túi 1:**
`json
{
  "document_id": "f6b95ddb72dfe25b",
  "filename": "first_page_only.pdf",
  "source": "D:\\LLM_mini\\data\\first_page_only.pdf",
  "page": 1,
  "section": null
}
`
**Nội dung:**
`	ext
AI VIET NAM – AI COURSE 2025
Project: Building a Simple
NotebookLM  
Dương Trường Bình Tô Phát Đạt Dương Đình Thắng Đinh Quang Vinh  
I. Dẫn nhập  
Các mô hình ngôn ngữ lớn (LLM) đã và đang được ứng dụng rộng rãi trong học tập, nghiên cứu
và khai thác tri thức từ tài liệu. Tuy nhiên, khi áp dụng vào các bài toán giáo dục, tính chính
xác, khả năng kiểm chứng và mức độ bám sát tài liệu nguồn là những yêu cầu rất quan trọng.
Nếu chỉ dựa vào tri thức có sẵn trong mô hình, hệ thống có thể sinh ra thông tin sai lệch hoặc
không có căn cứ, thường được gọi là hiện tượng “ảo giác” hay còn gọi là hallucination.  
Hình 1: Minh hoạ tổng quan dự án cùng các chức năng chính.  
Project Building a Simple NotebookLM được xây dựng nhằm mô phỏng một hệ thống hỗ trợ
học tập dựa trên tài liệu cá nhân. Thay vì để LLM trả lời hoàn toàn từ tri thức nội tại, hệ thống
sử dụng kiến trúc Retrieval-Augmented Generation (RAG) để truy xuất các đoạn nội dung liên
quan từ tài liệu đã được nạp trước, sau đó đưa các ngữ cảnh này vào prompt để sinh phản hồi.
Cách tiếp cận này giúp câu trả lời có cơ sở rõ ràng hơn, giảm rủi ro hallucination và hỗ trợ người
học kiểm tra lại nguồn thông tin.  
1  
UserPersonal DocumentsQueriesWhat is RAG?Summarize Create quizLearning SystemResponseCreate flashcard
`

--- GIAI ĐOẠN 3: Đóng gói với build_chunks ---

Số lượng túi (chunks) cuối cùng sau GĐ 3: 2

**Túi cuối cùng 1:**
`json
{
  "document_id": "f6b95ddb72dfe25b",
  "notebook_id": "notebook_test_123",
  "filename": "first_page_only.pdf",
  "source": "D:\\LLM_mini\\data\\first_page_only.pdf",
  "page": 1,
  "chunk_id": "f6b95ddb72dfe25b:1:0",
  "section": null
}
`
**Nội dung:**
`	ext
AI VIET NAM – AI COURSE 2025
Project: Building a Simple
NotebookLM  
Dương Trường Bình Tô Phát Đạt Dương Đình Thắng Đinh Quang Vinh  
I. Dẫn nhập  
Các mô hình ngôn ngữ lớn (LLM) đã và đang được ứng dụng rộng rãi trong học tập, nghiên cứu
và khai thác tri thức từ tài liệu. Tuy nhiên, khi áp dụng vào... [CẮT BỚT CHO GỌN]
`

**Túi cuối cùng 2:**
`json
{
  "document_id": "f6b95ddb72dfe25b",
  "notebook_id": "notebook_test_123",
  "filename": "first_page_only.pdf",
  "source": "D:\\LLM_mini\\data\\first_page_only.pdf",
  "page": 1,
  "chunk_id": "f6b95ddb72dfe25b:1:1",
  "section": null
}
`
**Nội dung:**
`	ext
học tập dựa trên tài liệu cá nhân. Thay vì để LLM trả lời hoàn toàn từ tri thức nội tại, hệ thống
sử dụng kiến trúc Retrieval-Augmented Generation (RAG) để truy xuất các đoạn nội dung liên
quan từ tài liệu đã được nạp trước, sau đó đưa các ngữ cảnh này vào prompt để sinh phản hồi.
Cách tiếp cận này ... [CẮT BỚT CHO GỌN]
`