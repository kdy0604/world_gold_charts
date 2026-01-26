import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# 1. 페이지 설정 및 스타일
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

st.markdown("""
    <style>
    .gs-title { font-size: 22px; font-weight: 800; margin-bottom: 10px; color: #1e1e1e; }
    .main-title { font-size: 17px; font-weight: 700; margin-top: 25px; margin-bottom: 2px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .sub-time { font-size: 11px; color: #888; margin-bottom: 12px; padding-left: 15px; }
    
    /* 모바일 한 줄 레이아웃 */
    .mobile-row { 
        display: flex; justify-content: space-between; align-items: center; 
        background-color: #f8f9fa; padding: 12px 15px; border-radius: 10px; 
        border: 1px solid #eee; margin-bottom: 8px;
    }
    .price-label { font-size: 13px; color: #666; font-weight: 600; }
    .price-val { font-size: 17px; font-weight: 800; color: #111; text-align: right; }
    .delta { font-size: 11px; font-weight: 600; display: block; }
    .up { color: #d9534f; } .down { color: #0275d8; }
    
    .fx-bar { background-color: #f1f3f9; padding: 12px 15px; border-radius: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #dbe2ef; }
    </style>
    """, unsafe_allow_html=True)

# --- [핵심] 네이버 JSON API 호출 함수 ---
@st.cache_data(ttl=30)
def fetch_naver_price(item_code="FX_USDKRW"):
    """
    item_code 예시: 
    - FX_USDKRW: 원달러 환율
    - CMDT_GD: 국제 금 (LBMA)
    - CMDT_SI: 국제 은
    """
    url = f"https://m.stock.naver.com/api/marketindex/price/{item_code}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        return resp.json()
    except: return None

# --- 국내 금 실시간 (네이버 금현물 API) ---
@st.cache_data(ttl=30)
def fetch_domestic_gold():
    # 네이버 금현물(KRX금) 실시간 API 엔드포인트
    url = "https://m.stock.naver.com/api/marketindex/metals/KORSV/price"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        data = requests.get(url, headers=headers, timeout=5).json()
        return data
    except: return None

def get_delta_html(close, change):
    color = "up" if change >= 0 else "down"
    sign = "▲" if change >= 0 else "▼"
    pct = (change / (close - change)) * 100
    return f'<span class="delta {color}">{sign} {abs(change):,.2f} ({pct:+.2f}%)</span>'

# 데이터 가져오기
fx_data = fetch_naver_price("FX_USDKRW")
int_gold = fetch_naver_price("CMDT_GD")
int_silver = fetch_naver_price("CMDT_SI")
dom_gold = fetch_domestic_gold()
update_time = datetime.now(KST).strftime('%H:%M:%S')

st.markdown('<p class="gs-title">📊 금/은 마켓 실시간 대시보드</p>', unsafe_allow_html=True)

# 1. 환율 바
if fx_data:
    st.markdown(f'''
        <div class="fx-bar">
            <span style="font-weight:700; font-size:14px;">원/달러 환율</span>
            <div style="text-align:right;">
                <span style="font-size:16px; font-weight:800;">{fx_data['closePrice']}원</span><br>
                {get_delta_html(float(fx_data['closePrice'].replace(',','')), float(fx_data['changePrice'].replace(',','')))}
            </div>
        </div>
    ''', unsafe_allow_html=True)

# 2. 국제 금
st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-time">실시간 업데이트: {update_time}</p>', unsafe_allow_html=True)
if int_gold:
    price_1돈 = (float(int_gold['closePrice'].replace(',','')) / 31.1034) * float(fx_data['closePrice'].replace(',','')) * 3.75
    st.markdown(f'''
        <div class="mobile-row">
            <span class="price-label">국제 (1oz)</span>
            <div class="price-val">${int_gold['closePrice']}<br>{get_delta_html(float(int_gold['closePrice'].replace(',','')), float(int_gold['changePrice'].replace(',','')),)}</div>
        </div>
        <div class="mobile-row">
            <span class="price-label">국내환산 (1돈)</span>
            <div class="price-val">{int(price_1돈):,}원</div>
        </div>
    ''', unsafe_allow_html=True)

# 3. 국내 실시간 금 (KRX 금현물 API 데이터)
st.markdown('<p class="main-title">🇰🇷 국내 금 실시간 (KRX 금현물)</p>', unsafe_allow_html=True)
if dom_gold:
    price_don = float(dom_gold['closePrice'].replace(',','')) * 3.75
    st.markdown(f'''
        <div class="mobile-row" style="border-left: 5px solid #d9534f; background-color: #fff5f5;">
            <span class="price-label">실시간 현재가 (1돈)</span>
            <div class="price-val" style="color:#d9534f; font-size:19px;">{int(price_don):,}원<br>
            {get_delta_html(float(dom_gold['closePrice'].replace(',','')), float(dom_gold['changePrice'].replace(',','')))}</div>
        </div>
    ''', unsafe_allow_html=True)

# 4. 국제 은
st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
if int_silver:
    st.markdown(f'''
        <div class="mobile-row">
            <span class="price-label">국제 (1oz)</span>
            <div class="price-val">${int_silver['closePrice']}<br>{get_delta_html(float(int_silver['closePrice'].replace(',','')), float(int_silver['changePrice'].replace(',','')))}</div>
        </div>
    ''', unsafe_allow_html=True)
