import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz

# 1. 페이지 및 시간 설정
st.set_page_config(page_title="제네바시계 마켓 (안정판)", layout="centered")
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

# 2. 유틸리티 함수
def format_delta(curr, prev):
    if pd.isna(curr) or pd.isna(prev): return ""
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    return f'<span class="{color}">{sign} {abs(diff):,.2f} ({pct:+.2f}%)</span>'

# 3. 데이터 로드 (일별 데이터 - 가장 안정적)
@st.cache_data(ttl=3600)
def get_daily_data():
    try:
        # 최근 3개월 일별 데이터 로드
        tickers = ["GC=F", "SI=F", "KRW=X"]
        df = yf.download(tickers, period="3mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill().dropna()
        
        # 1돈 환산가 계산
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        return df
    except: return None

@st.cache_data(ttl=3600)
def get_krx_data():
    try:
        url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
        # 서비스키는 그대로 사용
        params = {'serviceKey': "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a", 'numOfRows': '45', 'resultType': 'xml'}
        res = requests.get(url, params=params, timeout=10)
        root = ET.fromstring(res.text)
        items = root.findall('.//item')
        hist = []
        for i in items:
            clpr = i.find('clpr').text
            if clpr:
                hist.append({
                    '날짜': pd.to_datetime(i.find('basDt').text),
                    '종가': float(clpr) * 3.75,
                    '등락률': float(i.find('flctRt').text or 0)
                })
        return pd.DataFrame(hist).sort_values('날짜')
    except: return None

# 데이터 준비
df_intl = get_daily_data()
df_krx = get_krx_data()

st.markdown('<p class="gs-title">📊 금/은 일별 시세 리포트</p>', unsafe_allow_html=True)

# 1. 국제 금 시세
st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
if df_intl is not None and len(df_intl) >= 2:
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(curr['gold_don']):,}원</span>{format_delta(curr['gold_don'], prev['gold_don'])}</div>
            <div class="price-box"><span class="val-label">국제 가격 (1oz)</span><span class="val-main">${curr['gold']:.2f}</span>{format_delta(curr['gold'], prev['gold'])}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Y축 최적화 차트
    fig = px.line(df_intl, y='gold_don', template="plotly_white", title="최근 3개월 추이 (1돈 환산)")
    y_min, y_max = df_intl['gold_don'].min() * 0.98, df_intl['gold_don'].max() * 1.02
    fig.update_layout(height=280, margin=dict(l=0,r=0,t=30,b=0), yaxis=dict(range=[y_min, y_max], autorange=False), xaxis_title=None, yaxis_title=None)
    fig.update_traces(line_color='#f1c40f', line_width=3)
    st.plotly_chart(fig, use_container_width=True)

# 2. 국내 금 시세 (KRX)
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx is not None and not df_krx.empty:
    latest = df_krx.iloc[-1]
    st.markdown(f"""<div class="price-box" style="margin-bottom:15px;"><span class="val-label">KRX 종가 (1돈 환산)</span><span class="val-main">{int(latest['종가']):,}원</span><span class="{'up' if latest['등락률'] > 0 else 'down'}">{'▲' if latest['등락률'] > 0 else '▼'} {latest['등락률']}%</span></div>""", unsafe_allow_html=True)
    
    y_k_min, y_k_max = df_krx['종가'].min() * 0.99, df_krx['종가'].max() * 1.01
    fig_krx = px.area(df_krx, x='날짜', y='종가', template="plotly_white")
    fig_krx.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_k_min, y_k_max], autorange=False), xaxis_title=None, yaxis_title=None)
    fig_krx.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)')
    st.plotly_chart(fig_krx, use_container_width=True)

# 3. 국제 은 시세
st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
if df_intl is not None and len(df_intl) >= 2:
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(curr['silver_don']):,}원</span>{format_delta(curr['silver_don'], prev['silver_don'])}</div>
            <div class="price-box"><span class="val-label">국제 가격 (1oz)</span><span class="val-main">${curr['silver']:.2f}</span>{format_delta(curr['silver'], prev['silver'])}</div>
        </div>
    """, unsafe_allow_html=True)
    
    fig_s = px.line(df_intl, y='silver_don', template="plotly_white", title="최근 3개월 추이 (1돈 환산)")
    y_s_min, y_s_max = df_intl['silver_don'].min() * 0.95, df_intl['silver_don'].max() * 1.05
    fig_s.update_layout(height=280, margin=dict(l=0,r=0,t=30,b=0), yaxis=dict(range=[y_s_min, y_s_max], autorange=False), xaxis_title=None, yaxis_title=None)
    fig_s.update_traces(line_color='#adb5bd', line_width=3)
    st.plotly_chart(fig_s, use_container_width=True)
