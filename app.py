import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime
import pytz
from pykrx import stock

# 1. 페이지 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 5px; color: #1e1e1e; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 5px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 12px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-sub { font-size: 11px; color: #666; margin-bottom: 3px; display: block; }
    .delta { font-size: 12px; font-weight: 600; }
    .up { color: #d9534f; } .down { color: #0275d8; }
    </style>
    """, unsafe_allow_html=True)

# --- 등락 표시 유틸리티 ---
def get_delta_html(curr, prev, prefix=""):
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    color = "up" if diff >= 0 else "down"
    sign = "▲" if diff >= 0 else "▼"
    return f'<span class="delta {color}">{sign} {prefix}{abs(diff):,.2f} ({pct:+.2f}%)</span>'

# --- [수정] pykrx 실시간 금 시세 ---
def get_krx_realtime_pykrx():
    try:
        # 금 99.99K 1kg 종목코드: KGS00C003001
        # 가장 최근 거래일의 시세를 가져옴
        today = datetime.now(KST).strftime("%Y%m%d")
        df = stock.get_market_ohlcv(today, today, "KGS00C003001", market="GOLD")
        
        # 만약 오늘 데이터가 아직 없으면(장 전/휴일) 최근 7일 중 마지막 데이터 사용
        if df.empty:
            df = stock.get_market_ohlcv("20260119", today, "KGS00C003001", market="GOLD")
            
        last_price_1g = df['종가'].iloc[-1]
        prev_price_1g = df['종가'].iloc[-2] if len(df) > 1 else last_price_1g
        
        return last_price_1g * 3.75, prev_price_1g * 3.75
    except:
        return None, None

# --- 데이터 로드: 국내 금 이력 (공공데이터) ---
@st.cache_data(ttl=3600)
def get_krx_history():
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    raw_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    try:
        res = requests.get(url, params={'serviceKey': unquote(raw_key), 'numOfRows': '400', 'resultType': 'xml'})
        root = ET.fromstring(res.content)
        data_list = [{'날짜': pd.to_datetime(item.findtext('basDt')), '종가': float(item.findtext('clpr', 0)) * 3.75} 
                     for item in root.findall('.//item') if "금" in item.findtext('itmsNm', '')]
        return pd.DataFrame(data_list).drop_duplicates('날짜').set_index('날짜').sort_index()
    except: return None

# (국제 데이터 로드 생략 - 이전과 동일)
df_intl = ... # 생략

# 실행부
kr_now, kr_prev = get_krx_realtime_pykrx()
df_kr_history = get_krx_history()

# --- 화면 출력 ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 실시간)</p>', unsafe_allow_html=True)
if kr_now:
    st.markdown(f"""
        <div class="price-box">
            <span class="val-sub">KRX 실시간 (1돈 기준)</span>
            <span class="val-main">{int(kr_now):,}원</span>
            {get_delta_html(kr_now, kr_prev)}
        </div>
    """, unsafe_allow_html=True)

if df_kr_history is not None:
    fig = px.area(df_kr_history, y='종가')
    st.plotly_chart(fig, use_container_width=True)
