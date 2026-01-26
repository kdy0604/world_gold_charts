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
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .price-container { display: flex; gap: 10px; margin-bottom: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-label { font-size: 11px; color: #666; margin-bottom: 5px; display: block; }
    .up { color: #d9534f; font-weight: 600; font-size: 12px; } .down { color: #0275d8; font-weight: 600; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 등락 표시 함수 (이름 통일: format_delta)
def format_delta(curr, prev):
    if curr is None or prev is None: return ""
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    return f'<span class="{color}">{sign} {abs(diff):,.2f} ({pct:+.2f}%)</span>'

# 3. 데이터 로드 함수
@st.cache_data(ttl=600)
def get_intl_data(period="5d", interval="10m"):
    try:
        tickers = ["GC=F", "SI=F", "KRW=X"]
        data = yf.download(tickers, period=period, interval=interval, progress=False)['Close'].ffill()
        df = data.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
        if df.index.tz is None: df.index = df.index.tz_localize('UTC').tz_convert('Asia/Seoul')
        else: df.index = df.index.tz_convert('Asia/Seoul')
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        return df
    except: return None

@st.cache_data(ttl=3600)
def get_krx_data():
    service_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    params = {'serviceKey': service_key, 'numOfRows': '30', 'resultType': 'xml'}
    try:
        res = requests.get(url, params=params, timeout=15)
        root = ET.fromstring(res.text)
        items = root.findall('.//item')
        hist = [{'날짜': pd.to_datetime(i.find('basDt').text), '종가': float(i.find('clpr').text)*3.75, '등락률': float(i.find('flctRt').text if i.find('flctRt') is not None else 0)} for i in items if i.find('clpr') is not None]
        return pd.DataFrame(hist).sort_values('날짜')
    except: return None

# 데이터 준비
df_10m = get_intl_data("5d", "10m")
df_daily = get_intl_data("1mo", "1d")
df_krx = get_krx_data()

st.markdown('<p class="gs-title">📊 금/은 마켓 대시보드</p>', unsafe_allow_html=True)
st.markdown(f'<p style="text-align:right; font-size:12px; color:#888;">조회 기준(KST): {now_kst.strftime("%Y-%m-%d %H:%M:%S")}</p>', unsafe_allow_html=True)

# --- 1. 국제 금 섹션 ---
st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
if df_10m is not None and len(df_10m) >= 2: # 데이터가 2개 이상 있을 때만 표시 (IndexError 방지)
    c_rt, p_rt = df_10m.iloc[-1], df_10m.iloc[-2]
    c_da, p_da = df_daily.iloc[-1], df_daily.iloc[-2] if len(df_daily) >= 2 else (c_rt, c_rt)
    
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(c_rt['gold_don']):,}원</span>{format_delta(c_da['gold_don'], p_da['gold_don'])}</div>
            <div class="price-box"><span class="val-label">국제 시세 (1oz)</span><span class="val-main">${c_rt['gold']:.2f}</span>{format_delta(c_da['gold'], p_da['gold'])}</div>
        </div>
    """, unsafe_allow_html=True)

    t1, t2 = st.tabs(["실시간(10분)", "한달(일)"])
    with t1:
        fig = px.line(df_10m.tail(150), y='gold_don', template="plotly_white")
        fig.update_traces(line_color='#f1c40f').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(autorange=True, fixedrange=False))
        st.plotly_chart(fig, use_container_width=True)
    with t2:
        fig = px.line(df_daily, y='gold_don', template="plotly_white")
        fig.update_traces(line_color='#f1c40f').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(autorange=True, fixedrange=False))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("국제 금 시세 데이터를 불러오고 있습니다. 장 마감 직후에는 시간이 소요될 수 있습니다.")

# --- 2. 국내 금 섹션 ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 종가)</p>', unsafe_allow_html=True)
if df_krx is not None and not df_krx.empty:
    latest = df_krx.iloc[-1]
    st.markdown(f"""
        <div class="price-box" style="margin-bottom:15px;">
            <span class="val-label">KRX 금 시장 종가 (1돈 환산)</span><span class="val-main">{int(latest['종가']):,}원</span>
            <span class="{'up' if latest['등락률'] > 0 else 'down'}">{'▲' if latest['등락률'] > 0 else '▼'} {latest['등락률']}% (전일대비)</span>
        </div>
    """, unsafe_allow_html=True)
    fig_krx = px.area(df_krx, x='날짜', y='종가', template="plotly_white")
    fig_krx.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)')
    fig_krx.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(autorange=True, fixedrange=False))
    st.plotly_chart(fig_krx, use_container_width=True)
else:
    st.warning("국내 KRX 시세 데이터를 불러올 수 없습니다.")

# --- 3. 국제 은 섹션 ---
st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
if df_10m is not None and len(df_10m) >= 2:
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(c_rt['silver_don']):,}원</span>{format_delta(c_da['silver_don'], p_da['silver_don'])}</div>
            <div class="price-box"><span class="val-label">국제 시세 (1oz)</span><span class="val-main">${c_rt['silver']:.2f}</span>{format_delta(c_da['silver'], p_da['silver'])}</div>
        </div>
    """, unsafe_allow_html=True)
    t3, t4 = st.tabs(["실시간(10분)", "한달(일)"])
    with t3:
        fig = px.line(df_10m.tail(150), y='silver_don', template="plotly_white")
        fig.update_traces(line_color='#adb5bd').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(autorange=True, fixedrange=False))
        st.plotly_chart(fig, use_container_width=True)
    with t4:
        fig = px.line(df_daily, y='silver_don', template="plotly_white")
        fig.update_traces(line_color='#adb5bd').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(autorange=True, fixedrange=False))
        st.plotly_chart(fig, use_container_width=True)
