import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime, timedelta
import pytz
from pykrx import stock

# 1. 설정 및 스타일
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 5px; color: #1e1e1e; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 5px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 12px; border-radius: 12px; border: 1px solid #eee; text-align: center; min-height: 120px; margin-bottom: 10px; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-sub { font-size: 11px; color: #666; margin-bottom: 3px; display: block; }
    .delta { font-size: 12px; font-weight: 600; }
    .up { color: #d9534f; } .down { color: #0275d8; }
    .ref-time { font-size: 10px; color: #999; display: block; margin-top: 8px; line-height: 1.3; }
    .fx-container { background-color: #f1f3f9; padding: 12px 15px; border-radius: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #dbe2ef; }
    </style>
    """, unsafe_allow_html=True)

# --- 등락 표시 유틸리티 ---
def get_delta_html(curr, prev, prefix=""):
    try:
        if prev is None or curr is None or prev == 0: return ""
        diff = curr - prev
        pct = (diff / prev) * 100
        color = "up" if diff >= 0 else "down"
        sign = "▲" if diff >= 0 else "▼"
        return f'<span class="delta {color}">{sign} {prefix}{abs(diff):,.2f} ({pct:+.2f}%)</span>'
    except: return ""

def update_layout(fig, y_min, y_max):
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(range=[y_min, y_max], fixedrange=True, title=None),
        xaxis=dict(fixedrange=True, title=None), template="plotly_white", dragmode=False)
    return fig

# --- [데이터 로드] ---
@st.cache_data(ttl=60)
def get_single_ticker(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        df = t.history(period="3mo")['Close']
        live = t.fast_info.last_price
        if live: df.iloc[-1] = live
        return df
    except: return None

@st.cache_data(ttl=3600)
def get_krx_history():
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    raw_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    try:
        res = requests.get(url, params={'serviceKey': unquote(raw_key), 'numOfRows': '400', 'resultType': 'xml'}, timeout=10)
        root = ET.fromstring(res.content)
        data = [{'날짜': pd.to_datetime(i.findtext('basDt')), '종가': float(i.findtext('clpr', 0)) * 3.75} 
                for i in root.findall('.//item') if "금" in i.findtext('itmsNm', '') and "99.99" in i.findtext('itmsNm', '')]
        df = pd.DataFrame(data).drop_duplicates('날짜').set_index('날짜').sort_index()
        return df, df.index[-1].strftime('%Y-%m-%d')
    except: return None, None

def get_pykrx_realtime():
    try:
        end = datetime.now(KST).strftime("%Y%m%d")
        start = (datetime.now(KST) - timedelta(days=10)).strftime("%Y%m%d")
        df = stock.get_market_ohlcv(start, end, "KGS00C003001", market="GOLD")
        if df.empty: return None, None, None
        return df['종가'].iloc[-1] * 3.75, df['종가'].iloc[-2] * 3.75, datetime.now(KST).strftime('%H:%M:%S')
    except: return None, None, None

# 데이터 수집 (각각 독립적으로 수집하여 하나라도 나오게 함)
gold_history = get_single_ticker("GC=F")
silver_history = get_single_ticker("SI=F")
ex_history = get_single_ticker("KRW=X")
df_krx_h, krx_last_date = get_krx_history()
kr_now, kr_prev, kr_time = get_pykrx_realtime()

st.markdown('<p class="gs-title">📊 금/은 마켓 실시간 대시보드</p>', unsafe_allow_html=True)

# 1. 국제 금 섹션 (데이터가 있을 때만 표시)
if gold_history is not None and ex_history is not None:
    # 환산 데이터 생성
    df_intl = pd.concat([gold_history, ex_history], axis=1).ffill().dropna()
    df_intl.columns = ['gold', 'ex']
    df_intl['gold_don'] = (df_intl['gold'] / 31.1034) * df_intl['ex'] * 3.75
    
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    update_time = datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')

    st.markdown(f'<div class="fx-container"><b>원/달러 환율</b><div style="text-align:right;"><b>{curr["ex"]:,.2f}원</b><br>{get_delta_html(curr["ex"], prev["ex"])}</div></div>', unsafe_allow_html=True)
    st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: st.markdown(f'<div class="price-box"><span class="val-sub">국제 (1oz)</span><span class="val-main">${curr["gold"]:,.2f}</span>{get_delta_html(curr["gold"], prev["gold"], "$")}<span class="ref-time">수집: {update_time}</span></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="price-box"><span class="val-sub">국내환산 (1돈)</span><span class="val-main">{int(curr["gold_don"]):,}원</span>{get_delta_html(curr["gold_don"], prev["gold_don"])}<span class="ref-time">기준: {update_time}</span></div>', unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["$/oz 차트", "₩/돈 차트"])
    with t1: st.plotly_chart(update_layout(px.line(df_intl, y='gold'), df_intl['gold'].min()*0.99, df_intl['gold'].max()*1.01), use_container_width=True)
    with t2: st.plotly_chart(update_layout(px.line(df_intl, y='gold_don').update_traces(line_color='#f1c40f'), df_intl['gold_don'].min()*0.99, df_intl['gold_don'].max()*1.01), use_container_width=True)

# 2. 국내 금 섹션
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx_h is not None:
    disp_p = kr_now if kr_now else df_krx_h['종가'].iloc[-1]
    prev_ref = kr_prev if kr_now else df_krx_h['종가'].iloc[-2]
    st.markdown(f"""
        <div class="price-box">
            <span class="val-sub">{"KRX 실시간(pykrx)" if kr_now else "KRX 마지막 종가"}</span>
            <span class="val-main" style="color:#d9534f;">{int(disp_p):,}원</span>
            {get_delta_html(disp_p, prev_ref)}
            <span class="ref-time"><b>실시간 시세:</b> {kr_time if kr_now else "장외"}<br><b>차트 데이터:</b> {krx_last_date} 종가 기준</span>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(update_layout(px.area(df_krx_h, y='종가').update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)'), df_krx_h['종가'].min()*0.98, df_krx_h['종가'].max()*1.02), use_container_width=True)

# 3. 국제 은 섹션
if silver_history is not None and ex_history is not None:
    df_silver = pd.concat([silver_history, ex_history], axis=1).ffill().dropna()
    df_silver.columns = ['silver', 'ex']
    df_silver['silver_don'] = (df_silver['silver'] / 31.1034) * df_silver['ex'] * 3.75
    
    curr_s, prev_s = df_silver.iloc[-1], df_silver.iloc[-2]
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3: st.markdown(f'<div class="price-box"><span class="val-sub">국제 (1oz)</span><span class="val-main">${curr_s["silver"]:,.2f}</span>{get_delta_html(curr_s["silver"], prev_s["silver"], "$")}<span class="ref-time">수집: {update_time}</span></div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="price-box"><span class="val-sub">국내환산 (1돈)</span><span class="val-main">{int(curr_s["silver_don"]):,}원</span>{get_delta_html(curr_s["silver_don"], prev_s["silver_don"])}<span class="ref-time">기준: {update_time}</span></div>', unsafe_allow_html=True)
    
    s1, s2 = st.tabs(["$/oz 차트", "₩/돈 차트"])
    with s1: st.plotly_chart(update_layout(px.line(df_silver, y='silver').update_traces(line_color='#adb5bd'), df_silver['silver'].min()*0.95, df_silver['silver'].max()*1.05), use_container_width=True)
    with s2: st.plotly_chart(update_layout(px.line(df_silver, y='silver_don').update_traces(line_color='#adb5bd'), df_silver['silver_don'].min()*0.95, df_silver['silver_don'].max()*1.05), use_container_width=True)
