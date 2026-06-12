import re
import sys

try:
    with open('d:/LLM_mini/pipeline_viewer.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # Add CSS for why-card
    css_insert = '''
        .why-card {
            background: rgba(245,158,11,0.08); border-left: 3px solid rgba(245,158,11,0.6);
            padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 13.5px; color: #fcd34d; line-height: 1.6;
        }
        .why-card .why-title { font-weight: 600; margin-bottom: 4px; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; opacity: 0.8; }
'''
    if '.why-card {' not in html:
        html = html.replace('.func-list { list-style: none;', css_insert.strip() + '\n        .func-list { list-style: none;')

    # Update JS modal render
    js_update = '''
    if (info.why) {
        html += `<div class="why-card"><div class="why-title">Tại sao cần làm nhiệm vụ này?</div>${info.why}</div>`;
    }

    if (info.details && info.details.length > 0) {
'''
    if 'info.why' not in html:
        html = html.replace('if (info.details && info.details.length > 0) {', js_update)

    whys = {
        'User': 'Người dùng là điểm xuất phát, xác định yêu cầu hệ thống.',
        'Streamlit': 'Cung cấp giao diện trực quan, thân thiện cho end-user thao tác mà không cần biết code.',
        'FastAPI': 'Tách biệt logic backend và frontend, hỗ trợ xử lý luồng (streaming) và tác vụ nặng hiệu quả.',
        'CLI': 'Tiện lợi cho dev/admin thực thi các lệnh quản trị, cronjob, tự động hóa từ terminal.',
        'Redis': 'Cache giúp trả lời các câu hỏi trùng lặp trong <0.1s, tiết kiệm API cost và tăng tốc đáng kể.',
        'Session': 'Cung cấp ngữ cảnh ngắn hạn (history) để LLM hiểu đại từ (nó, đó) từ câu trước.',
        'Prometheus': 'Giám sát hiệu năng hệ thống (latency, load) để phát hiện sớm các vấn đề bottleneck.',
        'LangSmith': 'Trace chi tiết luồng xử lý RAG để debug LLM prompt và pipeline lỗi ở đâu.',
        'Worker': 'Giúp API không bị nghẽn (timeout) khi người dùng upload file quá lớn (ví dụ: PDF 500 trang).',
        'Worker2': 'Giúp API không bị nghẽn (timeout) khi người dùng upload file quá lớn (ví dụ: PDF 500 trang).',
        'Parser': 'LLM chỉ hiểu văn bản thuần túy (text). Cần trích xuất nội dung từ định dạng PDF, DOCX, ảnh.',
        'Parse': 'LLM chỉ hiểu văn bản thuần túy (text). Cần trích xuất nội dung từ định dạng PDF, DOCX, ảnh.',
        'Chunker': 'Văn bản quá dài sẽ tràn Context Window của LLM, hoặc làm giảm độ chính xác. Chunk nhỏ giúp target đúng thông tin.',
        'Chunk': 'Văn bản quá dài sẽ tràn Context Window của LLM, hoặc làm giảm độ chính xác.',
        'Embedder': 'Chuyển ngôn ngữ tự nhiên (tiếng Việt) thành vector số học đa chiều để máy tính hiểu ý nghĩa.',
        'Embed': 'Chuyển ngôn ngữ tự nhiên (tiếng Việt) thành vector số học đa chiều để máy tính hiểu ý nghĩa.',
        'Token': 'Trích xuất các từ khóa chính xác để hỗ trợ tìm kiếm BM25 (tránh sót tên riêng, mã số).',
        'Qdrant': 'Vector Database chuyên dụng để tìm nhanh các chunk có ngữ nghĩa tương đương câu hỏi.',
        'QStore': 'Vector Database chuyên dụng để tìm nhanh các chunk có ngữ nghĩa tương đương câu hỏi.',
        'BM25': 'Hệ thống keyword matching truyền thống. Bù đắp khuyết điểm của Vector (dễ trượt từ khóa chính xác).',
        'BStore': 'Lưu trữ inverted index tốc độ cao để tìm kiếm keyword.',
        'Router': 'Phân nhánh tối ưu: Q&A cần tìm kiếm dữ liệu cụ thể, Summary/Quiz cần lấy toàn bộ văn bản.',
        'Router2': 'Phân nhánh tối ưu: Q&A cần tìm kiếm dữ liệu cụ thể, Summary/Quiz cần lấy toàn bộ văn bản.',
        'HybridSearch': 'Kết hợp sức mạnh cả Vector và Keyword để không bỏ lọt mảnh thông tin nào.',
        'RRF': 'Thuật toán công bằng để gộp và sắp xếp kết quả từ cả 2 nguồn (Vector và BM25).',
        'Reranker': 'Tìm kiếm ban đầu nhanh nhưng thô. Cần AI chấm điểm lại chính xác hơn để cung cấp kết quả tinh sạch nhất cho LLM.',
        'Rerank': 'Tìm kiếm ban đầu nhanh nhưng thô. Cần AI chấm điểm lại chính xác hơn để cung cấp kết quả tinh sạch nhất cho LLM.',
        'Scroll': 'Tác vụ học tập (Tóm tắt, Quiz) yêu cầu nắm TOÀN BỘ kiến thức, không được phép bỏ sót data qua search.',
        'Scroll2': 'Tác vụ học tập (Tóm tắt, Quiz) yêu cầu nắm TOÀN BỘ kiến thức, không được phép bỏ sót data qua search.',
        'ContextBuilder': 'LLM cần context được đánh số [S1] [S2] để biết chính xác thông tin ở đâu và trích dẫn.',
        'CB': 'LLM cần context được đánh số [S1] [S2] để biết chính xác thông tin ở đâu và trích dẫn.',
        'Jinja': 'Tách biệt cấu trúc prompt khỏi code Python. Dễ sửa đổi, điều hướng LLM làm đúng nhiệm vụ.',
        'Template': 'Tách biệt cấu trúc prompt khỏi code Python. Dễ sửa đổi, điều hướng LLM làm đúng nhiệm vụ.',
        'MapReduce': 'LLM không thể đọc quá nhiều text cùng lúc. Phải cắt nhỏ (Map) tóm tắt, sau đó gộp lại (Reduce).',
        'LLMFactory': 'Linh hoạt chuyển đổi giữa API đám mây và Local AI tùy cấu hình tài nguyên của user.',
        'LLM2': 'Linh hoạt chuyển đổi giữa API đám mây và Local AI tùy cấu hình tài nguyên của user.',
        'Gemini': 'API Cloud LLM cực mạnh, cực nhanh cho trải nghiệm tốt nhất.',
        'HFLocal': 'Dành cho doanh nghiệp cần bảo mật 100% data, không truyền ra ngoài internet.',
        'vLLM': 'Tối ưu tốc độ xuất chữ (tokens/sec) cho local LLM, phục vụ đa luồng.',
        'GGUF': 'Giúp chạy LLM trực tiếp trên CPU hoặc máy yếu (low VRAM mode).',
        'StreamBatch': 'Gửi từng đoạn chữ nhỏ xuống trình duyệt để User đọc ngay lập tức, không bắt họ chờ lâu.',
        'Stream': 'Gửi từng đoạn chữ nhỏ xuống trình duyệt để User đọc ngay lập tức.',
        'Block': 'Trả JSON định dạng cứng dành cho hệ thống phân tích data (không phải cho text reader).',
        'Pydantic': 'Ép LLM trả về đúng schema JSON của Quiz/Flashcard, tự sửa và lọc lỗi sai định dạng.',
        'Upload': 'Đưa tài liệu thô vào hệ thống.',
        'API': 'Tiếp nhận HTTP request.',
        'Status': 'Giám sát trạng thái background.',
        'Q': 'Truyền đạt nhu cầu kiến thức của người dùng.',
        'CacheGet': 'Bỏ qua các bước tính toán RAG phức tạp nếu câu hỏi bị trùng.',
        'CacheHit': 'Trả lời siêu tốc, giảm tải hệ thống.',
        'SessionGet': 'Đảm bảo tính liên tục của đoạn hội thoại, LLM nhớ context.',
        'VSearch': 'Tìm theo ý nghĩa ẩn sâu của câu hỏi.',
        'KSearch': 'Tìm theo từ khoá chính xác trên văn bản.',
        'G': 'Cloud LLM siêu việt.', 'H': 'Local LLM on-premise.', 'V': 'Fast local inference.', 'GG': 'Low VRAM local inference.',
        'Save': 'Hoàn tất chu trình lưu vết (cache, metrics) để tối ưu lần sau.',
        'Req': 'Khởi chạy workflow học tập theo yêu cầu user.',
        'Resolve': 'Kiểm tra xem tác vụ có cần thu hẹp scope không.',
        'Check': 'Xác định chiến lược MapReduce tùy theo độ dài của dữ liệu nạp vào.',
        'Single': 'Xử lý gộp 1 lần vì độ dài phù hợp.',
        'Batch': 'Tách lô để vượt qua Context Window Limit của LLM.',
        'M1': 'Tóm tắt cục bộ phần đầu.', 'M2': 'Tóm tắt cục bộ đoạn giữa.', 'MN': 'Tóm tắt cục bộ đoạn cuối.',
        'Collect': 'Gom các ý tóm tắt nhỏ vào 1 prompt.',
        'Reduce': 'Tổng hợp thành bài tóm tắt toàn cục đầy đủ.',
        'QPrompt': 'Chỉ thị LLM xây dựng bộ Quiz từ chunk.',
        'QParse': 'Bóc tách payload an toàn phòng trường hợp LLM sinh mã Markdown thừa.',
        'QVal': 'Đảm bảo object chứa Quiz không bị rỗng/thiếu thuộc tính do ảo giác AI.',
        'FPrompt': 'Chỉ thị LLM xây dựng Flashcard từ chunk.',
        'FParse': 'Bóc tách payload an toàn.',
        'FVal': 'Đảm bảo object chứa Flashcard chuẩn Pydantic schema.',
        'Citations': 'Gắn metadata nguồn để web UI sinh footnote click được.',
        'Export': 'Hỗ trợ tải về đa format để ôn tập offline.',
        'A': 'Endpoint RAG.', 'B': 'Endpoint Learning.', 'C': 'Endpoint Upload.', 'D': 'Endpoint Feedback.',
        'C1': 'Thống kê mật độ sử dụng.', 'C2': 'Phát hiện chậm nghẽn server.', 'C3': 'Đánh giá độ hiệu quả của Semantic Cache.', 'C4': 'Đếm Cache Miss.', 'C5': 'Đếm số lượng chunk.', 'C6': 'Giám sát queue Worker.', 'C7': 'Thống kê mức độ hài lòng.',
        'T1S': 'Cung cấp trace log tổng thể cho 1 request RAG.', 'T2S': 'Mổ xẻ latency của từng node nhỏ bên trong pipeline.',
        'F1': 'Tiếp nhận user signal tốt xấu.', 'F2': 'Lưu database.', 'EP': 'Scrape metrics.'
    }

    for node_id, why_text in whys.items():
        if f'{node_id}: {{why:' not in html:
            pattern = f'{node_id}: {{'
            replacement = f'{node_id}: {{why: "{why_text}", '
            html = html.replace(pattern, replacement)

    # Pipeline A
    html = html.replace('Upload --> API --> Worker2 --> Parse --> Chunk', 'Upload -->|1| API -->|2| Worker2 -->|3| Parse -->|4| Chunk')
    html = html.replace('Chunk --> Embed --> QStore', 'Chunk -->|5| Embed -->|6| QStore')
    html = html.replace('Chunk --> Token --> BStore', 'Chunk -->|5| Token -->|6| BStore')
    html = html.replace('Worker2 -.-> Status', 'Worker2 -.->|Theo dõi| Status')

    # Pipeline B
    html = html.replace('Q --> CacheGet', 'Q -->|1| CacheGet')
    html = html.replace('CacheGet -->|"HIT"| CacheHit', 'CacheGet -->|2. HIT| CacheHit')
    html = html.replace('CacheGet -->|"MISS"| SessionGet --> Router2', 'CacheGet -->|2. MISS| SessionGet -->|3| Router2')
    html = html.replace('Router2 -->|"Query"| VSearch & KSearch', 'Router2 -->|4. HYBRID| VSearch & KSearch')
    html = html.replace('VSearch & KSearch --> RRF', 'VSearch & KSearch -->|5| RRF')
    html = html.replace('RRF --> Rerank --> CB', 'RRF -->|6| Rerank -->|7| CB')
    html = html.replace('Router2 -->|"Scroll"| CB', 'Router2 -->|4. SCROLL| CB')
    html = html.replace('CB --> Template --> LLM2', 'CB -->|8| Template -->|9| LLM2')
    html = html.replace('LLM2 --> G & H & V & GG', 'LLM2 -->|10| G & H & V & GG')
    html = html.replace('G & H & V & GG -->|"Stream"| StreamBatch --> FastAPI', 'G & H & V & GG -->|"11. Stream"| StreamBatch -->|12| FastAPI')
    html = html.replace('G & H & V & GG -->|"Block"| Pydantic --> FastAPI', 'G & H & V & GG -->|"11. Block"| Pydantic -->|12| FastAPI')
    html = html.replace('G & H & V & GG --> Stream & Block', 'G & H & V & GG -->|11| Stream & Block')
    html = html.replace('Stream & Block --> Save', 'Stream & Block -->|12| Save')

    # Pipeline C
    html = html.replace('Req --> Resolve --> Scroll2', 'Req -->|1| Resolve -->|2| Scroll2')
    html = html.replace('Scroll2 -->|"chunks[]"| Check', 'Scroll2 -->|3. chunks[]| Check')
    html = html.replace('Check -->|"Ngắn"| Single', 'Check -->|4. Ngắn| Single')
    html = html.replace('Check -->|"Dài"| Batch --> M1 & M2 & MN --> Collect --> Reduce', 'Check -->|4. Dài| Batch -->|5| M1 & M2 & MN -->|6| Collect -->|7| Reduce')
    html = html.replace('Single --> Citations', 'Single -->|8| Citations')
    html = html.replace('Reduce --> Citations', 'Reduce -->|8| Citations')
    html = html.replace('Scroll2 -->|"chunks[]"| QPrompt --> QParse --> QVal --> Citations', 'Scroll2 -->|3. chunks[]| QPrompt -->|4| QParse -->|5| QVal -->|6| Citations')
    html = html.replace('Scroll2 -->|"chunks[]"| FPrompt --> FParse --> FVal --> Citations', 'Scroll2 -->|3. chunks[]| FPrompt -->|4| FParse -->|5| FVal -->|6| Citations')
    html = html.replace('Citations --> Export', 'Citations -->|Cuối| Export')

    # Pipeline D
    html = html.replace('A & B --> C1 & C2', 'A & B -->|1| C1 & C2')
    html = html.replace('A --> C3 & C4', 'A -->|2| C3 & C4')
    html = html.replace('C --> C5 & C6', 'C -->|3| C5 & C6')
    html = html.replace('D --> C7', 'D -->|4| C7')
    html = html.replace('A & B -.-> T1S --> T2S', 'A & B -.->|Trace| T1S --> T2S')
    html = html.replace('D --> F1 --> F2', 'D -->|Feedback| F1 --> F2')

    with open('d:/LLM_mini/pipeline_viewer.html', 'w', encoding='utf-8') as f:
        f.write(html)
        
    print("DONE")
except Exception as e:
    print(e)
    sys.exit(1)
