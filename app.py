import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="실시간 금/은 마켓 리포트", layout="centered")

# 실시간 느낌을 주는 디자인 (네온 포인트)
st.markdown("""
    <style>
    .live-indicator { color: #ff0000; font-weight: 800; font-size: 12px; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    .price-card { background: #1e1e1e; color: white; padding: 20px; border-radius: 15px; border-top: 5px solid #f1c40f; }
    .label-text { font-size: 12px; color: #aaa; }
    .value-text { font-size: 24px; font-weight: 800; color: #ffffff; }
    .delta-text { font-size: 13px; font-weight: 600; }
    .up { color: #ff4b4b; } .down { color: #377dff; }
    </style>
    """, unsafe_allow_html=True)

# 2. 등락 계산 함수
def get_delta_html(curr, prev, is_currency=False):
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    sign = "▲" if diff > 0 else "▼"
    color = "up" if diff > 0 else "down"
    v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
    return f'<span class="delta-text {color}">{sign} {v} ({pct:+.2f}%)</span>'

# 3. 실시간 데이터 로드 (1분 단위)
@st.cache_data(ttl=60) # 60초마다 캐시 만료
def load_realtime_data():
    try:
        # 1분 단위(interval='1m')로 최근 7일치 데이터를 가져옴
        tickers = ["GC=F", "SI=F", "KRW=X"]
        data = yf.download(tickers, period="5d", interval="1m")['Close']
        df = data.ffill().rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
        
        # 실시간 국내 금/은 환산 (국제 시세 기반)
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        return df
    except: return None

df = load_realtime_data()

# 헤더 부분
col_t1, col_t2 = st.columns([2, 1])
with col_t1:
    st.markdown('<p class="gs-title">⚡ 실시간 금/은 시세 리포트</p>', unsafe_allow_html=True)
with col_t2:
    st.markdown(f'<p style="text-align:right; margin-top:30px;"><span class="live-indicator">● LIVE</span> <br><span style="font-size:11px; color:#888;">{datetime.now().strftime("%H:%M:%S")}</span></p>', unsafe_allow_html=True)

if df is not None:
    c = df.iloc[-1]
    p = df.iloc[-2] # 1분 전 데이터와 비교

    # --- 실시간 금 시세 ---
    st.markdown('<p class="main-title">🟡 실시간 국제/국내 금 시세</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""<div class="price-card">
            <div class="label-text">국내 금 1돈 (환산 시세)</div>
            <div class="value-text">{int(c['gold_don']):,}<small style="font-size:14px;">원</small></div>
            {get_delta_html(c['gold_don'], p['gold_don'])}
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="price-card" style="border-top-color: #eee;">
            <div class="label-text">국제 금 (Real-time)</div>
            <div class="value-text"><small style="font-size:14px;">$</small>{c['gold']:.1f}</div>
            {get_delta_html(c['gold'], p['gold'], True)}
        </div>""", unsafe_allow_html=True)

    fig_g = px.line(df.tail(100), y='gold_don', template="plotly_dark") # 최근 100분간의 흐름
    fig_g.update_traces(line_color='#f1c40f')
    fig_g.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig_g, use_container_width=True)

    # --- 실시간 환율 정보 ---
    st.markdown(f"""
        <div style="text-align: right; padding: 10px; background: #2b2b2b; color: #ddd; border-radius: 8px; margin: 10px 0;">
            <span style="font-size: 12px;">현재 환율: <b>{c['ex']:.2f}원</b></span>
            <span style="font-size: 11px;"> {get_delta_html(c['ex'], p['ex'], True)}</span>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- 실시간 은 시세 ---
    st.markdown('<p class="main-title">⚪ 실시간 국제/국내 은 시세</p>', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        st.markdown(f"""<div class="price-card" style="border-top-color: #adb5bd;">
            <div class="label-text">국내 은 1돈 (환산 시세)</div>
            <div class="value-text">{int(c['silver_don']):,}<small style="font-size:14px;">원</small></div>
            {get_delta_html(c['silver_don'], p['silver_don'])}
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="price-card" style="border-top-color: #eee;">
            <div class="label-text">국제 은 (Real-time)</div>
            <div class="value-text"><small style="font-size:14px;">$</small>{c['silver']:.2f}</div>
            {get_delta_html(c['silver'], p['silver'], True)}
        </div>""", unsafe_allow_html=True)

    fig_s = px.line(df.tail(100), y='silver_don', template="plotly_dark")
    fig_s.update_traces(line_color='#adb5bd')
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig_s, use_container_width=True)

    st.caption("※ 본 시세는 국제 마켓 데이터를 기반으로 1분마다 자동 계산됩니다. (Yahoo Finance Real-time Feed)")
else:
    st.error("실시간 데이터를 연결할 수 없습니다.")
