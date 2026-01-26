import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")

# CSS 수정: 차트 컨테이너 좌우 여백(margin) 추가
st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 20px; color: #1e1e1e; border-bottom: 2px solid #333; padding-bottom: 10px; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .fx-container { background-color: #f1f3f9; padding: 12px 18px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #dbe2ef; display: flex; justify-content: space-between; align-items: center; }
    .price-container { display: flex; gap: 10px; margin-bottom: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-sub { font-size: 11px; color: #666; margin-bottom: 5px; display: block; }
    .up { color: #d9534f; font-weight: 600; font-size: 12px; } .down { color: #0275d8; font-weight: 600; font-size: 12px; }
    
    /* 차트 좌우 여백 확보를 위한 스타일 */
    .stPlotlyChart {
        padding-left: 15px;
        padding-right: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# 공통 차트 설정 함수 (확대 금지 및 모바일 최적화)
def update_chart_layout(fig, y_min, y_max):
    fig.update_layout(
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(range=[y_min, y_max], autorange=False, fixedrange=True), # Y축 확대/스크롤 금지
        xaxis=dict(fixedrange=True), # X축 확대/스크롤 금지
        dragmode=False, # 드래그 기능 끔
        hovermode="x unified",
        template="plotly_white"
    )
    return fig

# 2. 등락 표시 유틸리티
def get_delta_html(curr, prev, prefix="", is_percent=True):
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    res = f'<span class="{color}">{sign} {prefix}{abs(diff):,.2f}'
    if is_percent: res += f' ({pct:+.2f}%)'
    res += '</span>'
    return res

# 3. 데이터 로드: 국제/환율
@st.cache_data(ttl=3600)
def get_intl_data():
    try:
        df = yf.download(["GC=F", "SI=F", "KRW=X"], period="3mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill().dropna()
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        return df
    except: return None

# 4. 데이터 로드: 국내 KRX
@st.cache_data(ttl=3600)
def get_krx_data():
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    raw_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    try:
        res = requests.get(url, params={'serviceKey': unquote(raw_key), 'numOfRows': '400', 'resultType': 'xml'}, timeout=15)
        root = ET.fromstring(res.content)
        data_list = []
        for item in root.findall('.//item'):
            name = item.findtext('itmsNm', '')
            if "금" in name and "99.99" in name and "미니" not in name:
                d_val = item.findtext('basDt')
                p_val = item.findtext('clpr')
                if d_val and p_val:
                    data_list.append({
                        '날짜': pd.to_datetime(d_val),
                        '종가': float(p_val) * 3.75,
                        '등락률': float(item.findtext('flctRt', 0))
                    })
        if not data_list: return None
        return pd.DataFrame(data_list).drop_duplicates('날짜').sort_values('날짜')
    except: return None

df_intl = get_intl_data()
df_krx = get_krx_data()

st.markdown('<p class="gs-title">📊 금/은 마켓 대시보드</p>', unsafe_allow_html=True)

# --- 섹션 1: 환율 및 국제 금 ---
if df_intl is not None and len(df_intl) >= 2:
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    
    st.markdown(f"""
        <div class="fx-container">
            <span style="font-size:14px; color:#555; font-weight:600;">현재 원/달러 환율</span>
            <div style="text-align:right;">
                <span style="font-size:18px; font-weight:800;">{curr['ex']:,.2f}원</span>
                {get_delta_html(curr['ex'], prev['ex'])}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box">
                <span class="val-sub">국내 환산가 (1돈)</span>
                <span class="val-main">{int(curr['gold_don']):,}원</span>
                {get_delta_html(curr['gold_don'], prev['gold_don'])}
            </div>
            <div class="price-box">
                <span class="val-sub">국제 시세 (1oz)</span>
                <span class="val-main">${curr['gold']:,.2f}</span>
                {get_delta_html(curr['gold'], prev['gold'], prefix="$")}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    y_min, y_max = df_intl['gold_don'].min() * 0.995, df_intl['gold_don'].max() * 1.005
    fig_g = px.line(df_intl, y='gold_don')
    fig_g = update_chart_layout(fig_g, y_min, y_max)
    fig_g.update_traces(line_color='#f1c40f', line_width=3)
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False})

# --- 섹션 2: 국내 금 시세 (KRX) ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx is not None and not df_krx.empty:
    latest_k = df_krx.iloc[-1]
    st.markdown(f"""
        <div class="price-box" style="margin-bottom:15px;">
            <span class="val-sub">오늘의 KRX 종가 (1돈 환산)</span>
            <span class="val-main">{int(latest_k['종가']):,}원</span>
            <span class="{'up' if latest_k['등락률'] > 0 else 'down'}">
                {'▲' if latest_k['등락률'] > 0 else '▼'} {abs(latest_k['등락률'])}%
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    yk_min, yk_max = df_krx['종가'].min() * 0.995, df_krx['종가'].max() * 1.005
    fig_k = px.area(df_krx, x='날짜', y='종가')
    fig_k = update_chart_layout(fig_k, yk_min, yk_max)
    fig_k.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)')
    st.plotly_chart(fig_k, use_container_width=True, config={'displayModeBar': False})

# --- 섹션 3: 국제 은 시세 ---
st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
if df_intl is not None and len(df_intl) >= 2:
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box">
                <span class="val-sub">국내 환산가 (1돈)</span>
                <span class="val-main">{int(curr['silver_don']):,}원</span>
                {get_delta_html(curr['silver_don'], prev['silver_don'])}
            </div>
            <div class="price-box">
                <span class="val-sub">국제 시세 (1oz)</span>
                <span class="val-main">${curr['silver']:,.2f}</span>
                {get_delta_html(curr['silver'], prev['silver'], prefix="$")}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    ys_min, ys_max = df_intl['silver_don'].min() * 0.96, df_intl['silver_don'].max() * 1.04
    fig_s = px.line(df_intl, y='silver_don')
    fig_s = update_chart_layout(fig_s, ys_min, ys_max)
    fig_s.update_traces(line_color='#adb5bd', line_width=3)
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})
