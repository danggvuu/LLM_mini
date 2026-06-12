"""
Streamlit Web UI — Tầng Giao diện Multi-Workspace (Notebooks)
Mô phỏng trải nghiệm Google NotebookLM.
"""
import streamlit as st
import httpx
import json
import uuid
import sys
import os

# Đảm bảo Python nhận diện được thư mục gốc của dự án để import 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.config import settings
from src.interfaces.styles import GLOBAL_CSS

_API = settings.api_url

def _get_session_id():
    """Get or create a persistent session ID for this browser session."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    return st.session_state.session_id

def _api(method: str, path: str, **kwargs):
    try:
        res = httpx.request(method, f"{_API}{path}", timeout=180.0, **kwargs)
        if res.status_code >= 400:
            try:
                detail = res.json().get("detail", res.text)
            except Exception:
                detail = res.text

            if "API key required" in detail or "API_KEY" in detail or "API key not valid" in detail:
                st.error("🔑 **Lỗi cấu hình API Key:** Vui lòng kiểm tra file `.env`.")
            else:
                st.error(f"❌ **Lỗi từ Backend:** {detail}")
            return None
        return res.json()
    except Exception as e:
        st.error(f"Lỗi kết nối đến API backend: {e}")
        return None

def _api_stream(path: str, payload: dict):
    """Call streaming API and yield text chunks."""
    try:
        with httpx.stream("POST", f"{_API}{path}", json=payload, timeout=180.0) as response:
            if response.status_code != 200:
                response.read()
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", response.text)
                except Exception:
                    detail = response.text
                yield f"\n\n⚠️ Lỗi hệ thống ({response.status_code}): {detail}"
                return

            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "text" in data:
                        yield data["text"]
                    if data.get("done"):
                        break
    except Exception as e:
        yield f"\n\n⚠️ Lỗi kết nối đến Backend: {e}"

# -----------------------------------------------------------------------------
# Trạng thái hệ thống (State Machine)
# -----------------------------------------------------------------------------
# pages: "landing", "dashboard", "notebook"

if "page" not in st.session_state:
    st.session_state.page = "landing"
if "notebook_id" not in st.session_state:
    st.session_state.notebook_id = None
if "notebook_name" not in st.session_state:
    st.session_state.notebook_name = None

def navigate_to(page: str, notebook_id: str = None, notebook_name: str = None):
    st.session_state.page = page
    if notebook_id:
        st.session_state.notebook_id = notebook_id
    if notebook_name:
        st.session_state.notebook_name = notebook_name
    st.rerun()

# -----------------------------------------------------------------------------
# Trang 1: Landing Page
# -----------------------------------------------------------------------------
def render_landing():
    st.markdown("<div style='text-align:center; padding-top: 100px;'>", unsafe_allow_html=True)
    st.markdown("<h1 style='font-size: 4rem; font-family: Space Grotesk; color: #818cf8;'>NotebookLM</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.2rem; color: #94a3b8;'>Hệ thống RAG hỗ trợ học tập và nghiên cứu thông minh của riêng bạn.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Dùng thử NotebookLM", use_container_width=False, type="primary"):
        navigate_to("dashboard")
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Trang 2: Dashboard (Danh sách Thẻ / Notebooks)
# -----------------------------------------------------------------------------
def render_dashboard():
    st.markdown("<h1 style='font-family: Space Grotesk; color: #818cf8;'>📓 Thẻ của tôi (Notebooks)</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Tạo thẻ mới hoặc chọn một thẻ đã có để tiếp tục làm việc.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_name = st.text_input("Tên Thẻ Mới", placeholder="Nhập tên thẻ... (VD: Lịch sử, AI Research...)")
    
    st.markdown("**Chọn AI Backend cho thẻ này:**")
    provider_options = {
        "🖥️ Universal Local AI (Riêng tư, 100% tự động tương thích mọi phần cứng)": "hf_local",
        "🌐 Gemini API (Nhanh, cần API Key — ⚠️ không dùng với data riêng tư)": "gemini"
    }
    selected_provider_label = st.selectbox(
        "LLM Backend",
        list(provider_options.keys()),
        label_visibility="collapsed",
    )
    selected_provider = provider_options[selected_provider_label]
    if selected_provider == "gemini":
        st.warning("⚠️ **Lưu ý:** Gemini API sẽ gửi nội dung tài liệu của bạn lên máy chủ Google. Không nên dùng với dữ liệu riêng tư/nhạy cảm.")

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Tạo Thẻ Mới", use_container_width=True):
            if new_name.strip():
                with st.spinner("Đang tạo thẻ..."):
                    res = _api("POST", "/notebooks", json={"name": new_name.strip(), "llm_provider": selected_provider})
                    if res:
                        navigate_to("notebook", res["id"], res["name"])
            else:
                st.warning("Vui lòng nhập tên thẻ.")

    st.markdown("---")
    
    notebooks = _api("GET", "/notebooks")
    if not notebooks:
        st.info("Bạn chưa có Thẻ nào. Hãy tạo Thẻ mới ở trên.")
        return

    # Hiển thị dạng Grid
    cols = st.columns(3)
    for idx, nb in enumerate(notebooks):
        with cols[idx % 3]:
            st.markdown(f"<div class='glass-card' style='height: 150px; cursor: pointer;'>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin-bottom:0;'>{nb['name']}</h3>", unsafe_allow_html=True)
            st.markdown(f"<p style='font-size: 0.8rem; color: #94a3b8;'>{len(nb['documents'])} tài liệu</p>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Mở 📂", key=f"open_{nb['id']}", use_container_width=True):
                    with st.spinner("Đang mở thẻ..."):
                        navigate_to("notebook", nb["id"], nb["name"])
            with c2:
                if st.button("Xóa 🗑️", key=f"del_{nb['id']}", use_container_width=True):
                    _api("DELETE", f"/notebooks/{nb['id']}")
                    st.rerun()
            # Show provider badge
            provider_badge = {
                "gemini": "🌐 Gemini API",
                "hf_local": "🖥️ Local HF",
                "vllm": "⚡ vLLM",
            }.get(nb.get("llm_provider", "gemini"), "🌐 Gemini API")
            st.caption(f"AI: {provider_badge}")
            st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Trang 3: Notebook View (Trong một thẻ cụ thể)
# -----------------------------------------------------------------------------
def _sidebar_notebook(notebook_id: str, notebook_name: str):
    if st.sidebar.button("⬅️ Trở về Dashboard"):
        navigate_to("dashboard")
        
    st.sidebar.markdown(f"<h2 style='font-family:Space Grotesk; font-weight:700; color:#818cf8;'>📓 {notebook_name}</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # Upload
    uploaded_file = st.sidebar.file_uploader(
        "Kéo thả tài liệu vào đây (Tự động nạp)",
        type=["pdf", "docx", "pptx", "xlsx", "csv", "html", "md", "txt", "jpg", "jpeg", "png"],
    )

    # Fetch notebook info to check LLM provider
    nb_list = _api("GET", "/notebooks")
    nb_data = next((n for n in (nb_list or []) if n["id"] == notebook_id), None)
    is_gemini = nb_data and nb_data.get("llm_provider") == "gemini"

    # Privacy selection
    if is_gemini:
        privacy_choice = st.sidebar.radio(
            "Nhãn bảo mật tài liệu:",
            ["🌍 Công khai (Public)", "🔒 Riêng tư (Private)"],
            index=0,
            help="Private: cảnh báo nếu notebook dùng Gemini API (gửi data lên cloud)",
        )
        privacy = "private" if "Private" in privacy_choice else "public"
    else:
        st.sidebar.success("🔒 **100% Local AI**\nDữ liệu không bao giờ rời khỏi máy tính.")
        privacy = "private"  # Always private for local models

    if uploaded_file is not None:
        if st.session_state.get("last_uploaded_file_id") != uploaded_file.file_id:
            st.session_state["last_uploaded_file_id"] = uploaded_file.file_id

            if privacy == "private" and is_gemini:
                st.sidebar.warning(
                    "⚠️ **Cảnh báo Bảo mật:** Thẻ này đang dùng **Gemini API** (cloud).\n\n"
                    "Tài liệu **Riêng tư** của bạn sẽ được gửi đến máy chủ Google để xử lý.\n\n"
                    "Vui lòng chọn một trong các tuỳ chọn bên dưới:"
                )
                confirmed = st.sidebar.checkbox("✅ Tôi hiểu rủi ro và vẫn muốn tiếp tục với Gemini API", key="privacy_confirm")

                if not confirmed:
                    st.sidebar.markdown("**Hoặc chuyển sang Local AI để bảo vệ dữ liệu:**")
                    col_a, col_b = st.sidebar.columns(2)
                    with col_a:
                        if st.button("🖥️ Dùng Local HF", key="switch_hf", use_container_width=True):
                            _api("POST", f"/notebooks/{notebook_id}/provider", json={"llm_provider": "hf_local"})
                            st.session_state["last_uploaded_file_id"] = None  # reset để upload lại
                            st.sidebar.success("✅ Đã chuyển sang Local HF! Hãy tải file lại.")
                            st.rerun()
                    with col_b:
                        if st.button("⚡ Dùng vLLM", key="switch_vllm", use_container_width=True):
                            _api("POST", f"/notebooks/{notebook_id}/provider", json={"llm_provider": "vllm"})
                            st.session_state["last_uploaded_file_id"] = None
                            st.sidebar.success("✅ Đã chuyển sang vLLM! Hãy tải file lại.")
                            st.rerun()
                    st.sidebar.stop()

            with st.spinner("Đang xử lý và nhúng Vector, vui lòng đợi..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/octet-stream")}
                res = _api("POST", f"/upload/{notebook_id}", files=files, params={"privacy": privacy})
                if res:
                    task_id = res.get("task_id", "")
                    if task_id:
                        import time
                        while True:
                            status = _api("GET", f"/upload/status/{task_id}")
                            if not status or status.get("status") in ("done", "error"):
                                break
                            time.sleep(1.0)
                        
                        if status and status.get("status") == "done":
                            st.sidebar.success(f"✅ Đã nạp xong: {status.get('filename')}")
                        elif status and status.get("status") == "error":
                            st.sidebar.error(f"❌ Lỗi: {status.get('error_message')}")
                        
                        st.rerun()



    st.sidebar.markdown("---")
    
    # Document List
    st.sidebar.markdown("### Nguồn (Tài liệu đã nạp)")
    docs = _api("GET", f"/notebooks/{notebook_id}/documents")
    
    if not docs:
        st.sidebar.warning("Thẻ này chưa có tài liệu. Vui lòng tải lên.")
        return None, None

    for d in docs:
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            st.markdown(f"📄 **{d['filename']}**", unsafe_allow_html=True)
        with col2:
            if st.button("🗑️", key=f"del_doc_{d['filename']}", help="Xóa tài liệu"):
                _api("DELETE", f"/notebooks/{notebook_id}/documents/{d['filename']}")
                st.rerun()
                
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Bộ lọc tìm kiếm")
    doc_options = ["Toàn bộ tài liệu (Corpus)"] + [d["filename"] for d in docs]
    selected_doc = st.sidebar.selectbox("Chỉ định tài liệu", doc_options)
    doc_target = None if selected_doc == "Toàn bộ tài liệu (Corpus)" else selected_doc
    
    page_filter = None
    if doc_target:
        # We don't have page count in the simplified Notebook metadata yet, so fallback to simple text input or no filter
        st.sidebar.caption(f"Lọc theo tài liệu: {doc_target}")

    return doc_target, page_filter


@st.fragment
def _tab_chat(notebook_id, selected_doc, page_filter):
    st.markdown("<h2 style='font-family:Space Grotesk; font-weight:700;'>💬 Hỏi đáp với tài liệu</h2>", unsafe_allow_html=True)
    
    session_key = f"messages_{notebook_id}"
    if session_key not in st.session_state:
        nb_list = _api("GET", "/notebooks")
        nb_data = next((n for n in (nb_list or []) if n["id"] == notebook_id), None)
        st.session_state[session_key] = nb_data.get("messages", []) if nb_data else []

    use_streaming = st.checkbox("🚀 Streaming mode (SSE)", value=True)

    if st.button("Xóa lịch sử chat", type="secondary"):
        st.session_state[session_key] = []
        _api("DELETE", f"/notebooks/{notebook_id}/messages")
        st.rerun()

    for msg in st.session_state[session_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("citations"):
                with st.expander("📚 Nguồn trích dẫn (Citations)"):
                    for c in msg["citations"]:
                        st.markdown(f"<span class='source-tag'>{c['source_marker']}</span> <b>{c['filename']}</b> (Trang {c['page']})", unsafe_allow_html=True)

    query = st.chat_input("Nhập câu hỏi của bạn về tài liệu ở đây...")
    if query:
        with st.chat_message("user"):
            st.markdown(query)
        msg_user = {"role": "user", "content": query}
        st.session_state[session_key].append(msg_user)
        _api("POST", f"/notebooks/{notebook_id}/messages", json=msg_user)

        filters = {"notebook_id": notebook_id}
        if page_filter:
            filters["page"] = page_filter
        if selected_doc:
            filters["filename"] = selected_doc

        with st.chat_message("assistant"):
            if use_streaming:
                payload = {
                    "question": query,
                    "k": settings.top_k,
                    "filters": filters,
                    "session_id": _get_session_id(),
                }
                response_placeholder = st.empty()
                collected = []
                for chunk in _api_stream("/ask/stream", payload):
                    collected.append(chunk)
                    response_placeholder.markdown("".join(collected))

                full_answer = "".join(collected)
                msg_asst = {
                    "role": "assistant",
                    "content": full_answer,
                    "citations": [],
                }
                st.session_state[session_key].append(msg_asst)
                _api("POST", f"/notebooks/{notebook_id}/messages", json=msg_asst)
            else:
                with st.spinner("Đang suy nghĩ và trích xuất nguồn..."):
                    payload = {
                        "question": query,
                        "k": settings.top_k,
                        "filters": filters,
                        "session_id": _get_session_id(),
                    }
                    res = _api("POST", "/ask", json=payload)
                    if res:
                        st.markdown(res["answer"])
                        if res["citations"]:
                            with st.expander("📚 Nguồn trích dẫn (Citations)"):
                                for c in res["citations"]:
                                    st.markdown(f"<span class='source-tag'>{c['source_marker']}</span> <b>{c['filename']}</b> (Trang {c['page']})", unsafe_allow_html=True)

                        msg_asst = {
                            "role": "assistant",
                            "content": res["answer"],
                            "citations": res["citations"]
                        }
                        st.session_state[session_key].append(msg_asst)
                        _api("POST", f"/notebooks/{notebook_id}/messages", json=msg_asst)


@st.fragment
def _tab_summary(notebook_id, selected_doc, page_filter):
    doc_key = selected_doc or "all"
    st.markdown("<h2 style='font-family:Space Grotesk; font-weight:700;'>📝 Hướng dẫn học tập (Study Guide)</h2>", unsafe_allow_html=True)
    summary_focus = st.text_input("Trọng tâm tóm tắt (Để trống để tóm tắt toàn bộ tài liệu)", placeholder="Ví dụ: các khái niệm cốt lõi...")
    
    # Auto-load from NotebookStore
    if "active_summary" not in st.session_state:
        nb_res = _api("GET", f"/notebooks/{notebook_id}")
        if nb_res and "learning_data" in nb_res:
            saved_data = nb_res["learning_data"].get("summary", {}).get(doc_key)
            if saved_data:
                st.session_state["active_summary"] = saved_data

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("Tạo Hướng dẫn"):
            with st.spinner("Đang phân tích..."):
                filters = {"notebook_id": notebook_id}
                if page_filter:
                    filters["page"] = page_filter

                payload = {
                    "document": selected_doc,
                    "query": summary_focus if summary_focus.strip() else None,
                    "filters": filters
                }
                res = _api("POST", "/summarize", json=payload)
                if res:
                    st.session_state["active_summary"] = res
    with col_btn2:
        if "active_summary" in st.session_state:
            if st.button("🗑️ Xóa bài tập này", type="primary"):
                _api("DELETE", f"/notebooks/{notebook_id}/learning/summary?document={doc_key}")
                del st.session_state["active_summary"]
                st.rerun()

    if "active_summary" in st.session_state:
        sum_data = st.session_state["active_summary"]
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:#818cf8;'>✨ Bản tóm tắt chính</h3>", unsafe_allow_html=True)
        st.markdown(sum_data["summary"])
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:#818cf8;'>📌 Các ý chính nổi bật</h3>", unsafe_allow_html=True)
        for kp in sum_data["key_points"]:
            st.markdown(f"- {kp}")
        st.markdown("</div>", unsafe_allow_html=True)


@st.fragment
def _tab_quiz(notebook_id, selected_doc, page_filter):
    doc_key = selected_doc or "all"
    st.markdown("<h2 style='font-family:Space Grotesk; font-weight:700;'>📝 Trắc nghiệm</h2>", unsafe_allow_html=True)
    count = st.slider("Số lượng câu", 3, 15, 5)

    # Auto-load from NotebookStore
    if "active_quiz" not in st.session_state:
        nb_res = _api("GET", f"/notebooks/{notebook_id}")
        if nb_res and "learning_data" in nb_res:
            saved_data = nb_res["learning_data"].get("quiz", {}).get(doc_key)
            if saved_data:
                st.session_state["active_quiz"] = saved_data
                st.session_state["quiz_answers"] = {}
                st.session_state["quiz_submitted"] = False

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("Tạo bộ câu hỏi"):
            with st.spinner("Đang thiết lập..."):
                filters = {"notebook_id": notebook_id}
                if page_filter:
                    filters["page"] = page_filter

                payload = {"document": selected_doc, "count": count, "filters": filters}
                res = _api("POST", "/quiz", json=payload)
                if res and res.get("items"):
                    st.session_state["active_quiz"] = res
                    st.session_state["quiz_answers"] = {}
                    st.session_state["quiz_submitted"] = False
    
    with col_btn2:
        if "active_quiz" in st.session_state:
            if st.button("🗑️ Xóa bài tập này", type="primary", key="btn_del_quiz"):
                _api("DELETE", f"/notebooks/{notebook_id}/learning/quiz?document={doc_key}")
                del st.session_state["active_quiz"]
                if "quiz_answers" in st.session_state: del st.session_state["quiz_answers"]
                if "quiz_submitted" in st.session_state: del st.session_state["quiz_submitted"]
                st.rerun()

    if "active_quiz" in st.session_state:
        quiz_data = st.session_state["active_quiz"]
        for idx, item in enumerate(quiz_data["items"]):
            st.markdown(f"<div style='font-weight:600; margin-top:20px;'>Câu {idx+1}: {item['question']}</div>", unsafe_allow_html=True)
            key = f"q_{idx}"
            selected_option = st.radio("Chọn đáp án:", item["options"], key=key, index=None, disabled=st.session_state["quiz_submitted"])
            if selected_option:
                st.session_state["quiz_answers"][idx] = item["options"].index(selected_option)

            if st.session_state["quiz_submitted"]:
                user_ans = st.session_state["quiz_answers"].get(idx)
                correct_ans = item["correct_index"]
                if user_ans == correct_ans:
                    st.success("✅ Chính xác!")
                else:
                    st.error(f"❌ Sai! Đáp án đúng: {item['options'][correct_ans]}")
                st.info(f"Giải thích: {item['explanation']}")

        if not st.session_state["quiz_submitted"]:
            if st.button("Nộp bài"):
                st.session_state["quiz_submitted"] = True
                st.rerun()


@st.fragment
def _tab_flashcards(notebook_id, selected_doc, page_filter):
    doc_key = selected_doc or "all"
    st.markdown("<h2 style='font-family:Space Grotesk; font-weight:700;'>🗂️ Thẻ ghi nhớ (Flashcards)</h2>", unsafe_allow_html=True)
    count = st.slider("Số lượng thẻ", 5, 20, 8)

    # Auto-load from NotebookStore
    if "active_flashcards" not in st.session_state:
        nb_res = _api("GET", f"/notebooks/{notebook_id}")
        if nb_res and "learning_data" in nb_res:
            saved_data = nb_res["learning_data"].get("flashcards", {}).get(doc_key)
            if saved_data:
                st.session_state["active_flashcards"] = saved_data
                st.session_state["flashcard_index"] = 0
                st.session_state["flashcard_flipped"] = False

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("Tạo thẻ"):
            with st.spinner("Đang tạo thẻ..."):
                filters = {"notebook_id": notebook_id}
                if page_filter:
                    filters["page"] = page_filter

                payload = {"document": selected_doc, "count": count, "filters": filters}
                res = _api("POST", "/flashcards", json=payload)
                if res and res.get("cards"):
                    st.session_state["active_flashcards"] = res
                    st.session_state["flashcard_index"] = 0
                    st.session_state["flashcard_flipped"] = False
                    
    with col_btn2:
        if "active_flashcards" in st.session_state:
            if st.button("🗑️ Xóa bài tập này", type="primary", key="btn_del_fc"):
                _api("DELETE", f"/notebooks/{notebook_id}/learning/flashcards?document={doc_key}")
                del st.session_state["active_flashcards"]
                if "flashcard_index" in st.session_state: del st.session_state["flashcard_index"]
                if "flashcard_flipped" in st.session_state: del st.session_state["flashcard_flipped"]
                st.rerun()

    if "active_flashcards" in st.session_state:
        fc_data = st.session_state["active_flashcards"]
        idx = st.session_state["flashcard_index"]
        card = fc_data["cards"][idx]

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀️ Trước", disabled=(idx == 0), use_container_width=True):
                st.session_state["flashcard_index"] -= 1
                st.session_state["flashcard_flipped"] = False
                st.rerun()
        with col2:
            st.markdown(f"<div style='text-align:center;'>Thẻ {idx+1} / {len(fc_data['cards'])}</div>", unsafe_allow_html=True)
        with col3:
            if st.button("Sau ▶️", disabled=(idx == len(fc_data["cards"]) - 1), use_container_width=True):
                st.session_state["flashcard_index"] += 1
                st.session_state["flashcard_flipped"] = False
                st.rerun()

        st.markdown("<div class='flashcard-container'>", unsafe_allow_html=True)
        if not st.session_state["flashcard_flipped"]:
            st.markdown(f"<div class='flashcard-content'>{card['front']}</div>", unsafe_allow_html=True)
            if st.button("🔄 Lật mặt sau", use_container_width=True):
                st.session_state["flashcard_flipped"] = True
                st.rerun()
        else:
            st.markdown(f"<div class='flashcard-content' style='color:#a5b4fc;'>{card['back']}</div>", unsafe_allow_html=True)
            if st.button("🔄 Lật mặt trước", use_container_width=True):
                st.session_state["flashcard_flipped"] = False
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def run():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    page = st.session_state.page
    
    if page == "landing":
        render_landing()
    elif page == "dashboard":
        render_dashboard()
    elif page == "notebook":
        nb_id = st.session_state.notebook_id
        nb_name = st.session_state.notebook_name
        
        nb_res = _api("GET", f"/notebooks/{nb_id}")
        
        selected_doc, page_filter = _sidebar_notebook(nb_id, nb_name)
        
        # Chặn xử lý nội dung chính nếu có tài liệu đang được nạp (hoặc bị kẹt)
        is_processing = False
        if nb_res and "documents" in nb_res:
            for doc in nb_res["documents"]:
                if doc.get("chunks_indexed", 0) == 0:
                    is_processing = True
                    break
                    
        if is_processing:
            st.warning("⏳ Hệ thống đang nạp tài liệu. Nếu bị kẹt quá lâu do sập nguồn, bạn có thể ấn nút 🗑️ ở bên trái để xóa tài liệu bị kẹt.")
            import time
            time.sleep(3)
            st.rerun()
            return
        
        # Thêm cảnh báo nếu tạo quá nhiều tài liệu học tập
        if nb_res and "learning_data" in nb_res:
            total_materials = sum(len(docs) for docs in nb_res["learning_data"].values())
            if total_materials > 10:
                st.warning(f"⚠️ Cảnh báo: Bạn đang lưu trữ {total_materials} bài tập trong thẻ này. Hãy xem xét xóa bớt những tài liệu học xong rồi hoặc không học nữa để giải phóng không gian ổ cứng!")

        tabs = st.tabs(["💬 Hỏi đáp", "📝 Tóm tắt", "🧠 Trắc nghiệm", "🗂️ Flashcards"])
        with tabs[0]:
            _tab_chat(nb_id, selected_doc, page_filter)
        with tabs[1]:
            _tab_summary(nb_id, selected_doc, page_filter)
        with tabs[2]:
            _tab_quiz(nb_id, selected_doc, page_filter)
        with tabs[3]:
            _tab_flashcards(nb_id, selected_doc, page_filter)

if __name__ == "__main__":
    run()
