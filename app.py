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
    /* 제목 및 공통 스타일 */
    .gs-title { font-size: 22px; font-weight: 800; margin-bottom: 10px; color: #1e1e1e; }
    .main-title { font-size: 17px; font-weight: 700; margin-top: 25px; margin-bottom: 2px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .sub-time { font-size: 11px; color: #888; margin-bottom: 12px; padding-left: 15px; }
    
    /* 모바일에서 한 줄로 보이도록 하는 슬림 박스 디자인 */
    .mobile-price-row { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        background-color: #f8f9fa; 
        padding: 12px 15px; 
        border-radius: 10px; 
        border: 1px solid #eee; 
        margin-bottom: 8px;
    }
    .price-label { font-size: 12px; color: #666; font-weight: 600; }
    .price-value { font-size: 17px; font-weight: 800; color: #111; text-align: right; }
    .delta-small { font-size: 11px; font-weight: 600; display: block; }
    
    .up { color: #d9534f; } .down { color: #0275d8; }
    
    /* 환율 컨테이너 */
    .fx-container { background-color: #f1f3f9; padding: 12px 15px; border-radius: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #dbe2ef; }
    </style>
    """, unsafe_allow_html=True)

# --- 유틸리티: 등락 표시 ---
def get_delta_text(curr, prev, prefix=""):
    if prev == 0 or curr is None: return ""
    diff = curr - prev
    pct = (diff / prev) * 100
    color = "up" if diff >= 0 else "down"
    sign = "▲" if diff >= 0 else "▼"
    return f'<span class="delta-small {color}">{sign} {prefix}{abs(diff):,.2f} ({pct:+.2f}%)</span>'

# --- 유틸리티: 차트 레이아웃 (0f만 버그 완전 해결) ---
def update_chart_style(fig, df, y_min, y_max, is_won=False, is_silver=False):
    # hovertemplate 문법 수정: .0f 또는 .1f 뒤에 '만'을 붙임
    if is_won:
        hover_fmt = "날짜: %{x}<br>가격: %{y:.1f}만<extra></extra>" if is_silver else "날짜: %{x}<br>가격: %{y:.0f}만<extra></extra>"
    else:
        hover_fmt = "날짜: %{x}<br>가격: %{y:,.2f}<extra></extra>"

    fig.update_traces(mode='lines+markers', marker=dict(size=4), connectgaps=True, hovertemplate=hover_fmt)
    fig.update_layout(
        height=280, margin=dict(l=0, r=10, t=10, b=0),
        yaxis=dict(range=[y_min, y_max], fixedrange=True, title=None, ticksuffix="만" if is_won else ""),
        xaxis=dict(range=[df.index.min(), df.index.max()], fixedrange=True, title=None, type='date', tickformat='%m-%d'),
        dragmode=False, hovermode="x unified", template="plotly_white"
    )
    return fig

# --- 데이터 수집 함수 (기본 유지) ---
def get_naver_realtime():
    try:
        url = "https://finance.naver.com/marketindex/goldDetail.naver"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        price_tag = soup.select_one("div.day_data p.no_today em span.blind")
        if price_tag:
            return float(price_tag.text.replace(',', '')) * 3.75, datetime.now(KST).strftime('%H:%M:%S')
    except: pass
    return None, None

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
        return df, datetime.now(KST).strftime('%H:%M:%S')
    except: return None, None

# 데이터 로드
df_intl, intl_time = get_intl_data()
df_krx, krx_last_date = get_krx_data()
realtime_kr, naver_time = get_naver_realtime()

st.markdown('<p class="gs-title">📊 금/은 마켓 대시보드</p>', unsafe_allow_html=True)

# --- [1] 환율 ---
if df_intl is not None:
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    st.markdown(f'''
        <div class="fx-container">
            <span style="font-weight:700; font-size:14px;">원/달러 환율</span>
            <div style="text-align:right;">
                <span style="font-size:16px; font-weight:800;">{curr["ex"]:,.2f}원</span><br>
                {get_delta_text(curr["ex"], prev["ex"])}
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # --- [2] 국제 금 ---
    st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-time">수집: {intl_time} (환율기준 포함)</p>', unsafe_allow_html=True)
    
    st.markdown(f'''
        <div class="mobile-price-row">
            <span class="price-label">국제 (1oz)</span>
            <div class="price-value">${curr["gold"]:,.1f}<br>{get_delta_text(curr["gold"], prev["gold"], "$")}</div>
        </div>
        <div class="mobile-price-row">
            <span class="price-label">국내환산 (1돈)</span>
            <div class="price-value">{int(curr["gold_don"]):,}원<br>{get_delta_text(curr["gold_don"], prev["gold_don"])}</div>
        </div>
    ''', unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["$/oz 차트", "₩/돈 차트"])
    with t1: st.plotly_chart(update_chart_style(px.line(df_intl, y='gold'), df_intl, df_intl['gold'].min()*0.99, df_intl['gold'].max()*1.01), use_container_width=True, config={'displayModeBar': False})
    with t2:
        df_won = df_intl[['gold_don']] / 10000
        st.plotly_chart(update_chart_style(px.line(df_won, y='gold_don').update_traces(line_color='#f1c40f'), df_won, df_won['gold_don'].min()*0.99, df_won['gold_don'].max()*1.01, is_won=True), use_container_width=True, config={'displayModeBar': False})

# --- [3] 국내 금 (KRX) ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx is not None:
    k_curr, k_prev = df_krx['종가'].iloc[-1], df_krx['종가'].iloc[-2]
    disp_p = realtime_kr if realtime_kr else k_curr
    st.markdown(f'<p class="sub-time">실시간: {naver_time if naver_time else "연결지연"} / 차트: {krx_last_date}</p>', unsafe_allow_html=True)
    st.markdown(f'''
        <div class="mobile-price-row" style="border-left: 5px solid #d9534f; background-color: #fff5f5;">
            <span class="price-label">{"실시간 현재가" if realtime_kr else "마지막 종가"}</span>
            <div class="price-value" style="color:#d9534f; font-size:20px;">{int(disp_p):,}원<br>{get_delta_text(disp_p, k_prev)}</div>
        </div>
    ''', unsafe_allow_html=True)
    df_krx_won = df_krx[['종가']] / 10000
    st.plotly_chart(update_chart_style(px.area(df_krx_won, y='종가').update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)'), df_krx_won, df_krx_won['종가'].min()*0.98, df_krx_won['종가'].max()*1.02, is_won=True), use_container_width=True, config={'displayModeBar': False})

# --- [4] 국제 은 ---
if df_intl is not None:
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-time">수집: {intl_time}</p>', unsafe_allow_html=True)
    st.markdown(f'''
        <div class="mobile-price-row">
            <span class="price-label">국제 (1oz)</span>
            <div class="price-value">${curr["silver"]:,.2f}<br>{get_delta_text(curr["silver"], prev["silver"], "$")}</div>
        </div>
        <div class="mobile-price-row">
            <span class="price-label">국내환산 (1돈)</span>
            <div class="price-value">{int(curr["silver_don"]):,}원<br>{get_delta_text(curr["silver_don"], prev["silver_don"])}</div>
        </div>
    ''', unsafe_allow_html=True)
    
    s1, s2 = st.tabs(["$/oz 차트", "₩/돈 차트"])
    with s1: st.plotly_chart(update_chart_style(px.line(df_intl, y='silver').update_traces(line_color='#adb5bd'), df_intl, df_intl['silver'].min()*0.95, df_intl['silver'].max()*1.05), use_container_width=True, config={'displayModeBar': False})
    with s2:
        df_sv_won = df_intl[['silver_don']] / 10000
        st.plotly_chart(update_chart_style(px.line(df_sv_won, y='silver_don').update_traces(line_color='#adb5bd'), df_sv_won, df_sv_won['silver_don'].min()*0.95, df_sv_won['silver_don'].max()*1.05, is_won=True, is_silver=True), use_container_width=True, config={'displayModeBar': False})
