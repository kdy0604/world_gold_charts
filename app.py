import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# 1. 페이지 설정 및 스타일
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

st.markdown("""
    <style>
    .gs-title { font-size: 22px; font-weight: 800; margin-bottom: 5px; color: #1e1e1e; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 25px; margin-bottom: 2px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .mobile-row { display: flex; gap: 8px; width: 100%; margin-bottom: 5px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 10px 5px; border-radius: 12px; border: 1px solid #eee; text-align: center; min-width: 0; }
    .val-main { font-size: 16px; font-weight: 800; color: #111; display: block; white-space: nowrap; }
    .val-sub { font-size: 11px; color: #666; margin-bottom: 2px; display: block; }
    .delta { font-size: 10px; font-weight: 600; display: block; }
    .up { color: #d9534f; } .down { color: #0275d8; }
    .ref-time-integrated { font-size: 11px; color: #999; text-align: right; margin-bottom: 15px; }
    .fx-container { background-color: #f1f3f9; padding: 10px 15px; border-radius: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #dbe2ef; }
    </style>
    """, unsafe_allow_html=True)

# --- 유틸리티: 등락 표시 ---
def get_delta_html(curr, prev, prefix=""):
    if prev == 0 or curr is None: return ""
    diff = curr - prev
    pct = (diff / prev) * 100
    color = "up" if diff >= 0 else "down"
    sign = "▲" if diff >= 0 else "▼"
    return f'<span class="delta {color}">{sign}{prefix}{abs(diff):,.1f}({pct:+.2f}%)</span>'

# --- 유틸리티: 차트 레이아웃 ---
def update_chart_style(fig, df, y_min, y_max, is_won=False, is_silver=False):
    if is_won:
        # 축은 '만' 단위로 보이지만, 실제 툴팁(hover)은 원본 데이터(customdata)를 참조하여 '원' 단위로 표시
        custom_hover = "날짜: %{x}<br>가격: %{customdata:,.0f}원<extra></extra>"
    else:
        custom_hover = "날짜: %{x}<br>가격: %{y:,.2f}<extra></extra>"
        
    fig.update_traces(
        mode='lines+markers', 
        marker=dict(size=4), 
        connectgaps=True, 
        hovertemplate=custom_hover
    )
    
    fig.update_layout(
        height=280, margin=dict(l=0, r=10, t=10, b=0),
        yaxis=dict(
            range=[y_min, y_max], 
            fixedrange=True, 
            title=None, 
            ticksuffix="만" if is_won else ""
        ),
        xaxis=dict(
            range=[df.index.min(), df.index.max()], 
            fixedrange=True, 
            title=None, 
            type='date', 
            tickformat='%m-%d'
        ),
        dragmode=False, 
        hovermode="x unified", 
        template="plotly_white"
    )
    return fig

# --- 데이터 수집: 네이버 실시간 (KRX 기준) ---
def get_naver_realtime_krx():
    try:
        url = "https://m.stock.naver.com/marketindex/metals/M04020000"
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"}
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 클래스 부분 일치로 가격 태그 찾기
        price_tag = soup.select_one("strong[class*='DetailInfo_price']")
        if price_tag:
            raw_text = price_tag.get_text(strip=True)
            # "원/g" 잘라내기 로직
            clean_text = raw_text.split('원')[0].replace(',', '')
            price_1g = float(clean_text)
            return price_1g * 3.75, datetime.now(KST).strftime('%H:%M:%S')
    except Exception as e:
        print(f"Naver Scraping Error: {e}")
    return None, None

@st.cache_data(ttl=3600)
def get_krx_data():
    try:
        url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
        raw_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
        res = requests.get(url, params={'serviceKey': unquote(raw_key), 'numOfRows': '90', 'resultType': 'xml'}, timeout=10)
        root = ET.fromstring(res.content)
        data_list = []
        for item in root.findall('.//item'):
            if "금" in item.findtext('itmsNm', '') and "99.99" in item.findtext('itmsNm', ''):
                data_list.append({'날짜': pd.to_datetime(item.findtext('basDt')), '종가': float(item.findtext('clpr', 0)) * 3.75})
        df = pd.DataFrame(data_list).drop_duplicates('날짜').set_index('날짜').sort_index()
        return df, df.index[-1].strftime('%Y-%m-%d')
    except: pass
    return None, None

@st.cache_data(ttl=120)
def get_intl_data():
    try:
        # 1. 과거 3개월 일봉 데이터 가져오기 (각 날짜의 데이터는 뉴욕 17:00 종가 기준)
        # yfinance의 '1d' interval 데이터는 기본적으로 정산 종가를 제공합니다.
        df = yf.download(["GC=F", "SI=F", "KRW=X"], period="3mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill().dropna()
        
        # 2. 오늘 실시간 가격 데이터 가져오기
        for t, col in zip(["GC=F", "SI=F", "KRW=X"], ["gold", "silver", "ex"]):
            ticker = yf.Ticker(t)
            live_price = ticker.fast_info.last_price
            
            if live_price > 0:
                # 데이터프레임의 가장 마지막 행(오늘)을 실시간 가격으로 업데이트
                df.iloc[-1, df.columns.get_loc(col)] = live_price
        
        # 3. 원화 환산 (돈당 가격 계산)
        df['gold_don'] = (df['gold'] / 31.1034) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1034) * df['ex'] * 3.75
        
        # 4. 뉴욕 현지 시간 계산 (상태 표시용)
        ny_tz = pytz.timezone('America/New_York')
        ny_now = datetime.now(ny_tz)
        
        return df, ny_now.strftime('%m-%d %H:%M')
    except Exception as e:
        print(f"International Data Error: {e}")
        return None, None


