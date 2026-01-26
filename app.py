import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz

# 1. 페이지 설정 및 한국 시간 설정
st.set_page_config(page_title="제네바시계 금융 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')
now_kst = datetime.now(KST)

st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 20px; color: #1e1e1e; border-bottom: 2px solid #333; padding-bottom: 10px; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; display: flex; align-items: center; }
    .price-container { display: flex; gap: 10px; margin-bottom: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-label { font-size: 11px; color: #666; margin-bottom: 5px; display: block; }
    .up { color: #d9534f; font-weight: 600; font-size: 12px; } .down { color: #0275d8; font-weight: 600; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 크롤링 함수
@st.cache_data(ttl=60)
def get_intl_data(period="2d", interval="1m"):
    tickers = ["GC=F", "SI=F", "KRW=X"]
    data = yf.download(tickers, period=period, interval=interval)['Close'].ffill()
    df = data.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
    df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
    df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
    return df

@st.cache_data(ttl=3600)
def get_krx_data():
    service_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    params = {'serviceKey': service_key, 'numOfRows': '30', 'resultType': 'xml'}
    try:
        res = requests.get(url, params=params, timeout=10)
        root = ET.fromstring(res.text)
        items = root.findall('.//item')
        hist = []
        for item in items:
            hist.append({'날짜': pd.to_datetime(item.find('basDt').text), 
                         '종가': float(item.find('clpr').text) * 3.75,
                         '등락률': float(item.find('flctRt').text)})
        return pd.DataFrame(hist).sort_values('날짜')
    except: return None

def format_delta(curr, prev):
    diff = curr - prev
    pct = (diff / prev) * 100
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    return f'<span class="{color}">{sign} {abs(diff):,.2f} ({pct:+.2f}%)</span>'

# 상단 제목 및 시간
st.markdown(f'<p class="gs-title">📊 금/은 마켓 대시보드</p>', unsafe_allow_html=True)
st.markdown(f'<p style="text-align:right; font-size:12px; color:#888;">업데이트: {now_kst.strftime("%Y-%m-%d %H:%M:%S")} (KST)</p>', unsafe_allow_html=True)

# 데이터 로드
df_rt = get_intl_data("2d", "1m")
df_daily = get_intl_data("1mo", "1d")
df_krx = get_krx_data()

# ---------------------------------------------------------
# 1. 국제 금 시세 (GC=F)
# ---------------------------------------------------------
st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
if df_rt is not None:
    c_rt, p_rt = df_rt.iloc[-1], df_rt.iloc[-2]  # 실시간/전분
    c_da, p_da = df_daily.iloc[-1], df_daily.iloc[-2] # 오늘/어제
    
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box">
                <span class="val-label">국내 환산가 (1돈)</span>
                <span class="val-main">{int(c_rt['gold_don']):,}원</span>
                {format_delta(c_da['gold_don'], p_da['gold_don'])} <small>(전일대비)</small>
            </div>
            <div class="price-box">
                <span class="val-label">국제 시세 (1oz)</span>
                <span class="val-main">${c_rt['gold']:.2f}</span>
                {format_delta(c_da['gold'], p_da['gold'])} <small>(전일대비)</small>
            </div>
        </div>
    """, unsafe_allow_html=True)

    g_tab1, g_tab2 = st.tabs(["실시간(분)", "한달(일)"])
    with g_tab1:
        fig = px.line(df_rt.tail(60), y='gold_don', template="plotly_white")
        fig.update_traces(line_color='#f1c40f').update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with g_tab2:
        fig = px.line(df_daily, y='gold_don')
        fig.update_traces(line_color='#f1c40f').update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 2. 국내 금 시세 (KRX 공식)
# ---------------------------------------------------------
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식 종가)</p>', unsafe_allow_html=True)
if df_krx is not None:
    latest = df_krx.iloc[-1]
    color = "up" if latest['등락률'] > 0 else "down"
    sign = "▲" if latest['등락률'] > 0 else "▼"
    
    st.markdown(f"""
        <div class="price-box" style="margin-bottom:15px;">
            <span class="val-label">KRX 금 시장 종가 (1돈 환산)</span>
            <span class="val-main">{int(latest['종가']):,}원</span>
            <span class="{color}">{sign} {latest['등락률']}% (전일대비)</span>
        </div>
    """, unsafe_allow_html=True)
    
    fig_krx = px.area(df_krx, x='날짜', y='종가')
    fig_krx.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)')
    fig_krx.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_krx, use_container_width=True)

# ---------------------------------------------------------
# 3. 국제 은 시세 (Silver)
# ---------------------------------------------------------
st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
if df_rt is not None:
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box">
                <span class="val-label">국내 환산가 (1돈)</span>
                <span class="val-main">{int(c_rt['silver_don']):,}원</span>
                {format_delta(c_da['silver_don'], p_da['silver_don'])} <small>(전일대비)</small>
            </div>
            <div class="price-box">
                <span class="val-label">국제 시세 (1oz)</span>
                <span class="val-main">${c_rt['silver']:.2f}</span>
                {format_delta(c_da['silver'], p_da['silver'])} <small>(전일대비)</small>
            </div>
        </div>
    """, unsafe_allow_html=True)

    s_tab1, s_tab2 = st.tabs(["실시간(분)", "한달(일)"])
    with s_tab1:
        fig = px.line(df_rt.tail(60), y='silver_don')
        fig.update_traces(line_color='#adb5bd').update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with s_tab2:
        fig = px.line(df_daily, y='silver_don')
        fig.update_traces(line_color='#adb5bd').update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

st.caption(f"※ 환율 정보는 국제 시계열에 실시간 반영되어 계산됩니다. 기준 시간: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST")
