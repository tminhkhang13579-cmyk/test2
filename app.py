import os
import re
import json
import unicodedata
from pathlib import Path
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# =====================================================================
# 1. CẤU HÌNH TRANG WEB & GIAO DIỆN CSS (DARK MODE HIỆN ĐẠI)
# =====================================================================
st.set_page_config(
    page_title="TechBot PC Store - Linh Kiện Máy Tính",
    page_icon="🖥️",
    layout="wide"
)

st.markdown("""
<style>
    .product-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .product-card:hover {
        transform: translateY(-3px);
        border-color: #38bdf8;
    }
    .badge {
        background-color: #0284c7;
        color: white;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }
    .price-tag {
        color: #4ade80;
        font-size: 20px;
        font-weight: bold;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. KHỞI TẠO DỮ LIỆU CỬA HÀNG & CATALOG LINH KIỆN MÁY TÍNH
# =====================================================================
MODEL_NAME = "gemini-3.5-flash-lite"

STORE_CONFIG = {
    "store_name": "TechBot PC Store",
    "store_address": "Khu Công Nghệ Cao, TP. Hồ Chí Minh",
    "hotline": "1900-0000",
    "functions": [
        "giới thiệu cửa hàng",
        "tư vấn linh kiện máy tính & build PC",
        "giải đáp thông số và so sánh sản phẩm"
    ],
    "out_of_scope_message": "Tôi đang không hỗ trợ chức năng này. Xin vui lòng liên hệ nhân viên cửa hàng qua hotline 1900-0000 để được trợ giúp."
}

@st.cache_data
def load_catalog() -> pd.DataFrame:
    catalog_path = Path("techbot_products_catalog_300_filled.csv")
    if not catalog_path.exists():
        # Dữ liệu mẫu chuyên về Linh kiện máy tính & Gaming Gear
        sample_products = [
            {
                "product_id": "PC01",
                "product_name": "AMD Ryzen 7 7800X3D",
                "brand": "AMD",
                "category": "Vi xử lý (CPU)",
                "release_year": "2023",
                "launch_price": "449",
                "currency": "USD",
                "specifications": "8 nhân 16 luồng; xung nhịp tối đa 5.0GHz; bộ nhớ đệm 96MB 3D V-Cache; Socket AM5; TDP 120W",
                "advantages": "Hiệu năng chơi game đỉnh cao nhờ 3D V-Cache; tiết kiệm điện năng hơn đối thủ cùng phân khúc",
                "disadvantages": "Khả năng ép xung thủ công hạn chế; yêu cầu mainboard AM5 và RAM DDR5",
                "successor_model": "Ryzen 7 9800X3D",
                "official_source_url": "https://www.amd.com",
                "data_status": "Độ tin cậy trung bình, cần đối chiếu nguồn hãng."
            },
            {
                "product_id": "PC02",
                "product_name": "NVIDIA GeForce RTX 4070 Super",
                "brand": "NVIDIA",
                "category": "Card đồ họa (GPU)",
                "release_year": "2024",
                "launch_price": "599",
                "currency": "USD",
                "specifications": "12GB GDDR6X; 7168 nhân CUDA; hỗ trợ DLSS 3 Frame Generation, Ray Tracing; TGP 220W",
                "advantages": "Hiệu năng trên giá thành tốt cho màn hình 2K (1440p); nhiều hơn 20% nhân CUDA so với bản 4070 thường",
                "disadvantages": "VRAM 12GB có thể hơi sát với một số tựa game AAA 4K trong tương lai",
                "successor_model": "RTX 5070",
                "official_source_url": "https://www.nvidia.com",
                "data_status": "Độ tin cậy trung bình, cần đối chiếu nguồn hãng."
            },
            {
                "product_id": "PC03",
                "product_name": "Samsung 990 PRO 1TB NVMe M.2",
                "brand": "Samsung",
                "category": "Mạng và lưu trữ",
                "release_year": "2022",
                "launch_price": "129.99",
                "currency": "USD",
                "specifications": "Chuẩn PCIe 4.0 x4 NVMe M.2; Đọc tuần tự 7450 MB/s; Ghi tuần tự 6900 MB/s; DRAM Cache 1GB LPDDR4",
                "advantages": "Tốc độ đọc ghi thuộc hàng nhanh nhất chuẩn PCIe 4.0; độ bền cao, load game và ứng dụng cực nhanh",
                "disadvantages": "Giá cao hơn các dòng SSD phổ thông; cần tản nhiệt mainboard tốt khi chạy nặng",
                "successor_model": "Samsung 9100 PRO",
                "official_source_url": "https://www.samsung.com",
                "data_status": "Độ tin cậy trung bình, cần đối chiếu nguồn hãng."
            },
            {
                "product_id": "PC04",
                "product_name": "Corsair Vengeance RGB 32GB (2x16GB) DDR5 6000MHz",
                "brand": "Corsair",
                "category": "Bộ nhớ RAM",
                "release_year": "2023",
                "launch_price": "114.99",
                "currency": "USD",
                "specifications": "Dung lượng 32GB (2 thanh 16GB); Bus 6000MHz; CL36; hỗ trợ Intel XMP 3.0 & AMD EXPO; LED RGB 10 vùng",
                "advantages": "Mức bus 6000MHz tối ưu cho cả AMD Ryzen 7000 và Intel Gen 13/14; tản nhiệt nhôm đẹp, LED RGB rực rỡ",
                "disadvantages": "Chiều cao thanh RAM có thể cấn một số tản nhiệt khí cỡ lớn",
                "successor_model": "Chưa xác định",
                "official_source_url": "https://www.corsair.com",
                "data_status": "Độ tin cậy trung bình, cần đối chiếu nguồn hãng."
            },
            {
                "product_id": "0064",
                "product_name": "G Pro X Superlight 2",
                "brand": "Logitech",
                "category": "Chuột máy tính",
                "release_year": "2023",
                "launch_price": "159.99",
                "currency": "USD",
                "specifications": "Cảm biến HERO 2 32K; trọng lượng 60g; pin khoảng 95 giờ; tần số quét tới 2000Hz; cổng USB-C; switch LIGHTFORCE",
                "advantages": "Siêu nhẹ 60g; pin trâu 95 giờ; cổng sạc USB-C; độ trễ cực thấp cho eSports",
                "disadvantages": "Giá cao; kiểu dáng chỉ phù hợp tay trung và lớn",
                "successor_model": "Chưa xác định",
                "official_source_url": "https://www.logitech.com",
                "data_status": "Độ tin cậy trung bình, cần đối chiếu nguồn hãng."
            },
            {
                "product_id": "PC06",
                "product_name": "LG UltraGear 27GR95QE-B 27 inch OLED 240Hz",
                "brand": "LG",
                "category": "Màn hình",
                "release_year": "2023",
                "launch_price": "899.99",
                "currency": "USD",
                "specifications": "Kích thước 27 inch; độ phân giải QHD (2560x1440); tấm nền OLED; tần số quét 240Hz; tốc độ phản hồi 0.03ms; G-Sync & FreeSync",
                "advantages": "Màu đen tuyệt đối của OLED; tốc độ phản hồi 0.03ms gần như tức thì; tần số quét 240Hz siêu mượt",
                "disadvantages": "Độ sáng SDR ở mức trung bình; giá thành cao",
                "successor_model": "LG 27GS95QE-B",
                "official_source_url": "https://www.lg.com",
                "data_status": "Độ tin cậy trung bình, cần đối chiếu nguồn hãng."
            }
        ]
        pd.DataFrame(sample_products).to_csv(catalog_path, index=False, encoding="utf-8")
    return pd.read_csv(catalog_path, dtype=str).fillna("")

catalog_df = load_catalog()

# =====================================================================
# 3. LOGIC TÌM KIẾM SẢN PHẨM & XÂY DỰNG NGỮ CẢNH (TỪ FILE COLAB)
# =====================================================================
def normalize(text) -> str:
    text = unicodedata.normalize("NFD", str(text).lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()

CATEGORY_KEYWORDS = {
    "Vi xử lý (CPU)": ["cpu", "vi xu ly", "chip", "ryzen", "core i", "intel", "amd"],
    "Card đồ họa (GPU)": ["gpu", "vga", "card man hinh", "card do hoa", "rtx", "rx", "geforce"],
    "Bộ nhớ RAM": ["ram", "bo nho trong", "ddr4", "ddr5", "vengeance"],
    "Bo mạch chủ (Mainboard)": ["main", "mainboard", "bo mach chu", "b650", "b760", "z790"],
    "Điện thoại": ["dien thoai", "smartphone", "phone"],
    "Laptop": ["laptop", "may tinh xach tay", "notebook"],
    "Chuột máy tính": ["chuot", "mouse"],
    "Bàn phím": ["ban phim", "keyboard"],
    "Tai nghe và âm thanh": ["tai nghe", "loa", "am thanh", "headphone", "earbuds"],
    "Màn hình": ["man hinh", "monitor", "oled"],
    "Thiết bị chơi game": ["choi game", "may choi game", "console", "game"],
    "Mạng và lưu trữ": ["mang", "luu tru", "router", "wifi", "ssd", "nvme", "hdd", "o cung"],
}

STOPWORDS = set(
    "co la cua cho va nhung cac mot nao gi nhu the bao nhieu gia may thong so "
    "so sanh khac nhau ra mat nam khi tu den nay do hay voi ve thi nen o mau loai hang cua hang nhe nhat tot nhat".split()
)

def search_products(df: pd.DataFrame, question: str):
    q_norm = normalize(question)
    q_tokens = {t for t in q_norm.split() if t not in STOPWORDS}
    scored = []
    for idx, row in df.iterrows():
        name_tokens = normalize(row["product_name"]).split()
        core = [t for t in name_tokens if not re.fullmatch(r"(19|20)\d{2}", t)]
        brand_norm = normalize(row["brand"])
        matched = [t for t in core if t in q_tokens]
        score = 3.0 * len(matched)
        if core and len(matched) == len(core):
            score += 10
        brand_hit = brand_norm in q_tokens or any(t in q_tokens for t in brand_norm.split())
        if brand_hit:
            score += 2
        cat_hit = any(kw in f" {q_norm} " if " " in kw else kw in q_tokens
                      for kw in CATEGORY_KEYWORDS.get(row["category"], []))
        if cat_hit:
            score += 1.5
        if brand_hit and cat_hit:
            score += 3
        if str(row["release_year"]) in q_tokens:
            score += 1
        if score > 0:
            scored.append((score, idx))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [idx for _, idx in scored]

def reliability_text(status: str) -> str:
    status = str(status)
    note = ""
    if "Ghi chú:" in status:
        note = " Ghi chú: " + status.split("Ghi chú:", 1)[1].strip()
    if status.startswith("Độ tin cậy thấp"):
        return "thấp, cần xác minh từ nguồn hãng." + note
    return "trung bình, cần đối chiếu nguồn hãng." + note

def format_product(row) -> str:
    year = row["release_year"] or "chưa rõ"
    price = f"{row['launch_price']} {row['currency']}".strip() if row["launch_price"] else "chưa có dữ liệu giá"
    successor = row["successor_model"] or "chưa rõ"
    return (
        f"- {row['product_name']} ({row['brand']} | {row['category']} | ra mắt: {year}). "
        f"Giá khởi điểm: {price}. "
        f"Thông số: {row['specifications']}. "
        f"Ưu điểm: {row['advantages']}. "
        f"Nhược điểm: {row['disadvantages']}. "
        f"Đời kế nhiệm: {successor}. "
        f"Độ tin cậy dữ liệu: {reliability_text(row['data_status'])}"
    )

def catalog_overview(df: pd.DataFrame) -> str:
    parts = [f"{cat}: {n} sản phẩm" for cat, n in df["category"].value_counts().items()]
    return f"Catalog có {len(df)} sản phẩm. Các nhóm: " + "; ".join(parts) + "."

def build_catalog_context(df: pd.DataFrame, question: str, top_k: int = 8, extra_names: int = 25) -> str:
    matches = search_products(df, question)
    lines = [catalog_overview(df)]
    if not matches:
        lines.append("Không tìm thấy sản phẩm nào trong catalog khớp với câu hỏi này.")
        return "\n".join(lines)
    lines.append("Các sản phẩm liên quan nhất:")
    for idx in matches[:top_k]:
        lines.append(format_product(df.loc[idx]))
    rest = matches[top_k:top_k + extra_names]
    if rest:
        short = ", ".join(f"{df.loc[i, 'product_name']} ({df.loc[i, 'release_year'] or '?'})" for i in rest)
        lines.append(f"Các sản phẩm liên quan khác (chỉ có tên và năm): {short}.")
    return "\n".join(lines)

def build_system_instruction(cfg: dict) -> str:
    store_name = cfg.get("store_name", "TechBot Store")
    store_address = cfg.get("store_address", "")
    functions = ", ".join(cfg.get("functions", ["tư vấn sản phẩm công nghệ"]))
    out_of_scope_message = cfg.get("out_of_scope_message")

    return f"""
Bạn tên là TechBot, một trợ lý AI thông minh, nhiệt tình và lịch sự của cửa hàng {store_name}.
Địa chỉ cửa hàng: {store_address}.
Các nhiệm vụ được hỗ trợ: {functions}.

Quy tắc trả lời BẮT BUỘC:
1. Luôn trả lời bằng tiếng Việt, giọng điệu thân thiện, rõ ràng và chuyên nghiệp.
2. Chỉ tư vấn và trả lời dựa trên thông tin sản phẩm trong dữ liệu được cung cấp. Tuyệt đối KHÔNG tự bịa ra sản phẩm, thông số hay giá không có trong dữ liệu.
3. Nếu dữ liệu ghi "chưa có dữ liệu giá" hoặc thiếu thông tin, hãy nói rõ là chưa có dữ liệu thay vì đoán.
4. Khi giới thiệu sản phẩm, nêu thông số chính, ưu điểm, nhược điểm, năm ra mắt và đời kế nhiệm (nếu có). Nếu "Độ tin cậy dữ liệu" là thấp hoặc trung bình, nhắc khách nên đối chiếu với nguồn chính hãng trước khi mua. Giá là giá khởi điểm khi ra mắt, không phải giá bán hiện tại.
5. Khi khách muốn so sánh, hãy đối chiếu từng tiêu chí dựa trên dữ liệu cung cấp.
6. Nếu khách hỏi sản phẩm không có trong dữ liệu nhưng vẫn thuộc lĩnh vực công nghệ, hãy nói sản phẩm đó hiện chưa có trong catalog.
7. Nếu khách hàng hỏi những câu nằm NGOÀI phạm vi cửa hàng/sản phẩm công nghệ (ví dụ: món ăn, thời tiết, giải toán, chính trị...), hãy trả lời ĐÚNG câu sau:
   "{out_of_scope_message}"
8. Giữ câu trả lời súc tích, mạch lạc, dễ đọc.
""".strip()

# =====================================================================
# 4. HÀM GỌI GEMINI API (HỖ TRỢ SECRETS & MOCK MODE)
# =====================================================================
def ask_bot(question: str, api_key: str) -> str:
    catalog_context = build_catalog_context(catalog_df, question)
    system_instruction = build_system_instruction(STORE_CONFIG)

    user_prompt = f"""
Dưới đây là thông tin sản phẩm liên quan trong catalog của cửa hàng:
{catalog_context}

Khách hàng hỏi:
"{question}"

Hãy trả lời khách hàng theo đúng vai trò TechBot và các quy tắc đã được hướng dẫn.
"""
    if not api_key:
        return (
            "🤖 **[Chế độ Mock - Chưa có API Key]**: Bạn chưa cấu hình `GEMINI_API_KEY`. "
            "Tuy nhiên hệ thống tìm kiếm đã lọc ra ngữ cảnh sản phẩm khớp với câu hỏi của bạn:\n\n"
            f"```\n{catalog_context}\n```"
        )

    try:
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(thinking_level="minimal")
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=config,
        )
        return response.text
    except Exception as error:
        return f"⚠️ Lỗi khi gọi Gemini API: `{error}`. Vui lòng kiểm tra lại API Key hoặc tên model."

# =====================================================================
# 5. GIAO DIỆN NGƯỜI DÙNG (SIDEBAR + KỆ HÀNG + KHUNG CHAT)
# =====================================================================
with st.sidebar:
    st.title("🖥️ TechBot PC Store")
    st.write(f"📍 **Địa chỉ:** {STORE_CONFIG['store_address']}")
    st.write(f"☎️ **Hotline:** {STORE_CONFIG['hotline']}")
    st.divider()

    # Tự động đọc API Key từ Streamlit Secrets hoặc biến môi trường
    default_key = ""
    try:
        default_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        default_key = os.getenv("GEMINI_API_KEY", "")

    api_key_input = st.text_input(
        "🔑 Nhập Gemini API Key (để trống nếu đã cài trong Secrets):",
        value=default_key,
        type="password"
    )
    active_api_key = api_key_input.strip() or default_key

    st.divider()
    st.subheader("🔍 Bộ lọc linh kiện")
    categories = ["Tất cả"] + sorted(catalog_df["category"].unique().tolist())
    selected_cat = st.selectbox("Danh mục:", categories)
    search_kw = st.text_input("Tìm tên linh kiện / hãng:")

st.title("⚡ Cửa Hàng Linh Kiện Máy Tính & Trợ Lý AI TechBot")

col_shop, col_chat = st.columns([1.3, 1], gap="large")

# --- CỘT TRÁI: DANH SÁCH SẢN PHẨM ---
with col_shop:
    st.subheader("🛒 Danh Mục Linh Kiện & Gear")
    filtered_df = catalog_df.copy()
    if selected_cat != "Tất cả":
        filtered_df = filtered_df[filtered_df["category"] == selected_cat]
    if search_kw.strip():
        kw_norm = normalize(search_kw)
        mask = filtered_df.apply(
            lambda r: kw_norm in normalize(r["product_name"]) or kw_norm in normalize(r["brand"]),
            axis=1
        )
        filtered_df = filtered_df[mask]

    st.caption(f"Đang hiển thị **{len(filtered_df)}** sản phẩm.")

    for _, row in filtered_df.iterrows():
        st.markdown(f"""
        <div class="product-card">
            <span class="badge">{row['category']}</span>
            <span style="color: #94a3b8; font-size: 13px; margin-left: 8px;">Hãng: <b>{row['brand']}</b> | Ra mắt: {row['release_year']}</span>
            <h4 style="margin: 8px 0 4px 0; color: #f8fafc;">{row['product_name']}</h4>
            <div class="price-tag">💲 {row['launch_price']} {row['currency']} <span style="font-size:12px; color:#94a3b8; font-weight:normal;">(Giá niêm yết)</span></div>
            <p style="font-size: 13.5px; color: #cbd5e1; margin-bottom: 6px;">⚙️ <b>Thông số:</b> {row['specifications']}</p>
            <p style="font-size: 13px; color: #86efac; margin-bottom: 2px;">➕ <b>Ưu điểm:</b> {row['advantages']}</p>
            <p style="font-size: 13px; color: #fca5a5; margin-bottom: 0;">➖ <b>Nhược điểm:</b> {row['disadvantages']}</p>
        </div>
        """, unsafe_allow_html=True)

# --- CỘT PHẢI: CHATBOT AI ---
with col_chat:
    st.subheader("🤖 Trợ Lý Tư Vấn TechBot")
    st.caption("Hỏi đáp thông số CPU, GPU, RAM, SSD, so sánh linh kiện...")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": f"Chào bạn! Tôi là **TechBot** của **{STORE_CONFIG['store_name']}**. Bạn đang tìm kiếm CPU, Card đồ họa, RAM, SSD hay cần so sánh linh kiện nào?"
            }
        ]

    chat_container = st.container(height=520)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if user_q := st.chat_input("Ví dụ: Tư vấn cho mình CPU chơi game hoặc thông số RTX 4070 Super..."):
        st.session_state.messages.append({"role": "user", "content": user_q})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_q)

            with st.chat_message("assistant"):
                with st.spinner("TechBot đang tra cứu catalog..."):
                    reply = ask_bot(user_q, active_api_key)
                    st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
