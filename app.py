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

# 1. 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 5px; color: #1e1e1e; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 5px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 22px; font-weight: 800; color: #d9534f; display: block; }
    .val-sub { font-size: 12px; color: #666; margin-bottom: 5px; display: block; }
    .ref-time { font-size: 11px; color: #888; display: block; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 네이버 실시간 국내 금 시세 파싱 ---
def get_naver_realtime():
    try:
        url = "https://finance.naver.com/marketindex/goldDetail.naver"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        price_1g = soup.select_one("div.day_data p.no_today em span.blind").text
        return float(price_1g.replace(',', '')) * 3.75
    except:
        return None

# --- 3. 국내 데이터 로드 (공공데이터 포털) ---
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
                data_list.append({
                    '날짜': pd.to_datetime(item.findtext('basDt')),
                    '종가': float(item.findtext('clpr', 0)) * 3.75
                })
        df = pd.DataFrame(data_list).drop_duplicates('날짜').set_index('날짜').sort_index()
        return df
    except:
        return None

# --- 4. 국제 데이터 로드 (금/은/환율) ---
@st.cache_data(ttl=120)
def get_intl_data():
    try:
        df = yf.download(["GC=F", "SI=F", "KRW=X"], period="3mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill().dropna()
        # 실시간 데이터 갱신
        for t, col in zip(["GC=F", "SI=F", "KRW=X"], ["gold", "silver", "ex"]):
            live = yf.Ticker(t).fast_info.last_price
            if live > 0: df.iloc[-1, df.columns.get_loc(col)] = live
        df['gold_don'] = (df['gold'] / 31.1034) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1034) * df['ex'] * 3.75
        return df
    except: return None

# 데이터 호출
df_krx = get_krx_data()
df_intl = get_intl_data()
realtime_kr = get_naver_realtime()

st.markdown('<p class="gs-title">📊 금/은 마켓 실시간 대시보드</p>', unsafe_allow_html=True)

# --- [섹션 1] 국내 금 시세 ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx is not None:
    last_confirmed_price = df_krx['종가'].iloc[-1]
    last_date = df_krx.index[-1].strftime('%Y-%m-%d')
    
    # 상단 금액 결정: 실시간(89만)이 있으면 실시간, 없으면 마지막 종가
    display_price = realtime_kr if realtime_kr else last_confirmed_price
    price_tag = "실시간 현재가" if realtime_kr else "마지막 확정가"
    
    st.markdown(f"""
        <div class="price-box">
            <span class="val-sub">{price_tag} (1돈 기준)</span>
            <span class="val-main">{int(display_price):,}<small>원</small></span>
            <span class="ref-time">공식 데이터 기준: {last_date}</span>
            {"<span style='color:#0275d8; font-size:11px;'>* 네이버 실시간 연동 중</span>" if realtime_kr else ""}
        </div>
    """, unsafe_allow_html=True)
    
    # 차트 (공공데이터 자료까지만 표시)
    fig_k = px.area(df_krx, y='종가')
    fig_k.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), template="plotly_white",
                        yaxis=dict(range=[df_krx['종가'].min()*0.99, df_krx['종가'].max()*1.01], title=None),
                        xaxis=dict(title=None))
    st.plotly_chart(fig_k.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)'), use_container_width=True)

# --- [섹션 2] 국제 금/은 시세 ---
if df_intl is not None:
    curr = df_intl.iloc[-1]
    st.markdown(f'<p class="main-title">🟡 국제 금 시세 (Gold) <span style="font-size:12px; font-weight:400; color:#888;">환율: {curr["ex"]:,.2f}원</span></p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: st.markdown(f'<div class="price-box"><span class="val-sub">국제 (1oz)</span><span style="font-size:18px; font-weight:800;">${curr["gold"]:,.2f}</span></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="price-box"><span class="val-sub">국내환산 (1돈)</span><span style="font-size:18px; font-weight:800;">{int(curr["gold_don"]):,}원</span></div>', unsafe_allow_html=True)
    
    fig_g = px.line(df_intl, y='gold_don')
    fig_g.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), template="plotly_white", yaxis=dict(title=None), xaxis=dict(title=None))
    st.plotly_chart(fig_g.update_traces(line_color='#f1c40f'), use_container_width=True)

    st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
    fig_s = px.line(df_intl, y='silver_don')
    fig_s.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), template="plotly_white", yaxis=dict(title=None), xaxis=dict(title=None))
    st.plotly_chart(fig_s.update_traces(line_color='#adb5bd'), use_container_width=True)
