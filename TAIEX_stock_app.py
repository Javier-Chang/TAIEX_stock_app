import pandas as pd
import streamlit as st


# ==========================================
# 1. 密碼驗證機制 (含安全性防護)
# ==========================================
def check_password():
    """檢查 Streamlit Secrets 中的 APP_PASSWORD"""
    if "APP_PASSWORD" not in st.secrets:
        st.error(
            "⚠️ 未設定 `APP_PASSWORD`！請在 Streamlit Secrets 或 .streamlit/secrets.toml 中設定。"
        )
        return False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔒 系統登入")
    pwd = st.text_input("請輸入密碼", type="password")

    if st.button("登入"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 密碼錯誤，請重新輸入")

    return False


if not check_password():
    st.stop()


# ==========================================
# 2. 模擬範例資料 (請替換為你的實際資料源)
# ==========================================
@st.cache_data
def load_data():
    data = {
        "股票代號": ["2330", "2317", "2454", "2308", "2382"],
        "股票名稱": ["台積電", "鴻海", "聯發科", "台達電", "廣達"],
        "日 K": [20.5, 45.0, 15.0, 80.0, 65.0],
        "日 D": [50.0, 30.0, 10.0, 75.0, 60.0],
        "DIF": [-5.0, 2.5, 12.0, -12.0, 8.0],
        "MACD": [-3.0, 1.8, 10.0, -10.0, 6.0],
    }
    return pd.DataFrame(data)


df = load_data()


# ==========================================
# 3. 主畫面與篩選條件 (KD & MACD 皆使用 number_input)
# ==========================================
st.title("📈 股票技術指標篩選器")

st.sidebar.header("🔍 篩選條件設定")

# ------------------------------------------
# KD 指標設定 (已改為 number_input)
# ------------------------------------------
st.sidebar.subheader("日 KD 範圍")
col_k1, col_k2 = st.sidebar.columns(2)
with col_k1:
    k_min = st.number_input(
        "日 K 最小值",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
        key="k_min",
    )
    d_min = st.number_input(
        "日 D 最小值",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
        key="d_min",
    )
with col_k2:
    k_max = st.number_input(
        "日 K 最大值",
        min_value=0.0,
        max_value=100.0,
        value=22.0,
        step=1.0,
        key="k_max",
    )
    d_max = st.number_input(
        "日 D 最大值",
        min_value=0.0,
        max_value=100.0,
        value=53.0,
        step=1.0,
        key="d_max",
    )

st.sidebar.markdown("---")

# ------------------------------------------
# MACD 指標設定 (number_input)
# ------------------------------------------
st.sidebar.subheader("MACD 範圍")
col_m1, col_m2 = st.sidebar.columns(2)
with col_m1:
    dif_min = st.number_input(
        "DIF (快線) 最小值",
        min_value=-100.0,
        max_value=100.0,
        value=-11.0,
        step=1.0,
        key="dif_min",
    )
    macd_min = st.number_input(
        "MACD 最小值",
        min_value=-100.0,
        max_value=100.0,
        value=-10.0,
        step=1.0,
        key="macd_min",
    )
with col_m2:
    dif_max = st.number_input(
        "DIF (快線) 最大值",
        min_value=-100.0,
        max_value=100.0,
        value=10.0,
        step=1.0,
        key="dif_max",
    )
    macd_max = st.number_input(
        "MACD 最大值",
        min_value=-100.0,
        max_value=100.0,
        value=10.0,
        step=1.0,
        key="macd_max",
    )


# ==========================================
# 4. 資料過濾邏輯與結果顯示
# ==========================================
filtered_df = df[
    (df["日 K"] >= k_min)
    & (df["日 K"] <= k_max)
    & (df["日 D"] >= d_min)
    & (df["日 D"] <= d_max)
    & (df["DIF"] >= dif_min)
    & (df["DIF"] <= dif_max)
    & (df["MACD"] >= macd_min)
    & (df["MACD"] <= macd_max)
]

st.subheader(f"📊 篩選結果 (共 {len(filtered_df)} 檔)")
st.dataframe(filtered_df, use_container_width=True)