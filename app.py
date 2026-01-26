import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import re

# 1. 페이지 설정
st.set_page_config(page_title="국내 KRX 금 시세", layout="centered")

# CSS (디자인 유지)
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

# 2. 한국금거래소 실시간 시세 파싱
def get_realtime_kr_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
    try:
        # 한국금거래소 메인 페이지
        url = "https://www.koreagoldx.co.kr/"
        res = requests.get(url, headers=headers, timeout=7)
        soup = BeautifulSoup(res.text, 'html.parser')

        # KRX금 혹은 순금 시세 추출 (사이트 구조에 따라 다름)
        # 텍스트 내에서 숫자만 추출하는 정규식 사용
        gold_text = soup.find("dt", text=re.compile("KRX금")).find_next_sibling("dd").text
        gold_price = float(re.sub(r'[^0-9.]', '', gold_text))
        
        # 환율 (야후에서 가져오는 게 가장 안정적이므로 환율은 야후 병행)
        return {'krx_gold_1g': gold_price}
    except:
        return None

# 3. 데이터 로드 통합 함수
@st.cache_data(ttl=600)
def load_all_data():
    source = "한국금거래소 (KRX 실시간)"
    
    # 기본 야후 데이터 로드 (차트 및 백업용)
    try:
        g = yf.Ticker("GC=F").history(period="1mo")
        e = yf.Ticker("KRW=X").history(period="1mo")
        s = yf.Ticker("SI=F").history(period="1mo")
        chart_df = pd.DataFrame({'gold': g['Close'], 'silver': s['Close'], 'ex': e['Close']}).ffill()
        chart_df['gold_don'] = (chart_df['gold'] * chart_df['ex']) / 31.1035 * 3.75
        chart_df['silver_don'] = (chart_df['silver'] * chart_df['ex']) / 31.1035 * 3.75
    except:
        return None, None, None

    # 실시간 국내 시세 파싱 시도
    realtime = get_realtime_kr_data()
    
    if realtime:
        # 파싱 성공 시
        kr_data = {
            'gold_don': realtime['krx_gold_1g'] * 3.75,
            'ex': chart_df.iloc[-1]['ex'],
            'silver_don': chart_df.iloc[-1]['silver_don']
        }
    else:
        # 파싱 실패 시 야후 데이터 사용
        source = "Yahoo Finance (글로벌 환산)"
        last = chart_df.iloc[-1]
        kr_data = {
            'gold_don': last['gold_don'],
            'ex': last['ex'],
            'silver_don': last['silver_don']
        }
        
    return kr_data, chart_df, source

# 실행
curr, df, data_source = load_all_data()

st.markdown('<p class="gs-title">💰 국내 KRX 금/은 시세 리포트</p>', unsafe_allow_html=True)
st.markdown('<p class="geneva-title">by 제네바시계</p>', unsafe_allow_html=True)

if curr and df is not None:
    prev = df.iloc[-2]

    # --- 금 섹션 ---
    st.markdown('<p class="main-title">🟡 국내 KRX 금 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item gold-box">
                <div class="label-text">KRX 금 1돈</div>
                <div class="value-text">{int(curr['gold_don']):,}원</div>
                {get_delta_html(curr['gold_don'], prev['gold_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">현재 달러 환율</div>
                <div class="value-text">{curr['ex']:.2f}원</div>
                {get_delta_html(curr['ex'], prev['ex'], True)}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    fig_g = px.line(df, y='gold_don')
    fig_g.update_traces(line_color='#f1c40f')
    fig_g.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False})

    # --- 은 섹션 ---
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (1돈)</p>', unsafe_allow_html=True)
    # 은은 데이터 소스가 야후이므로 그대로 유지
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item silver-box">
                <div class="label-text">은 1돈 (환산)</div>
                <div class="value-text">{int(curr['silver_don']):,}원</div>
                {get_delta_html(curr['silver_don'], prev['silver_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 은 ($/oz)</div>
                <div class="value-text">${df.iloc[-1]['silver']:.2f}</div>
                {get_delta_html(df.iloc[-1]['silver'], prev['silver'], True)}
            </div>
        </div>
    """, unsafe_allow_html=True)

    fig_s = px.line(df, y='silver_don')
    fig_s.update_traces(line_color='#adb5bd')
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

    st.markdown(f'<p class="source-label">Data Source: {data_source}</p>', unsafe_allow_html=True)
else:
    st.error("데이터 로드 중입니다...")
