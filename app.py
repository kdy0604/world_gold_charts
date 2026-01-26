import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="금/은 종합 시세 리포트", layout="centered")

st.markdown("""
    <style>
    .block-container { max-width: 90% !important; padding-left: 5% !important; padding-right: 5% !important; }
    .gs-title { font-size: clamp(20px, 7vw, 30px) !important; font-weight: 700; margin-top: 20px; margin-bottom: 5px; line-height: 1.2 !important; display: block !important; }
    .geneva-title { font-size: 14px; font-weight: 700; margin-top: 5px; margin-bottom: 20px; text-align: right !important; padding-right: 15px !important; color: #888; }
    .main-title { font-size: 19px; font-weight: 700; margin-top: 25px; margin-bottom: 12px; }
    .custom-container { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 15px; }
    .custom-item { flex: 1; background-color: #f8f9fa; padding: 12px 5px; border-radius: 12px; text-align: center; border-left: 4px solid #dee2e6; min-width: 0; }
    .gold-box { background-color: #fff9e6; border-left-color: #f1c40f; }
    .silver-box { background-color: #f1f3f5; border-left-color: #adb5bd; }
    .krx-box { background-color: #eef2ff; border-left-color: #4361ee; }
    .label-text { font-size: 11px; color: #666; margin-bottom: 4px; white-space: nowrap; }
    .value-text { font-size: 16px; font-weight: 800; color: #1E1E1E; white-space: nowrap; }
    .delta-text { font-size: 11px; font-weight: 600; margin-top: 3px; display: block; }
    .ex-info { text-align: right; padding: 10px; background: #f8f9fa; border-radius: 8px; margin-top: -10px; margin-bottom: 20px; border: 1px solid #eee; }
    .up { color: #d9534f; } .down { color: #0275d8; } .equal { color: #666; }
    </style>
    """, unsafe_allow_html=True)

# 2. 등락 계산 함수
def get_delta_html(curr, prev, is_currency=False):
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    if abs(diff) < 0.001: return '<span class="delta-text equal">- 0 (0.00%)</span>'
    sign = "▲" if diff > 0 else "▼"
    color = "up" if diff > 0 else "down"
    v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
    return f'<span class="delta-text {color}">{sign} {v} ({pct:+.2f}%)</span>'

# 3. KRX 금 시세 데이터 (최근 10일치 차트용)
@st.cache_data(ttl=3600)
def get_krx_history():
    service_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    params = {'serviceKey': service_key, 'numOfRows': '15', 'pageNo': '1', 'resultType': 'xml'}
    
    try:
        res = requests.get(url, params=params, timeout=10)
        root = ET.fromstring(res.text)
        items = root.findall('.//item')
        
        hist_data = []
        for item in items:
            date_str = item.find('basDt').text
            price = float(item.find('clpr').text) * 3.75 # 1돈 환산
            hist_data.append({'날짜': pd.to_datetime(date_str), '국내금': price})
        
        df_krx = pd.DataFrame(hist_data).sort_values('날짜')
        return df_krx
    except: return None

# 4. 국제 데이터 로드 (Yahoo Finance)
@st.cache_data(ttl=600)
def load_intl_data():
    try:
        tickers = ["GC=F", "SI=F", "KRW=X"]
        data = yf.download(tickers, period="1mo", interval="1d")['Close']
        df = data.ffill().rename(columns={"GC=F": "gold_intl", "SI=F": "silver_intl", "KRW=X": "ex"})
        df['gold_don_intl'] = (df['gold_intl'] / 31.1035) * df['ex'] * 3.75
        df['silver_don_intl'] = (df['silver_intl'] / 31.1035) * df['ex'] * 3.75
        return df
    except: return None

# 데이터 준비
df_intl = load_intl_data()
df_krx = get_krx_history()

st.markdown('<p class="gs-title">💰 금/은 종합 시세 리포트</p>', unsafe_allow_html=True)
st.markdown('<p class="geneva-title">by 제네바시계</p>', unsafe_allow_html=True)

if df_intl is not None:
    c = df_intl.iloc[-1]
    p = df_intl.iloc[-2]

    # --- 1. 국제 금 섹션 ---
    st.markdown('<p class="main-title">🟡 국제 금 시세 (International)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item gold-box">
                <div class="label-text">국제금 1돈 (환산)</div>
                <div class="value-text">{int(c['gold_don_intl']):,}원</div>
                {get_delta_html(c['gold_don_intl'], p['gold_don_intl'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 금 (USD/oz)</div>
                <div class="value-text">${c['gold_intl']:.1f}</div>
                {get_delta_html(c['gold_intl'], p['gold_intl'], True)}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    fig_g_intl = px.line(df_intl, y='gold_don_intl')
    fig_g_intl.update_traces(line_color='#f1c40f', line_width=3)
    fig_g_intl.update_layout(xaxis_title=None, yaxis_title=None, height=180, margin=dict(l=0,r=0,t=10,b=0), hovermode="x")
    st.plotly_chart(fig_g_intl, use_container_width=True, config={'displayModeBar': False})

    # 환율 정보
    st.markdown(f"""
        <div class="ex-info">
            <span style="font-size: 12px; color: #666;">기준 환율: <b>{c['ex']:.2f}원</b></span>
            <span style="font-size: 11px;"> {get_delta_html(c['ex'], p['ex'], True)}</span>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- 2. 국내 금 섹션 (KRX 공식 추가) ---
    st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식 종가)</p>', unsafe_allow_html=True)
    if df_krx is not None:
        curr_krx = df_krx.iloc[-1]['국내금']
        prev_krx = df_krx.iloc[-2]['국내금']
        st.markdown(f"""
            <div class="custom-container">
                <div class="custom-item krx-box">
                    <div class="label-text">KRX 금 1돈 (공식 종가)</div>
                    <div class="value-text">{int(curr_krx):,}원</div>
                    {get_delta_html(curr_krx, prev_krx)}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        fig_krx = px.line(df_krx, x='날짜', y='국내금')
        fig_krx.update_traces(line_color='#4361ee', line_width=3)
        fig_krx.update_layout(xaxis_title=None, yaxis_title=None, height=180, margin=dict(l=0,r=0,t=10,b=0), hovermode="x")
        st.plotly_chart(fig_krx, use_container_width=True, config={'displayModeBar': False})
    else:
        st.warning("국내 API 데이터를 불러올 수 없습니다.")

    st.divider()

    # --- 3. 국제 은 섹션 ---
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item silver-box">
                <div class="label-text">은 1돈 (환산)</div>
                <div class="value-text">{int(c['silver_don_intl']):,}원</div>
                {get_delta_html(c['silver_don_intl'], p['silver_don_intl'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 은 (USD/oz)</div>
                <div class="value-text">${c['silver_intl']:.2f}</div>
                {get_delta_html(c['silver_intl'], p['silver_intl'], True)}
            </div>
        </div>
    """, unsafe_allow_html=True)

    fig_s = px.line(df_intl, y='silver_don_intl')
    fig_s.update_traces(line_color='#adb5bd', line_width=3)
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=180, margin=dict(l=0,r=0,t=10,b=0), hovermode="x")
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

    st.caption(f"KRX 종가는 공공데이터포털 기준이며, 국제 시세는 Yahoo Finance 기준입니다. (업데이트: {datetime.now().strftime('%H:%M')})")
else:
    st.error("데이터 로드 실패")
