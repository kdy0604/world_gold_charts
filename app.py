import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz

# 1. 페이지 및 시간 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')
now_kst = datetime.now(KST)

st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 20px; color: #1e1e1e; border-bottom: 2px solid #333; padding-bottom: 10px; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .fx-container { background-color: #f1f3f9; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #dbe2ef; display: flex; justify-content: space-between; align-items: center; }
    .fx-label { font-size: 13px; color: #444; font-weight: 600; }
    .fx-value { font-size: 16px; font-weight: 800; color: #111; }
    .price-container { display: flex; gap: 10px; margin-bottom: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-label { font-size: 11px; color: #666; margin-bottom: 5px; display: block; }
    .up { color: #d9534f; font-weight: 600; font-size: 12px; } .down { color: #0275d8; font-weight: 600; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 등락 표시 함수
def format_delta(curr, prev, is_fx=False):
    if pd.isna(curr) or pd.isna(prev): return ""
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    if is_fx:
        return f'<span class="{color}" style="font-size:14px; margin-left:8px;">{sign} {abs(diff):,.2f} ({pct:+.2f}%)</span>'
    return f'<span class="{color}">{sign} {abs(diff):,.2f} ({pct:+.2f}%)</span>'

# 3. 데이터 로드 (안정적인 일별 데이터)
@st.cache_data(ttl=3600)
def get_market_data():
    try:
        tickers = ["GC=F", "SI=F", "KRW=X"]
        df = yf.download(tickers, period="3mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill().dropna()
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        return df
    except: return None

@st.cache_data(ttl=3600)
def get_krx_data():
    try:
        # 공공데이터포털 KRX 금시세 API
        url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService"
        params = {'serviceKey': "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a", 'numOfRows': '45', 'resultType': 'xml'}
        res = requests.get(url, params=params, timeout=10)
        root = ET.fromstring(res.text)
        items = root.findall('.//item')
        if not items: return None
        
        hist = []
        for i in items:
            clpr_node = i.find('clpr')
            date_node = i.find('basDt')
            if clpr_node is not None and date_node is not None:
                hist.append({
                    '날짜': pd.to_datetime(date_node.text),
                    '종가': float(clpr_node.text) * 3.75,
                    '등락률': float(i.find('flctRt').text or 0)
                })
        return pd.DataFrame(hist).sort_values('날짜')
    except: return None

# 데이터 준비
df_intl = get_market_data()
df_krx = get_krx_data()

st.markdown('<p class="gs-title">📊 금/은 마켓 대시보드</p>', unsafe_allow_html=True)

# --- 1. 국제 금 & 환율 섹션 ---
if df_intl is not None and len(df_intl) >= 2:
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    
    # 환율 정보 표시 (차트 위)
    st.markdown(f"""
        <div class="fx-container">
            <span class="fx-label">현재 원/달러 환율 (USD/KRW)</span>
            <div style="display:flex; align-items:center;">
                <span class="fx-value">{curr['ex']:,.2f}원</span>
                {format_delta(curr['ex'], prev['ex'], is_fx=True)}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(curr['gold_don']):,}원</span>{format_delta(curr['gold_don'], prev['gold_don'])}</div>
            <div class="price-box"><span class="val-label">국제 가격 (1oz)</span><span class="val-main">${curr['gold']:.2f}</span>{format_delta(curr['gold'], prev['gold'])}</div>
        </div>
    """, unsafe_allow_html=True)
    
    fig = px.line(df_intl, y='gold_don', template="plotly_white")
    y_min, y_max = df_intl['gold_don'].min() * 0.98, df_intl['gold_don'].max() * 1.02
    fig.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_min, y_max], autorange=False), xaxis_title=None, yaxis_title=None)
    fig.update_traces(line_color='#f1c40f', line_width=3)
    st.plotly_chart(fig, use_container_width=True)

# --- 2. 국내 금 시세 (KRX) ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx is not None and not df_krx.empty:
    latest = df_krx.iloc[-1]
    st.markdown(f"""<div class="price-box" style="margin-bottom:15px;"><span class="val-label">KRX 종가 (1돈 환산)</span><span class="val-main">{int(latest['종가']):,}원</span><span class="{'up' if latest['등락률'] > 0 else 'down'}">{'▲' if latest['등락률'] > 0 else '▼'} {latest['등락률']}%</span></div>""", unsafe_allow_html=True)
    
    y_k_min, y_k_max = df_krx['종가'].min() * 0.99, df_krx['종가'].max() * 1.01
    fig_krx = px.area(df_krx, x='날짜', y='종가', template="plotly_white")
    fig_krx.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_k_min, y_k_max], autorange=False), xaxis_title=None, yaxis_title=None)
    fig_krx.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)')
    st.plotly_chart(fig_krx, use_container_width=True)
else:
    st.warning("국내(KRX) 데이터를 불러오는 데 실패했습니다. 서비스 키 권한이나 API 상태를 확인해주세요.")

# --- 3. 국제 은 시세 ---
st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
if df_intl is not None and len(df_intl) >= 2:
    curr_s = df_intl.iloc[-1]
    prev_s = df_intl.iloc[-2]
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(curr_s['silver_don']):,}원</span>{format_delta(curr_s['silver_don'], prev_s['silver_don'])}</div>
            <div class="price-box"><span class="val-label">국제 가격 (1oz)</span><span class="val-main">${curr_s['silver']:.2f}</span>{format_delta(curr_s['silver'], prev_s['silver'])}</div>
        </div>
    """, unsafe_allow_html=True)
    
    fig_s = px.line(df_intl, y='silver_don', template="plotly_white")
    y_s_min, y_s_max = df_intl['silver_don'].min() * 0.95, df_intl['silver_don'].max() * 1.05
    fig_s.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_s_min, y_s_max], autorange=False), xaxis_title=None, yaxis_title=None)
    fig_s.update_traces(line_color='#adb5bd', line_width=3)
    st.plotly_chart(fig_s, use_container_width=True)
