import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime
import pytz

# 페이지 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

# CSS 스타일
st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 5px; color: #1e1e1e; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 5px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 12px; border-radius: 12px; border: 1px solid #eee; text-align: center; min-height: 120px; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-sub { font-size: 11px; color: #666; margin-bottom: 3px; display: block; }
    .delta { font-size: 12px; font-weight: 600; }
    .up { color: #d9534f; } .down { color: #0275d8; }
    .ref-time { font-size: 10px; color: #999; display: block; margin-top: 8px; line-height: 1.3; }
    </style>
    """, unsafe_allow_html=True)

# --- 등락 표시 함수 ---
def get_delta_html(curr, prev):
    if prev == 0 or curr is None: return ""
    diff = curr - prev
    pct = (diff / prev) * 100
    color = "up" if diff >= 0 else "down"
    sign = "▲" if diff >= 0 else "▼"
    return f'<span class="delta {color}">{sign} {abs(diff):,.0f}원 ({pct:+.2f}%)</span>'

# --- 차트 레이아웃 함수 (0f만 버그 수정) ---
def update_chart_style(fig, df, is_won=False):
    fig.update_traces(
        mode='lines+markers', 
        marker=dict(size=4),
        # 버그 수정: %{y:.0f}로 작성하여 소수점 없이 '만'만 붙게 함
        hovertemplate="날짜: %{x}<br>가격: %{y:.1f}만<extra></extra>" if is_won else "날짜: %{x}<br>가격: %{y:,.2f}<extra></extra>"
    )
    fig.update_layout(
        height=300, margin=dict(l=0, r=20, t=10, b=0),
        yaxis=dict(fixedrange=True, title=None, ticksuffix="만" if is_won else ""),
        xaxis=dict(range=[df.index.min(), df.index.max()], fixedrange=True, title=None, type='date', tickformat='%m-%d'),
        dragmode=False, hovermode="x unified", template="plotly_white"
    )
    return fig

# --- 국내 금 데이터 (공공데이터 API) ---
@st.cache_data(ttl=3600)
def get_krx_data():
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    raw_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    try:
        res = requests.get(url, params={'serviceKey': unquote(raw_key), 'numOfRows': '400', 'resultType': 'xml'}, timeout=10)
        root = ET.fromstring(res.content)
        data_list = []
        for item in root.findall('.//item'):
            if "금" in item.findtext('itmsNm', '') and "99.99" in item.findtext('itmsNm', ''):
                data_list.append({'날짜': pd.to_datetime(item.findtext('basDt')), '종가': float(item.findtext('clpr', 0)) * 3.75})
        df = pd.DataFrame(data_list).drop_duplicates('날짜').set_index('날짜').sort_index()
        return df, df.index[-1].strftime('%Y-%m-%d')
    except: return None, None

# --- ETF 등락률 기반 실시간 예측 ---
def get_estimated_realtime(krx_prev_close):
    try:
        ticker = yf.Ticker("319660.KS")
        hist = ticker.history(period="5d") # 안정적으로 최근 데이터 수집
        if len(hist) >= 2:
            etf_prev = hist['Close'].iloc[-2] # 전일 종가
            etf_curr = ticker.fast_info.last_price # 현재가
            change_rate = (etf_curr - etf_prev) / etf_prev
            predicted = krx_prev_close * (1 + change_rate)
            return predicted, datetime.now(KST).strftime('%H:%M:%S')
    except: pass
    return None, None

# --- 국제 시세 데이터 ---
@st.cache_data(ttl=120)
def get_intl_data():
    try:
        df = yf.download(["GC=F", "SI=F", "KRW=X"], period="3mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill().dropna()
        return df, datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
    except: return None, None

# 데이터 로드
df_krx, krx_last_date = get_krx_data()
df_intl, intl_time = get_intl_data()

st.markdown('<p class="gs-title">📊 금/은 마켓 실시간 대시보드</p>', unsafe_allow_html=True)

# 1. 국제 시세 (기존 유지)
if df_intl is not None:
    curr = df_intl.iloc[-1]
    st.markdown('<p class="main-title">🟡 국제 금/환율</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: st.markdown(f'<div class="price-box"><span class="val-sub">국제 금 (1oz)</span><span class="val-main">${curr["gold"]:,.2f}</span></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="price-box"><span class="val-sub">원/달러 환율</span><span class="val-main">{curr["ex"]:,.2f}원</span></div>', unsafe_allow_html=True)

# 2. 국내 금 시세 (요청하신 등락 로직 적용)
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (실시간 예측)</p>', unsafe_allow_html=True)
if df_krx is not None:
    k_last_close = df_krx['종가'].iloc[-1]
    realtime_val, update_t = get_estimated_realtime(k_last_close)
    
    # 상단 박스 표시
    disp_val = realtime_val if realtime_val else k_last_close
    st.markdown(f"""
        <div class="price-box" style="margin-bottom:15px;">
            <span class="val-sub">{"실시간 예측 (ETF 등락반영)" if realtime_val else "마지막 종가"} (1돈)</span>
            <span class="val-main" style="color:#d9534f; font-size:28px;">{int(disp_val):,}원</span>
            {get_delta_html(disp_val, df_krx['종가'].iloc[-2])}
            <span class="ref-time">기준: {krx_last_date} 종가 대비 ETF 변동 적용<br>업데이트: {update_t if update_t else "정보없음"}</span>
        </div>
    """, unsafe_allow_html=True)

    # 차트 표시 (만원 단위)
    df_krx_won = df_krx[['종가']] / 10000
    fig = px.area(df_krx_won, y='종가').update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)')
    st.plotly_chart(update_chart_style(fig, df_krx_won, is_won=True), use_container_width=True, config={'displayModeBar': False})
