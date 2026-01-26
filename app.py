import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정
st.set_page_config(page_title="금/은 국제 시세", layout="centered")

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

# 2. 보강된 네이버 파싱 함수
def get_naver_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://finance.naver.com/'
    }
    try:
        ex_res = requests.get("https://finance.naver.com/marketindex/", headers=headers, timeout=5)
        ex_soup = BeautifulSoup(ex_res.text, 'html.parser')
        ex_rate = float(ex_soup.select_one(".usd .value").text.replace(',', ''))
        
        g_url = "https://finance.naver.com/marketindex/worldGoldDetail.naver?marketindexCd=CMDT_GC"
        g_res = requests.get(g_url, headers=headers, timeout=5)
        g_soup = BeautifulSoup(g_res.text, 'html.parser')
        gold = float(g_soup.select_one(".no_today .value").text.replace(',', ''))
        
        s_url = "https://finance.naver.com/marketindex/worldSilverDetail.naver?marketindexCd=CMDT_SI"
        s_res = requests.get(s_url, headers=headers, timeout=5)
        s_soup = BeautifulSoup(s_res.text, 'html.parser')
        silver = float(s_soup.select_one(".no_today .value").text.replace(',', ''))
        
        return {'ex': ex_rate, 'gold': gold, 'silver': silver}
    except:
        return None

# 3. 통합 데이터 로드 (네이버 실패 시 야후로 대체)
@st.cache_data(ttl=600)
def load_all_combined_data():
    source_name = "Naver Finance (실시간)"
    try:
        g = yf.Ticker("GC=F").history(period="1mo")
        s = yf.Ticker("SI=F").history(period="1mo")
        e = yf.Ticker("KRW=X").history(period="1mo")
        chart_df = pd.DataFrame({'gold': g['Close'], 'silver': s['Close'], 'ex': e['Close']}).ffill()
        chart_df['gold_don'] = (chart_df['gold'] * chart_df['ex']) / 31.1035 * 3.75
        chart_df['silver_don'] = (chart_df['silver'] * chart_df['ex']) / 31.1035 * 3.75
    except:
        return None, None, None

    current = get_naver_data()
    if not current:
        last = chart_df.iloc[-1]
        current = {'ex': last['ex'], 'gold': last['gold'], 'silver': last['silver']}
        source_name = "Yahoo Finance (지연 데이터)"
    
    return current, chart_df, source_name

def get_delta_html(curr, prev, is_currency=False):
    diff = curr - prev
    if abs(diff) < 0.001: return '<span class="delta-text equal">- 0</span>'
    if diff > 0:
        v = f"{diff:.2f}" if is_currency else f"{int(diff):,}"
        return f'<span class="delta-text up">▲ {v}</span>'
    v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
    return f'<span class="delta-text down">▼ {v}</span>'

# 실행
curr_data, chart_df, current_source = load_all_combined_data()

st.markdown('<p class="gs-title">💰 국제 금/은 시세 리포트</p>', unsafe_allow_html=True)
st.markdown('<p class="geneva-title">by 제네바시계</p>', unsafe_allow_html=True)

if curr_data and chart_df is not None:
    prev = chart_df.iloc[-2]
    c_gold_don = (curr_data['gold'] * curr_data['ex']) / 31.1035 * 3.75
    c_silver_don = (curr_data['silver'] * curr_data['ex']) / 31.1035 * 3.75

    # 금 섹션
    st.markdown('<p class="main-title">🟡 국제 금 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="custom-container"><div class="custom-item gold-box"><div class="label-text">금 1돈 (3.75g)</div><div class="value-text">{int(c_gold_don):,}원</div>{get_delta_html(c_gold_don, prev["gold_don"])}</div><div class="custom-item"><div class="label-text">현재 달러 환율</div><div class="value-text">{curr_data["ex"]:.2f}원</div>{get_delta_html(curr_data["ex"], prev["ex"], True)}</div></div>', unsafe_allow_html=True)
    
    fig_g = px.line(chart_df, y='gold_don')
    fig_g.update_traces(line_color='#f1c40f')
    fig_g.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    # 은 섹션
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="custom-container"><div class="custom-item silver-box"><div class="label-text">은 1돈 (3.75g)</div><div class="value-text">{int(c_silver_don):,}원</div>{get_delta_html(c_silver_don, prev["silver_don"])}</div><div class="custom-item"><div class="label-text">국제 은 ($/oz)</div><div class="value-text">${curr_data["silver"]:.2f}</div>{get_delta_html(curr_data["silver"], prev["silver"], True)}</div></div>', unsafe_allow_html=True)

    fig_s = px.line(chart_df, y='silver_don')
    fig_s.update_traces(line_color='#adb5bd')
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

    # 데이터 소스 표기
    st.markdown(f'<p class="source-label">Data Source: {current_source}</p>', unsafe_allow_html=True)
else:
    st.error("금융 서버에 접속할 수 없습니다. 잠시 후 다시 시도해 주세요.")

st.caption("공식: (국제시세 * 환율) / 31.1035 * 3.75")
