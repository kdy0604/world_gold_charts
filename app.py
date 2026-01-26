import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime
import pytz
from pykrx import stock  # pykrx 추가

# 1. 페이지 설정 및 스타일
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
    .ref-time { font-size: 11px; color: #888; display: block; margin-top: 5px; }
    .fx-container { background-color: #f1f3f9; padding: 10px 15px; border-radius: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #dbe2ef; }
    </style>
    """, unsafe_allow_html=True)

# --- 등락 표시 유틸리티 ---
def get_delta_html(curr, prev, prefix=""):
    if prev == 0: return ""
    diff = curr - prev
    pct = (diff / prev) * 100
    color = "up" if diff >= 0 else "down"
    sign = "▲" if diff >= 0 else "▼"
    return f'<span class="delta {color}">{sign} {prefix}{abs(diff):,.2f} ({pct:+.2f}%)</span>'

def update_chart_layout(fig, y_min, y_max):
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(range=[y_min, y_max], fixedrange=True, title=None),
        xaxis=dict(fixedrange=True, title=None),
        dragmode=False, hovermode="x unified", template="plotly_white")
    return fig

# --- [NEW] pykrx를 이용한 국내 금 실시간 시세 ---
def get_krx_realtime_pykrx():
    try:
        # KRX 금 시장의 종목코드 'KM'은 금 99.99K 1g을 의미함
        now_str = datetime.now(KST).strftime("%Y%m%d")
        # 최근 1일치 시세를 가져와 마지막 체결가 반환
        df = stock.get_market_ohlcv(now_str, now_str, "KGS00C003001", market="GOLD") # 금 99.99_1kg 종목코드
        if df.empty:
            # 장 전이거나 휴일이면 마지막 영업일 데이터 가져오기
            df = stock.get_market_ohlcv("20250101", now_str, "KGS00C003001", market="GOLD")
        
        last_price_1g = df['종가'].iloc[-1]
        return float(last_price_1g) * 3.75 # 1돈 환산
    except:
        return None

# --- 데이터 로드: 국내 금 이력 (공공데이터) ---
@st.cache_data(ttl=3600)
def get_krx_history_data():
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    raw_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    try:
        res = requests.get(url, params={'serviceKey': unquote(raw_key), 'numOfRows': '400', 'resultType': 'xml'}, timeout=10)
        root = ET.fromstring(res.content)
        data_list = []
        for item in root.findall('.//item'):
            if "금" in item.findtext('itmsNm', '') and "99.99" in item.findtext('itmsNm', ''):
                data_list.append({'날짜': pd.to_datetime(item.findtext('basDt')), '종가': float(item.findtext('clpr', 0)) * 3.75})
        return pd.DataFrame(data_list).drop_duplicates('날짜').set_index('날짜').sort_index()
    except: return None

# --- 데이터 로드: 국제 금/은/환율 (Yahoo Finance) ---
@st.cache_data(ttl=120)
def get_intl_data():
    try:
        df = yf.download(["GC=F", "SI=F", "KRW=X"], period="3mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill().dropna()
        for t, col in zip(["GC=F", "SI=F", "KRW=X"], ["gold", "silver", "ex"]):
            live = yf.Ticker(t).fast_info.last_price
            if live > 0: df.iloc[-1, df.columns.get_loc(col)] = live
        df['gold_don'] = (df['gold'] / 31.1034) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1034) * df['ex'] * 3.75
        return df, datetime.now(KST).strftime('%Y-%m-%d %H:%M')
    except: return None, None

# 데이터 호출
df_intl, intl_time = get_intl_data()
df_history = get_krx_history_data() # 공공데이터 이력
realtime_kr = get_krx_realtime_pykrx() # pykrx 실시간

st.markdown('<p class="gs-title">📊 금/은 마켓 실시간 대시보드</p>', unsafe_allow_html=True)

if df_intl is not None:
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    
    # --- 환율 정보 섹션 ---
    st.markdown(f"""
        <div class="fx-container">
            <span style="font-size:14px; font-weight:700;">원/달러 환율</span>
            <div style="text-align:right;">
                <span style="font-size:18px; font-weight:800;">{curr['ex']:,.2f}원</span><br>
                {get_delta_html(curr['ex'], prev['ex'])}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- [1] 국제 금 시세 ---
    st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: st.markdown(f'<div class="price-box"><span class="val-sub">국제 (1oz)</span><span class="val-main">${curr["gold"]:,.2f}</span>{get_delta_html(curr["gold"], prev["gold"], "$")}</div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="price-box"><span class="val-sub">국내환산 (1돈)</span><span class="val-main">{int(curr["gold_don"]):,}원</span>{get_delta_html(curr["gold_don"], prev["gold_don"])}</div>', unsafe_allow_html=True)

    t1, t2 = st.tabs(["온스당 달러 ($/oz)", "돈당 원화 (₩/돈)"])
    with t1: st.plotly_chart(update_chart_layout(px.line(df_intl, y='gold'), df_intl['gold'].min()*0.99, df_intl['gold'].max()*1.01), use_container_width=True)
    with t2: st.plotly_chart(update_chart_layout(px.line(df_intl, y='gold_don').update_traces(line_color='#f1c40f'), df_intl['gold_don'].min()*0.99, df_intl['gold_don'].max()*1.01), use_container_width=True)

# --- [2] 국내 금 시세 (KRX) ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_history is not None:
    h_curr, h_prev = df_history['종가'].iloc[-1], df_history['종가'].iloc[-2]
    # pykrx 데이터가 있으면 우선 사용, 없으면 공공데이터 마지막 값 사용
    display_price = realtime_kr if realtime_kr else h_curr
    
    st.markdown(f"""
        <div class="price-box" style="margin-bottom:15px;">
            <span class="val-sub">{"pykrx 실시간" if realtime_kr else "KRX 마지막 종가"} (1돈 기준)</span>
            <span class="val-main" style="color:#d9534f;">{int(display_price):,}원</span>
            {get_delta_html(display_price, h_prev)}
            <span class="ref-time">차트 데이터: 공공데이터포털 제공 ({df_history.index[-1].strftime('%Y-%m-%d')})</span>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(update_chart_layout(px.area(df_history, y='종가').update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)'), df_history['종가'].min()*0.98, df_history['종가'].max()*1.02), use_container_width=True)

# --- [3] 국제 은 시세 ---
if df_intl is not None:
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3: st.markdown(f'<div class="price-box"><span class="val-sub">국제 (1oz)</span><span class="val-main">${curr["silver"]:,.2f}</span>{get_delta_html(curr["silver"], prev["silver"], "$")}</div>', unsafe_allow_html=True)
    with col4: st.markdown(f'<div class="price-box"><span class="val-sub">국내환산 (1돈)</span><span class="val-main">{int(curr["silver_don"]):,}원</span>{get_delta_html(curr["silver_don"], prev["silver_don"])}</div>', unsafe_allow_html=True)

    s1, s2 = st.tabs(["온스당 달러 ($/oz)", "돈당 원화 (₩/돈)"])
    with s1: st.plotly_chart(update_chart_layout(px.line(df_intl, y='silver').update_traces(line_color='#adb5bd'), df_intl['silver'].min()*0.95, df_intl['silver'].max()*1.05), use_container_width=True)
    with s2: st.plotly_chart(update_chart_layout(px.line(df_intl, y='silver_don').update_traces(line_color='#adb5bd'), df_intl['silver_don'].min()*0.95, df_intl['silver_don'].max()*1.05), use_container_width=True)
