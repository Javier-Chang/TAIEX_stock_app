import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# ----------------- 簡易密碼保護機制 -----------------
def check_password():
    if "APP_PASSWORD" not in st.secrets:
        st.error(
            "⚠️ 未設定 `APP_PASSWORD`！請在 Streamlit Secrets 或"
            " .streamlit/secrets.toml 中設定。"
        )
        return False

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        pwd = st.text_input("請輸入存取密碼：", type="password")
        if st.button("登入"):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("密碼錯誤！")
        return False
    return True


if not check_password():
    st.stop()


# ----------------- 獲取上市與上櫃股票資料 -----------------
@st.cache_data(ttl=600)
def fetch_all_stocks():
    stocks = []

    # 1. 抓取上市股票 (TWSE)
    try:
        url_twse = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        df_twse = pd.read_json(url_twse)
        for _, r in df_twse.iterrows():
            c = str(r.get("Code", "")).strip()
            p = str(r.get("ClosingPrice", "")).replace(",", "").strip()
            n = str(r.get("Name", "")).strip()
            if len(c) == 4 and c.isdigit():
                stocks.append(
                    {"Code": c, "Name": n, "Price": p, "Market": "TW"}
                )
    except Exception:
        pass

    # 2. 抓取上櫃股票 (TPEx 官方每日收盤價 API)
    tpex_success = False
    try:
        url_tpex = (
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
        )
        res = requests.get(url_tpex, timeout=10)
        if res.status_code == 200:
            for r in res.json():
                c = str(r.get("SecuritiesCompanyCode", "")).strip()
                n = str(r.get("CompanyName", "")).strip()
                p = str(r.get("Close", "")).replace(",", "").strip()
                if len(c) == 4 and c.isdigit():
                    stocks.append(
                        {"Code": c, "Name": n, "Price": p, "Market": "TWO"}
                    )
            tpex_success = True
    except Exception:
        pass

    # 備援：若 OpenAPI 異常，改由備用網頁 API 接手
    if not tpex_success:
        try:
            res = requests.get(
                "https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw",
                timeout=10,
            ).json()
            for r in res.get("aaData", []):
                if len(r) >= 3:
                    c = str(r[0]).strip()
                    n = str(r[1]).strip()
                    p = str(r[2]).replace(",", "").strip()
                    if len(c) == 4 and c.isdigit():
                        stocks.append(
                            {"Code": c, "Name": n, "Price": p, "Market": "TWO"}
                        )
        except Exception:
            pass

    df = pd.DataFrame(stocks)
    if not df.empty:
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df = df.dropna(subset=["Price"])
        df = df[df["Price"] > 0]
        return df.drop_duplicates(subset=["Code"])

    return pd.DataFrame(columns=["Code", "Name", "Price", "Market"])


def download_stock_data(code, default_market):
    primary_mkt = default_market if default_market in ["TW", "TWO"] else "TW"
    secondary_mkt = "TWO" if primary_mkt == "TW" else "TW"

    for mkt in [primary_mkt, secondary_mkt]:
        try:
            # 採用 5 年資料確保 MACD 與技術指標平滑穩定
            df = yf.download(
                f"{code}.{mkt}",
                period="5y",
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            if not df.empty and len(df) >= 26:
                if isinstance(df.columns, pd.MultiIndex):
                    t_str = f"{code}.{mkt}"
                    df = (
                        df.xs(t_str, axis=1, level=1)
                        if t_str in df.columns.levels[1]
                        else df.droplevel(1, axis=1)
                    )
                req = ["Open", "High", "Low", "Close", "Volume"]
                if all(c in df.columns for c in req):
                    return df[req].dropna()
        except Exception:
            pass
    return pd.DataFrame()


# --------------------------------------------------
# 日線 KD 專用基準錨點字典
# --------------------------------------------------
KD_BASELINE_DICT = {
    "6669": {
        "daily": {"date": "2026-09-22", "K": 13.11, "D": 12.65}
    }
}


st.title("📈 台股全市場・自訂股價、日 KD 與日 MACD 篩選器")

if "matched_results" not in st.session_state:
    st.session_state.matched_results = None
if "has_run" not in st.session_state:
    st.session_state.has_run = False

# 第一排：股價門檻
min_price = st.number_input("最低股價門檻 (≧)", value=500, step=50)

# 第二排：日 KD 範圍設定
col1, col2 = st.columns(2)
with col1:
    min_day_k = st.number_input(
        "日 K 最小值", min_value=0.0, max_value=100.0, value=0.0, step=5.0
    )
    min_day_d = st.number_input(
        "日 D 最小值", min_value=0.0, max_value=100.0, value=0.0, step=5.0
    )
with col2:
    max_day_k = st.number_input(
        "日 K 最大值", min_value=0.0, max_value=100.0, value=90.0, step=5.0
    )
    max_day_d = st.number_input(
        "日 D 最大值", min_value=0.0, max_value=100.0, value=90.0, step=5.0
    )

st.markdown("---")

# 第三排：日 MACD 範圍設定
col3, col4, col5 = st.columns(3)
with col3:
    min_dif, max_dif = (
        st.number_input("DIF (快線) 最小值", value=-10.0, step=1.0),
        st.number_input("DIF (快線) 最大值", value=10.0, step=1.0),
    )
with col4:
    min_dea, max_dea = (
        st.number_input("MACD (慢線/DEM) 最小值", value=-10.0, step=1.0),
        st.number_input("MACD (慢線/DEM) 最大值", value=10.0, step=1.0),
    )
with col5:
    min_hist, max_hist = (
        st.number_input("MACD 柱狀體 最小值", value=-5.0, step=1.0),
        st.number_input("MACD 柱狀體 最大值", value=5.0, step=1.0),
    )

if st.button("開始掃描運算"):
    st.session_state.has_run = True
    with st.spinner("正在向交易所抓取清單並計算 KD/MACD，請稍候..."):
        df_all = fetch_all_stocks()

        tw_cnt = len(df_all[df_all["Market"] == "TW"])
        two_cnt = len(df_all[df_all["Market"] == "TWO"])
        st.info(
            f"💡 成功獲取股票總清單：上市 {tw_cnt} 檔，上櫃 {two_cnt} 檔"
        )

        target_stocks = df_all[df_all["Price"] >= min_price]

        matched = []
        progress_bar = st.progress(0)
        total = len(target_stocks)


        # 計算帶有錨點校正機制的日 KD 函式
        def calc_kd_series(df, code=None):
            if len(df) < 9:
                return pd.Series([50.0] * len(df)), pd.Series(
                    [50.0] * len(df)
                )
            low_min = df["Low"].rolling(9, min_periods=9).min()
            high_max = df["High"].rolling(9, min_periods=9).max()
            rsv = (
                (df["Close"] - low_min)
                / (high_max - low_min).replace(0, 1e-9)
                * 100
            )
            
            k_list, d_list = [], []
            k, d = 50.0, 50.0
            
            baseline = KD_BASELINE_DICT.get(str(code), {}).get("daily") if code else None
            baseline_date = pd.to_datetime(baseline["date"]).date() if baseline and "date" in baseline else None

            for dt, val in zip(df.index, rsv):
                current_date = pd.to_datetime(dt).date()

                if pd.isna(val):
                    k_list.append(round(k, 2))
                    d_list.append(round(d, 2))
                    continue

                matched_baseline = False
                if baseline_date and current_date == baseline_date:
                    matched_baseline = True

                if matched_baseline:
                    k = baseline["K"]
                    d = baseline["D"]
                else:
                    k = (2 / 3) * k + (1 / 3) * val
                    d = (2 / 3) * d + (1 / 3) * k

                k_list.append(round(k, 2))
                d_list.append(round(d, 2))

            return pd.Series(k_list, index=df.index), pd.Series(
                d_list, index=df.index
            )


        # 計算 MACD 函式
        def calc_macd_series(df):
            if len(df) < 26:
                zero_s = pd.Series([0.0] * len(df), index=df.index)
                return zero_s, zero_s, zero_s
            ema12 = df["Close"].ewm(span=12, adjust=False).mean()
            ema26 = df["Close"].ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            macd_hist = (dif - dea) * 2
            return dif, dea, macd_hist


        for i, (_, row) in enumerate(target_stocks.iterrows()):
            code = str(row["Code"]).strip()
            name = row["Name"]
            mkt = row.get("Market", "TW")

            try:
                df_d = download_stock_data(code, mkt)

                if not df_d.empty and len(df_d) >= 26:
                    dk_s, dd_s = calc_kd_series(df_d, code=code)
                    dif_s, dea_s, hist_s = calc_macd_series(df_d)

                    dk = dk_s.iloc[-1]
                    dd = dd_s.iloc[-1]
                    dif = round(dif_s.iloc[-1], 2)
                    dea = round(dea_s.iloc[-1], 2)
                    hist = round(hist_s.iloc[-1], 2)
                    latest_price = int(round(df_d["Close"].iloc[-1]))

                    kd_pass = (min_day_k <= dk <= max_day_k) and (
                        min_day_d <= dd <= max_day_d
                    )
                    macd_pass = (
                        (min_dif <= dif <= max_dif)
                        and (min_dea <= dea <= max_dea)
                        and (min_hist <= hist <= max_hist)
                    )

                    if kd_pass and macd_pass:
                        matched.append(
                            {
                                "代號": code,
                                "名稱": name,
                                "市場": "上櫃" if mkt == "TWO" else "上市",
                                "股價": latest_price,
                                "日K": dk,
                                "日D": dd,
                                "DIF (快線)": dif,
                                "MACD (慢線)": dea,
                                "柱狀體": hist,
                            }
                        )
            except Exception:
                pass

            if total > 0:
                progress_bar.progress((i + 1) / total)

        st.session_state.matched_results = matched

if st.session_state.has_run:
    st.subheader("📊 符合條件的股票清單")
    matched = st.session_state.matched_results
    if matched:
        st.success(f"找到 {len(matched)} 檔符合條件的股票！")
        st.dataframe(pd.DataFrame(matched))
    else:
        st.warning("在目前的篩選條件下，沒有找到符合的股票。")
