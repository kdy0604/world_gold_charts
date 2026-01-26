import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정 및 CSS (디자인 유지)
st.set_page_config(page_title="국내 KRX 금 시세", layout="centered")

st.markdown("""
    <style>
    .block-container { max-width: 90% !important; padding-left: 5% !important; padding-right: 5% !important; }
    .gs-title { font-size: clamp(20px, 7vw, 30px) !important; font-weight: 700; margin-top: 20px; margin-bottom: 5px; line-height: 1.2 !important; display: block !important; }
    .geneva-title { font-size: 15px; font-weight: 700; margin-top: 5px; margin-bottom: 20px; text-align: right !important; padding-right: 20px !important; }
    .main-title { font-size: 20px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; }
    .custom-container { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 15px; }
    .custom-item { flex: 1; background-color: #f8f9fa; padding: 10px 3px; border-radius: 10px; text-align: center; border-left: 4px solid #dee2e6; min-width: 0; }
    .gold-box { background-color: #fdf2d0; border-left-color: #f1c40f; }
    .silver-box { background-color: #e9ecef; border-left-color: #adb5bd; }
    .label-text { font-size: 11px; color: #666; margin-bottom: 3px; white-space: nowrap; }
    .value-text { font-size: 15px; font-weight: 800; color: #1E1E1E; white-space: nowrap; }
    .delta-text { font-size: 11px; font-weight: 600; margin-top: 2px; display: block; }
    .up { color: #d9534f; } .down { color: #0275d8; } .equal { color: #666; }
    .stPlotlyChart { touch-action: pan-y !important; }
    .source-label { font-size: 12px; color: #888; text-align: right; margin-top: 10px; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

# 2. 금시세닷컴 기반 KRX 금 및 환율 파싱
def get_krx_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}
    try:
        # 금시세닷컴 접속 (국내 금 및 환율 정보 포함)
        url = "https://sise.gold-sise.com/"
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')

        # KRX 금 1g 가격 파싱 (사이트 구조에 맞게 설정)
        # 보통 첫 번째 나오는 '순금' 혹은 'KRX금' 항목을 찾습니다.
        krx_1g = soup.select_one(".price_box .price").text.replace(',', '').replace('원', '')
        
        # 환율 정보 파싱
        ex_rate = soup.select_one(".exchange_box .price").text.replace(',', '').replace('원', '')
        
        return {
            'krx_gold_1g': float(krx_1g),
            'ex': float(ex_rate)
        }
    except:
        return None

# 3. 차트 및 데이터 로드 로직
@st.cache_data(ttl=600)
def load_data():
    source = "KRX 실시간 시세 (금시세닷컴)"
    # 차트 데이터는 추세 확인용으로 야후 유지
    try:
        g = yf.Ticker("GC=F").history(period="1mo")
        s = yf.Ticker("SI=F").history(period="1mo")
        e = yf.Ticker("KRW=X").history(period="1mo")
        chart_df = pd.DataFrame({'gold': g['Close'], 'silver': s['Close'], 'ex': e['Close']}).ffill()
        chart_df['gold_don'] = (chart_df['gold'] * chart_df['ex']) / 31.1035 * 3.75
        chart_df['silver_don'] = (chart_df['silver'] * chart_df['ex']) / 31.1035 * 3.75
    except:
        return None, None, None

    # 실시간 데이터 가져오기 시도
    realtime = get_krx_data()
    
    if not realtime:
        # 파싱 실패 시 야후 데이터로 대체
        last = chart_df.iloc[-1]
        # 야후 국제금 -> 1g 환산 (국제가는 oz당 달러이므로 환산 필요)
        gold_1g = (last['gold'] * last['ex']) / 31.1035
        realtime = {'krx_gold_1g': gold_1g, 'ex': last['ex']}
        source = "Yahoo Finance (네트워크 백업)"
    
    return realtime, chart_df, source

def get_delta_html(curr, prev, is_currency=False):
    diff = curr - prev
    if abs(diff) < 0.1: return '<span class="delta-text equal">- 0</span>'
    if diff > 0:
        v = f"{diff:.2f}" if is_currency else f"{int(diff):,}"
        return f'<span class="delta-text up">▲ {v}</span>'
    v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
    return f'<span class="delta-text down">▼ {v}</span>'

# 실행
curr_data, chart_df, current_source = load_data()

st.markdown('<p class="gs-title">💰 국내 KRX 금/은 시세 리포트</p>', unsafe_allow_html=True)
st.markdown('<p class="geneva-title">by 제네바시계</p>', unsafe_allow_html=True)

if curr_data and chart_df is not None:
    prev = chart_df.iloc[-2]
    
    # KRX 금 1돈 가격 계산
    c_gold_don = curr_data['krx_gold_1g'] * 3.75
    # 은은 KRX 시장 데이터가 제한적이므로 야후 환산값 유지
    c_silver_don = (chart_df.iloc[-1]['silver'] * curr_data['ex']) / 31.1035 * 3.75

    # --- 금(Gold) 섹션 ---
    st.markdown('<p class="main-title">🟡 국내 KRX 금 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item gold-box">
                <div class="label-text">KRX 금 1돈 (3.75g)</div>
                <div class="value-text">{int(c_gold_don):,}원</div>
                {get_delta_html(c_gold_don, prev['gold_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">현재 달러 환율</div>
                <div class="value-text">{curr_data['ex']:.2f}원</div>
                {get_delta_html(curr_data['ex'], prev['ex'], True)}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    fig_g = px.line(chart_df, y='gold_don')
    fig_g.update_traces(line_color='#f1c40f')
    fig_g.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    # --- 은(Silver) 섹션 ---
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item silver-box">
                <div class="label-text">은 1돈 (3.75g)</div>
                <div class="value-text">{int(c_silver_don):,}원</div>
                {get_delta_html(c_silver_don, prev['silver_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 은 시산 ($)</div>
                <div class="value-text">${chart_df.iloc[-1]['silver']:.2f}</div>
                {get_delta_html(chart_df.iloc[-1]['silver'], prev['silver'], True)}
            </div>
        </div>
        """, unsafe_allow_html=True)

    fig_s = px.line(chart_df, y='silver_don')
    fig_s.update_traces(line_color='#adb5bd')
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

    st.markdown(f'<p class="source-label">Data Source: {current_source}</p>', unsafe_allow_html=True)
else:
    st.error("데이터 연결에 실패했습니다.")
