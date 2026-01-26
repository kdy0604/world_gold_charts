import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="실시간 금/은 종합 리포트", layout="centered")

st.markdown("""
    <style>
    .block-container { max-width: 90% !important; padding-left: 5% !important; padding-right: 5% !important; }
    .gs-title { font-size: clamp(20px, 7vw, 30px) !important; font-weight: 700; margin-top: 20px; margin-bottom: 5px; line-height: 1.2 !important; }
    .live-indicator { color: #ff0000; font-weight: 800; font-size: 12px; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    .main-title { font-size: 19px; font-weight: 700; margin-top: 25px; margin-bottom: 12px; }
    .custom-container { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 15px; }
    .custom-item { flex: 1; background-color: #f8f9fa; padding: 12px 5px; border-radius: 12px; text-align: center; border-left: 4px solid #dee2e6; min-width: 0; }
    .gold-box { background-color: #fff9e6; border-left-color: #f1c40f; }
    .silver-box { background-color: #f1f3f5; border-left-color: #adb5bd; }
    .value-text { font-size: 16px; font-weight: 800; color: #1E1E1E; }
    .delta-text { font-size: 11px; font-weight: 600; margin-top: 3px; display: block; }
    .ex-info { text-align: right; padding: 10px; background: #f8f9fa; border-radius: 8px; margin-bottom: 20px; border: 1px solid #eee; }
    .up { color: #d9534f; } .down { color: #0275d8; } .equal { color: #666; }
    </style>
    """, unsafe_allow_html=True)

# 2. 등락 계산 함수
def get_delta_html(curr, prev, is_currency=False):
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    if abs(diff) < 0.0001: return '<span class="delta-text equal">- 0 (0.00%)</span>'
    sign = "▲" if diff > 0 else "▼"
    color = "up" if diff > 0 else "down"
    v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
    return f'<span class="delta-text {color}">{sign} {v} ({pct:+.2f}%)</span>'

# 3. 실시간 데이터 로드 (1분 단위)
@st.cache_data(ttl=60)
def load_full_realtime_data():
    try:
        tickers = ["GC=F", "SI=F", "KRW=X"]
        data = yf.download(tickers, period="2d", interval="1m")['Close']
        df = data.ffill().rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        return df
    except: return None

df = load_full_realtime_data()

# 헤더
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.markdown('<p class="gs-title">💰 실시간 금/은 종합 리포트</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:13px; color:#888; margin-top:-10px;">by 제네바시계</p>', unsafe_allow_html=True)
with col_h2:
    st.markdown(f'<p style="text-align:right;"><span class="live-indicator">● LIVE</span><br><span style="font-size:11px; color:#666;">{datetime.now().strftime("%H:%M:%S")}</span></p>', unsafe_allow_html=True)

if df is not None:
    c = df.iloc[-1]
    p = df.iloc[-2]

    # --- 1. 국제 금 시세 (USD) ---
    st.markdown('<p class="main-title">🟡 국제 금 시세 (Real-time USD)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item">
                <div style="font-size:11px; color:#666;">국제 금 (USD/oz)</div>
                <div class="value-text">${c['gold']:.2f}</div>
                {get_delta_html(c['gold'], p['gold'], True)}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    fig_g_intl = px.line(df.tail(60), y='gold')
    fig_g_intl.update_traces(line_color='#ffa500', line_width=2)
    fig_g_intl.update_layout(xaxis_title=None, yaxis_title=None, height=180, margin=dict(l=0,r=0,t=10,b=0), hovermode="x")
    st.plotly_chart(fig_g_intl, use_container_width=True, config={'displayModeBar': False})

    # 환율 정보 (차트 아래 배치)
    st.markdown(f"""
        <div class="ex-info">
            <span style="font-size: 12px; color: #666;">실시간 환율: <b>{c['ex']:.2f}원</b></span>
            <span> {get_delta_html(c['ex'], p['ex'], True)}</span>
        </div>
    """, unsafe_allow_html=True)

    # --- 2. 국내 금 시세 (KRW 환산) ---
    st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (실시간 환산가)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item gold-box">
                <div style="font-size:11px; color:#666;">국내 금 1돈 (3.75g)</div>
                <div class="value-text">{int(c['gold_don']):,}원</div>
                {get_delta_html(c['gold_don'], p['gold_don'])}
            </div>
        </div>
    """, unsafe_allow_html=True)

    fig_g_krw = px.line(df.tail(60), y='gold_don')
    fig_g_krw.update_traces(line_color='#f1c40f', line_width=2)
    fig_g_krw.update_layout(xaxis_title=None, yaxis_title=None, height=180, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x")
    st.plotly_chart(fig_g_krw, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    # --- 3. 국제 은 시세 (Silver) ---
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (Real-time)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item silver-box">
                <div style="font-size:11px; color:#666;">은 1돈 (원화 환산)</div>
                <div class="value-text">{int(c['silver_don']):,}원</div>
                {get_delta_html(c['silver_don'], p['silver_don'])}
            </div>
            <div class="custom-item">
                <div style="font-size:11px; color:#666;">국제 은 (USD/oz)</div>
                <div class="value-text">${c['silver']:.2f}</div>
                {get_delta_html(c['silver'], p['silver'], True)}
            </div>
        </div>
    """, unsafe_allow_html=True)

    fig_s = px.line(df.tail(60), y='silver_don')
    fig_s.update_traces(line_color='#adb5bd', line_width=2)
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=180, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x")
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

    st.caption("※ 1분 단위 실시간 마켓 피드 데이터입니다. (Yahoo Finance 제공)")
else:
    st.error("데이터 서버 연결 중입니다...")
