import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="제네바시계 금융 대시보드", layout="centered")

st.markdown("""
    <style>
    .gs-title { font-size: 28px; font-weight: 800; margin-bottom: 5px; color: #1e1e1e; }
    .live-indicator { color: #ff0000; font-weight: 800; font-size: 12px; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; border-left: 4px solid #333; padding-left: 10px; }
    .price-box { background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 10px; }
    .val-main { font-size: 22px; font-weight: 800; color: #111; }
    .val-sub { font-size: 13px; color: #666; margin-left: 10px; }
    .up { color: #d9534f; font-weight: 600; } .down { color: #0275d8; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 처리 함수들
@st.cache_data(ttl=60)
def load_realtime(): # 1분 단위 데이터
    tickers = ["GC=F", "SI=F", "KRW=X"]
    data = yf.download(tickers, period="2d", interval="1m")['Close'].ffill()
    df = data.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
    df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
    df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
    return df

@st.cache_data(ttl=3600)
def load_monthly(): # 한달 일별 데이터 (국제)
    tickers = ["GC=F", "SI=F", "KRW=X"]
    data = yf.download(tickers, period="1mo", interval="1d")['Close'].ffill()
    df = data.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
    df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
    df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
    return df

@st.cache_data(ttl=3600)
def get_krx_monthly(): # 국내 KRX 한달 종가
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
                         '등락': float(item.find('vs').text) * 3.75,
                         '등락률': float(item.find('flctRt').text)})
        return pd.DataFrame(hist).sort_values('날짜')
    except: return None

def display_delta(curr, prev):
    diff = curr - prev
    pct = (diff / prev) * 100
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    return f'<span class="{color}">{sign} {int(abs(diff)):,}원 ({pct:+.2f}%)</span>'

# 3. 메인 화면 구성
st.markdown('<p class="gs-title">💰 금/은 종합 리포트</p>', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["⚡ 실시간 리포트 (1분)", "📅 한달 기록 (일별)"])

df_rt = load_realtime()
df_mo = load_monthly()
df_krx = get_krx_monthly()

# --- [TAB 1] 실시간 리포트 ---
with tab1:
    if df_rt is not None:
        c = df_rt.iloc[-1]
        p = df_rt.iloc[-2]
        
        st.markdown(f'<p style="text-align:right;"><span class="live-indicator">● 실시간 LIVE</span> ({datetime.now().strftime("%H:%M:%S")})</p>', unsafe_allow_html=True)

        # 1. 국제 금
        st.markdown('<p class="main-title">🟡 국제 금 시세</p>', unsafe_allow_html=True)
        st.markdown(f"""<div class="price-box">
            <span class="val-main">{int(c['gold_don']):,}원</span>
            <span class="val-sub">(${c['gold']:.2f} / oz)</span><br>
            {display_delta(c['gold_don'], p['gold_don'])}
        </div>""", unsafe_allow_html=True)
        fig1 = px.line(df_rt.tail(60), y='gold_don', title="최근 60분 흐름 (1돈)")
        fig1.update_traces(line_color='#f1c40f').update_layout(height=200, margin=dict(l=0,r=0,t=30,b=0), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig1, use_container_width=True)

        # 2. 국내 금 (실시간은 API가 없으므로 환산 시세로 표시)
        st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (실시간 환산)</p>', unsafe_allow_html=True)
        st.markdown(f"""<div class="price-box">
            <span class="val-main">{int(c['gold_don']):,}원</span>
            <span class="val-sub">(환율: {c['ex']:.2f}원 적용)</span>
        </div>""", unsafe_allow_html=True)
        st.info("국내 실시간 시세는 국제 시세와 환율을 실시간 계산한 결과입니다.")

        # 3. 국제 은
        st.markdown('<p class="main-title">⚪ 국제 은 시세</p>', unsafe_allow_html=True)
        st.markdown(f"""<div class="price-box">
            <span class="val-main">{int(c['silver_don']):,}원</span>
            <span class="val-sub">(${c['silver']:.2f} / oz)</span><br>
            {display_delta(c['silver_don'], p['silver_don'])}
        </div>""", unsafe_allow_html=True)
        fig3 = px.line(df_rt.tail(60), y='silver_don')
        fig3.update_traces(line_color='#adb5bd').update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig3, use_container_width=True)

# --- [TAB 2] 한달 기록 리포트 ---
with tab2:
    # 1. 국제 금 (한달)
    st.markdown('<p class="main-title">🟡 국제 금 (최근 30일)</p>', unsafe_allow_html=True)
    fig_m1 = px.line(df_mo, y='gold_don')
    fig_m1.update_traces(line_color='#f1c40f').update_layout(height=220, xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_m1, use_container_width=True)

    # 2. 국내 금 (KRX 공식 한달 종가)
    st.markdown('<p class="main-title">🇰🇷 국내 금 (KRX 공식 한달)</p>', unsafe_allow_html=True)
    if df_krx is not None:
        latest = df_krx.iloc[-1]
        st.markdown(f"""<div class="price-box">
            <span class="val-main">{int(latest['종가']):,}원</span>
            <span class="{ 'up' if latest['등락'] > 0 else 'down' }">
                ({ '▲' if latest['등락'] > 0 else '▼' } {int(abs(latest['등락'])):,}원, {latest['등락률']}% )
            </span>
        </div>""", unsafe_allow_html=True)
        fig_m2 = px.bar(df_krx, x='날짜', y='종가', title="KRX 일별 종가 추이")
        fig_m2.update_traces(marker_color='#4361ee').update_layout(height=220, xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig_m2, use_container_width=True)

    # 3. 국제 은 (한달)
    st.markdown('<p class="main-title">⚪ 국제 은 (최근 30일)</p>', unsafe_allow_html=True)
    fig_m3 = px.line(df_mo, y='silver_don')
    fig_m3.update_traces(line_color='#adb5bd').update_layout(height=220, xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_m3, use_container_width=True)

st.caption("실시간 시세: Yahoo Finance (1분 단위) / 국내 종가 시세: 공공데이터포털 KRX")
