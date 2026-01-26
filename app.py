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
    </style>
    """, unsafe_allow_html=True)

# 2. 네이버 파싱 함수 보강 (에러 방지용)
def get_naver_val(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 상승/하락/보합 상관없이 'no_today' 안의 숫자 값을 가져옴
        val = soup.select_one(".no_today .value").text.replace(',', '')
        return float(val)
    except:
        return None

def get_naver_data():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # 환율 (메인 페이지에서 바로 추출)
        ex_res = requests.get("https://finance.naver.com/marketindex/", headers=headers, timeout=10)
        ex_soup = BeautifulSoup(ex_res.text, 'html.parser')
        ex_rate = float(ex_soup.select_one(".usd .value").text.replace(',', ''))
        
        # 금/은 개별 상세 페이지에서 추출
        gold = get_naver_val("https://finance.naver.com/marketindex/worldGoldDetail.naver?marketindexCd=CMDT_GC")
        silver = get_naver_val("https://finance.naver.com/marketindex/worldSilverDetail.naver?marketindexCd=CMDT_SI")
        
        if ex_rate and gold and silver:
            return {'ex': ex_rate, 'gold': gold, 'silver': silver}
    except:
        pass
    return None

@st.cache_data(ttl=1800)
def get_chart_data():
    try:
        # 야후 파이낸스 차트 데이터
        g = yf.Ticker("GC=F").history(period="1mo")
        s = yf.Ticker("SI=F").history(period="1mo")
        e = yf.Ticker("KRW=X").history(period="1mo")
        df = pd.DataFrame({'gold': g['Close'], 'silver': s['Close'], 'ex': e['Close']}).ffill()
        df['gold_don'] = (df['gold'] * df['ex']) / 31.1035 * 3.75
        df['silver_don'] = (df['silver'] * df['ex']) / 31.1035 * 3.75
        return df
    except:
        return None

def get_delta_html(curr, prev, is_currency=False):
    diff = curr - prev
    if diff > 0:
        v = f"{diff:.2f}" if is_currency else f"{int(diff):,}"
        return f'<span class="delta-text up">▲ {v}</span>'
    elif diff < 0:
        v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
        return f'<span class="delta-text down">▼ {v}</span>'
    return '<span class="delta-text equal">- 0</span>'

# 실행
naver = get_naver_data()
chart = get_chart_data()

st.markdown('<p class="gs-title">💰 국제 금/은 시세 리포트</p>', unsafe_allow_html=True)
st.markdown('<p class="geneva-title">by 제네바시계</p>', unsafe_allow_html=True)

if naver and chart is not None:
    prev = chart.iloc[-2]
    curr_g_don = (naver['gold'] * naver['ex']) / 31.1035 * 3.75
    curr_s_don = (naver['silver'] * naver['ex']) / 31.1035 * 3.75

    # --- 금 섹션 ---
    st.markdown('<p class="main-title">🟡 국제 금 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="custom-container"><div class="custom-item gold-box"><div class="label-text">금 1돈 (3.75g)</div><div class="value-text">{int(curr_g_don):,}원</div>{get_delta_html(curr_g_don, prev["gold_don"])}</div><div class="custom-item"><div class="label-text">현재 달러 환율</div><div class="value-text">{naver["ex"]:.2f}원</div>{get_delta_html(naver["ex"], prev["ex"], True)}</div></div>', unsafe_allow_html=True)
    
    fig_g = px.line(chart, y='gold_don')
    fig_g.update_traces(line_color='#f1c40f')
    fig_g.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    # --- 은 섹션 ---
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="custom-container"><div class="custom-item silver-box"><div class="label-text">은 1돈 (3.75g)</div><div class="value-text">{int(curr_s_don):,}원</div>{get_delta_html(curr_s_don, prev["silver_don"])}</div><div class="custom-item"><div class="label-text">국제 은 ($/oz)</div><div class="value-text">${naver["silver"]:.2f}</div>{get_delta_html(naver["silver"], prev["silver"], True)}</div></div>', unsafe_allow_html=True)

    fig_s = px.line(chart, y='silver_don')
    fig_s.update_traces(line_color='#adb5bd')
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})
else:
    st.warning("데이터를 불러오는 중입니다. 잠시만 기다려주시거나 새로고침 해주세요.")

st.caption("데이터 출처: 네이버 증권 / 실시간 국제 시세")
