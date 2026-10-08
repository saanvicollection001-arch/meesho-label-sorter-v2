import time
from io import BytesIO

import pandas as pd
import streamlit as st

from meesho_sorter import process_pdfs

st.set_page_config(
    page_title="Meesho Label Sorter",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_css():
    st.markdown(
        """
        <style>
        :root {
            --bg: #f7f8fc;
            --card: #ffffff;
            --text: #1e2457;
            --muted: #6f7798;
            --primary: #6f3dff;
            --primary2: #ff4fa3;
            --border: #e8eaf5;
            --success: #16a34a;
            --warning: #f59e0b;
        }
        .stApp {
            background: linear-gradient(180deg, #fbfbff 0%, #f6f7fc 100%);
            color: var(--text);
        }
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1380px;
        }
        h1, h2, h3, h4, h5, h6, p, span, label, div {
            color: var(--text);
        }
        .app-header {
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        .brand-wrap {
            display:flex;
            align-items:center;
            gap: 0.9rem;
        }
        .brand-icon {
            width:54px;
            height:54px;
            border-radius:16px;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:28px;
            background: linear-gradient(135deg, var(--primary2), var(--primary));
            color:#fff;
            box-shadow: 0 16px 32px rgba(111,61,255,0.18);
        }
        .brand-title {
            font-size: 2.1rem;
            line-height: 1.1;
            margin: 0;
            font-weight: 800;
            letter-spacing: -0.03em;
        }
        .brand-subtitle {
            margin: 0.28rem 0 0 0;
            color: var(--muted);
            font-size: 0.96rem;
        }
        .nav-pills {
            display:flex;
            gap:0.7rem;
            flex-wrap:wrap;
            justify-content:flex-end;
        }
        .pill {
            padding:0.7rem 1rem;
            border-radius: 999px;
            background:#fff;
            border:1px solid var(--border);
            color: var(--text);
            font-size: 0.93rem;
            font-weight:600;
            box-shadow: 0 8px 20px rgba(42, 52, 128, 0.04);
        }
        .pill.active {
            color:#fff;
            background: linear-gradient(135deg, var(--primary2), var(--primary));
            border:none;
        }
        .hero-card {
            background: linear-gradient(135deg, rgba(255,79,163,.12), rgba(111,61,255,.12));
            border:1px solid #efe7ff;
            border-radius:24px;
            padding: 1.7rem;
            box-shadow: 0 20px 50px rgba(76, 61, 181, 0.08);
            margin-top: 0.6rem;
            margin-bottom: 1rem;
        }
        .hero-grid {
            display:grid;
            grid-template-columns: 1.2fr 0.9fr;
            gap:1.2rem;
            align-items:center;
        }
        .hero-title {
            font-size: 2rem;
            line-height: 1.1;
            margin: 0 0 0.9rem 0;
            font-weight: 800;
            letter-spacing: -0.04em;
        }
        .hero-text {
            font-size: 1.03rem;
            line-height: 1.8;
            color: var(--text);
            margin-bottom: 1rem;
        }
        .mini-tag-wrap {
            display:flex;
            flex-wrap:wrap;
            gap:0.65rem;
            margin-top:0.5rem;
        }
        .mini-tag {
            padding:0.52rem 0.82rem;
            border-radius:12px;
            background:#fff;
            border:1px solid rgba(111,61,255,0.12);
            color:#423b79;
            font-size:0.88rem;
            font-weight:600;
        }
        .visual-board {
            display:grid;
            grid-template-columns: 1fr 0.23fr 1fr;
            gap:0.9rem;
            align-items:center;
        }
        .doc-stack {
            background:#fff;
            border-radius:20px;
            border:1px solid var(--border);
            min-height: 220px;
            padding: 1rem;
            box-shadow: 0 18px 36px rgba(42, 52, 128, 0.08);
            position:relative;
        }
        .stack-title {
            text-align:center;
            font-weight:800;
            font-size: 1rem;
            margin-bottom: 0.8rem;
        }
        .paper {
            background:linear-gradient(180deg, #ffffff 0%, #faf9ff 100%);
            border:1px solid #ececf8;
            border-radius:14px;
            height:138px;
            width:105px;
            position:absolute;
            left:50%;
            transform: translateX(-50%);
            box-shadow: 0 10px 26px rgba(50, 54, 131, 0.09);
            overflow:hidden;
        }
        .paper.p1 { top: 55px; left: 42%; transform: translateX(-50%) rotate(-10deg); }
        .paper.p2 { top: 48px; left: 50%; transform: translateX(-50%); z-index:2; }
        .paper.p3 { top: 55px; left: 58%; transform: translateX(-50%) rotate(10deg); }
        .paper.one { top: 48px; left: 50%; transform: translateX(-50%); }
        .barcode { height: 14px; background: repeating-linear-gradient(90deg,#111 0,#111 2px,#fff 2px,#fff 4px); margin: 10px 10px 8px 10px; border-radius:2px; }
        .boxline { height: 8px; margin: 6px 10px; border-radius: 999px; background: #ececf8; }
        .boxline.wide { width: 76%; }
        .boxline.mid { width: 58%; }
        .qr { width: 34px; height: 34px; background: linear-gradient(45deg,#111 25%,#fff 25%,#fff 50%,#111 50%,#111 75%,#fff 75%); background-size: 10px 10px; margin: 10px; border-radius:4px; }
        .pdfchip {
            position:absolute; bottom:12px; left:12px; padding:0.28rem 0.5rem; border-radius:8px; font-size:0.75rem; font-weight:700;
            background:#ff4d4f; color:#fff;
        }
        .arrow-mid {
            display:flex; align-items:center; justify-content:center; font-size:2rem; color:var(--primary); font-weight:800;
        }
        .section-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.2rem;
            box-shadow: 0 18px 38px rgba(39, 48, 114, 0.05);
            margin-bottom: 1rem;
        }
        .section-title { font-size: 1.08rem; font-weight: 800; margin-bottom: 0.2rem; }
        .section-subtitle { color: var(--muted); font-size: 0.92rem; margin-bottom: 0.9rem; }
        .feature-grid {
            display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:0.9rem; margin: 1rem 0 1.15rem 0;
        }
        .feature-box {
            background:#fff; border:1px solid var(--border); border-radius:18px; padding:0.95rem; display:flex; gap:0.8rem; align-items:flex-start;
        }
        .ficon {
            width:40px; height:40px; border-radius:14px; display:flex; align-items:center; justify-content:center; font-size:20px; color:#fff;
        }
        .pink { background:linear-gradient(135deg,#ff6eb5,#ff4fa3); }
        .blue { background:linear-gradient(135deg,#65a9ff,#4187ff); }
        .green { background:linear-gradient(135deg,#44d7b6,#20b486); }
        .orange { background:linear-gradient(135deg,#ffb76b,#ff8e2b); }
        .feature-title { font-weight: 800; font-size: 0.95rem; margin-bottom: 0.15rem; }
        .feature-text { color: var(--muted); font-size: 0.84rem; line-height: 1.45; }
        .metric-card {
            background:#fff; border:1px solid var(--border); border-radius:18px; padding:1rem 1rem 0.9rem 1rem; box-shadow: 0 12px 26px rgba(39, 48, 114, 0.05);
        }
        .metric-label { color: var(--muted); font-size: 0.84rem; font-weight: 600; }
        .metric-value { font-size: 2rem; font-weight: 800; line-height: 1.1; margin-top: 0.25rem; }
        .success-banner {
            background: linear-gradient(90deg, rgba(22,163,74,0.14), rgba(22,163,74,0.08));
            border:1px solid rgba(22,163,74,0.22);
            border-radius:18px;
            padding:1rem 1.1rem;
            margin: 0.6rem 0 1rem 0;
            font-weight:700;
        }
        .warn-banner {
            background: linear-gradient(90deg, rgba(245,158,11,0.18), rgba(245,158,11,0.09));
            border:1px solid rgba(245,158,11,0.25);
            border-radius:18px;
            padding:1rem 1.1rem;
            margin: 0.6rem 0 1rem 0;
            font-weight:700;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 14px !important;
            border: none !important;
            min-height: 3rem !important;
            font-weight: 700 !important;
            box-shadow: 0 14px 30px rgba(111,61,255,0.18) !important;
        }
        .stButton > button[kind="primary"], .stDownloadButton > button {
            background: linear-gradient(135deg, var(--primary2), var(--primary)) !important;
            color: #fff !important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            filter: brightness(1.02);
            transform: translateY(-1px);
        }
        .stFileUploader > div {
            border-radius: 20px !important;
            border: 2px dashed #cfd4ea !important;
            background: linear-gradient(180deg, #ffffff, #fafbff) !important;
            padding-top: 0.5rem;
        }
        [data-testid="stMetric"] {
            background: transparent;
            border:none;
            box-shadow:none;
        }
        .footer-note {
            background:#fff; border:1px solid var(--border); border-radius:16px; padding: 0.95rem 1rem; color: var(--muted); font-size:0.9rem;
        }
        @media (max-width: 980px) {
            .hero-grid, .feature-grid { grid-template-columns: 1fr; }
            .visual-board { grid-template-columns: 1fr; }
            .arrow-mid { transform: rotate(90deg); }
            .app-header { flex-direction: column; align-items:flex-start; }
            .nav-pills { justify-content:flex-start; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown(
        """
        <div class="app-header">
            <div class="brand-wrap">
                <div class="brand-icon">📦</div>
                <div>
                    <h1 class="brand-title">Meesho Label Sorter</h1>
                    <p class="brand-subtitle">Upload Meesho SKU label PDFs and get a single sorted merged PDF</p>
                </div>
            </div>
            <div class="nav-pills">
                <div class="pill active">🏠 Home</div>
                <div class="pill">🕘 History</div>
                <div class="pill">⚙️ Settings</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-grid">
                <div>
                    <div class="hero-title">Sort &amp; Merge Meesho SKU Labels</div>
                    <div class="hero-text">
                        Upload multiple Meesho label PDFs from different accounts. The tool automatically groups
                        by product family and sorts sizes in the correct order so you get one clean merged PDF
                        ready for printing and packing.
                    </div>
                    <div class="mini-tag-wrap">
                        <div class="mini-tag">Auto group by product family</div>
                        <div class="mini-tag">Sort sizes: XS → S → M → L → XL…</div>
                        <div class="mini-tag">Original labels remain unchanged</div>
                    </div>
                </div>
                <div class="visual-board">
                    <div class="doc-stack">
                        <div class="stack-title">Unsorted Multiple PDFs</div>
                        <div class="paper p1"><div class="barcode"></div><div class="boxline wide"></div><div class="boxline mid"></div><div class="qr"></div><div class="pdfchip">PDF</div></div>
                        <div class="paper p2"><div class="barcode"></div><div class="boxline wide"></div><div class="boxline mid"></div><div class="qr"></div><div class="pdfchip">PDF</div></div>
                        <div class="paper p3"><div class="barcode"></div><div class="boxline wide"></div><div class="boxline mid"></div><div class="qr"></div><div class="pdfchip">PDF</div></div>
                    </div>
                    <div class="arrow-mid">➜</div>
                    <div class="doc-stack">
                        <div class="stack-title">Sorted Single PDF</div>
                        <div class="paper one"><div class="barcode"></div><div class="boxline wide"></div><div class="boxline mid"></div><div class="qr"></div><div class="pdfchip">PDF</div></div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_strip():
    st.markdown(
        """
        <div class="feature-grid">
            <div class="feature-box">
                <div class="ficon pink">🧩</div>
                <div><div class="feature-title">Auto Group</div><div class="feature-text">Same product family ke labels ek saath grouped rehte hain.</div></div>
            </div>
            <div class="feature-box">
                <div class="ficon blue">📏</div>
                <div><div class="feature-title">Sort Sizes</div><div class="feature-text">XS → S → M → L → XL → XXL → XXXL → 4XL...</div></div>
            </div>
            <div class="feature-box">
                <div class="ficon green">🛡️</div>
                <div><div class="feature-title">Original Labels Safe</div><div class="feature-text">Barcode, SKU, address, invoice and layout unchanged rehte hain.</div></div>
            </div>
            <div class="feature-box">
                <div class="ficon orange">⚠️</div>
                <div><div class="feature-title">Unreadable at End</div><div class="feature-text">Unreadable labels final PDF ke end me blank page ke baad aate hain.</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_rules():
    with st.expander("Sorting rules and logic", expanded=False):
        st.markdown(
            """
            - **Product family:** SKU ke end ke numeric digits sirf grouping ke liye ignore hote hain. Original SKU label par unchanged rehta hai.
              Example: `RED_white_Flowar_01`, `RED_white_Flowar16`, `RED_white_Flowar_32` → same family.
            - **Name formatting bhi grouping me ignore hoti hai:** spaces / underscore / hyphen / dot aur upper-lower case ka difference same product ko split nahi karega.
              Example: `BLUSHPINK_01`, `blush pink-.4`, `BLUSH-PINK_06` → same family.
            - **Text suffix stays separate:** `RED_white_Flowar_A` alag family rahega.
            - **Family order:** alphabetical.
            - **Size order:** XS → S → M → L → XL → XXL → XXXL/3XL → 4XL → 5XL → 6XL → 7XL → 8XL.
            - Same product + size ke labels sab accounts se **continuous** rahenge.
            - Jo label read na ho, wo final PDF ke **end** me jayega; error section se pehle **1 blank page** aayega.
            - Barcode, QR, address, invoice, SKU text, page design ko edit nahi kiya jata.
            """
        )


def fmt_size(num_bytes):
    mb = num_bytes / (1024 * 1024)
    return f"{mb:.1f} MB"


def render_upload_card(uploads):
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Upload label PDFs</div>
            <div class="section-subtitle">14 Meesho accounts ki files ek saath upload kar sakte ho</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Drag & drop or choose PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="14 files ek saath upload kar sakte hain. Tool aur bhi PDFs handle kar sakta hai.",
        label_visibility="collapsed",
    )
    if uploaded:
        total_mb = sum(f.size for f in uploaded) / (1024 * 1024)
        st.markdown(
            f"""
            <div class="section-card" style="padding:1rem 1.1rem; margin-top:0.8rem;">
                <div class="section-title">Uploaded Files ({len(uploaded)})</div>
                <div class="section-subtitle">Total size: {total_mb:.1f} MB</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        file_df = pd.DataFrame(
            [{"File Name": f.name, "Size": fmt_size(f.size)} for f in uploaded]
        )
        st.dataframe(file_df, use_container_width=True, hide_index=True, height=min(270, 80 + len(file_df) * 35))
    return uploaded


def show_process_steps():
    st.markdown(
        """
        <div class="section-card" style="margin-top:0.8rem;">
            <div class="section-title">Processing Steps</div>
            <div class="section-subtitle">PDF read → SKU detect → family group → size sort → final PDF</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(column, label, value):
    with column:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


inject_css()
render_header()
render_hero()
render_feature_strip()
render_rules()

uploads = render_upload_card(st.session_state.get("uploads"))

if uploads:
    col_btn, col_blank = st.columns([1.2, 2.2])
    with col_btn:
        sort_clicked = st.button("⚡ SORT + MERGE", type="primary", use_container_width=True)
    with col_blank:
        st.markdown("<div style='height:3rem'></div>", unsafe_allow_html=True)

    if sort_clicked:
        start = time.time()
        show_process_steps()
        progress = st.progress(8, text="Uploading and opening PDF files...")

        try:
            named_bytes = [(f.name, f.getvalue()) for f in uploads]
            progress.progress(22, text="Reading labels from uploaded PDFs...")
            result = process_pdfs(named_bytes)
            progress.progress(68, text="Grouping by product family and sorting by size...")
            elapsed = time.time() - start
            progress.progress(100, text="Final sorted PDF ready.")
        except Exception as exc:
            progress.empty()
            st.error(f"Processing failed: {exc}")
            st.stop()

        st.session_state["last_result"] = result
        st.session_state["elapsed"] = elapsed
        st.session_state["file_count"] = len(uploads)

if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    elapsed = st.session_state.get("elapsed", 0)

    if len(result["unreadable_df"]) == 0:
        st.markdown(
            f"<div class='success-banner'>✅ Processing completed successfully. All {result['input_labels']} labels were read. Final PDF has {result['output_pages']} pages.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='warn-banner'>⚠️ {len(result['unreadable_df'])} label(s) could not be read. Final PDF me normal labels ke baad 1 blank separator page hai, aur uske baad unreadable labels original form me hain.</div>",
            unsafe_allow_html=True,
        )

    m1, m2, m3, m4, m5 = st.columns(5)
    render_metric_card(m1, "PDF Files", st.session_state.get("file_count", "-"))
    render_metric_card(m2, "Input Labels", result["input_labels"])
    render_metric_card(m3, "Product Families", result["product_families"])
    render_metric_card(m4, "Unreadable", len(result["unreadable_df"]))
    render_metric_card(m5, "Processing Time", f"{elapsed:.1f}s")

    csv_data = result["order_df"].to_csv(index=False).encode("utf-8")
    cta1, cta2 = st.columns(2)
    with cta1:
        st.download_button(
            "⬇️ Download Sorted Labels PDF",
            data=result["sorted_pdf"],
            file_name="Meesho_Final_Sorted_Labels.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
    with cta2:
        st.download_button(
            "📥 Download Label Index CSV",
            data=csv_data,
            file_name="Meesho_Sorted_Label_Index.csv",
            mime="text/csv",
            use_container_width=True,
        )

    tab1, tab2, tab3 = st.tabs(["📊 Product + Size Summary", "🧾 Sorted Label Index", "⚠️ Unreadable Labels"])

    with tab1:
        st.markdown(
            "<div class='section-card'><div class='section-title'>Product Family Summary</div><div class='section-subtitle'>Family-wise size counts for packing and picking</div></div>",
            unsafe_allow_html=True,
        )
        st.dataframe(result["summary_df"], use_container_width=True, hide_index=True, height=460)

    with tab2:
        st.markdown(
            "<div class='section-card'><div class='section-title'>Sorted Label Index</div><div class='section-subtitle'>Exact order of labels in the final sorted PDF</div></div>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            result["order_df"][["family", "size", "sku", "order_no", "source_file", "page_number", "parse_status"]],
            use_container_width=True,
            hide_index=True,
            height=520,
        )

    with tab3:
        st.markdown(
            "<div class='section-card'><div class='section-title'>Unreadable / Error Labels</div><div class='section-subtitle'>These go to the end of the final PDF after one blank separator page</div></div>",
            unsafe_allow_html=True,
        )
        if len(result["unreadable_df"]):
            st.dataframe(
                result["unreadable_df"][["source_file", "page_number", "sku", "size", "parse_note"]],
                use_container_width=True,
                hide_index=True,
                height=300,
            )
        else:
            st.success("No unreadable labels found.")

st.markdown(
    "<div class='footer-note'>Privacy note: Streamlit Cloud par upload ki hui order PDFs server par processing ke liye bheji jati hain. Customer-address PDFs ke liye app ko private rakhna recommended hai.</div>",
    unsafe_allow_html=True,
)
