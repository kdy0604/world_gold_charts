import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 1. 페이지 설정 및 모바일 강제 여백 CSS
st.set_page_config(page_title="금/은 국제 시세", layout="centered")

st.markdown("""
    <style>
    /* 전체 앱의 너비를 90%로 제한하여 양옆에 5%씩 스크롤 전용 여백 확보 */
    .block-container {
        max-width: 90% !important;
        padding-left: 5% !important;
        padding-right: 5% !important;
    }
    
    /* 제목 및 텍스트 스타일 */
    .gs-title { font-size: clamp(20px, 7vw, 30px) !important; 
        font-weight: 700; margin-top: 20px; margin-bottom: 5px; 
        white-space: nowrap !important;     /* 줄바꿈 금지 */
        overflow: hidden !important;        /* 넘치는 부분 숨김 */
        text-overflow: ellipsis !important; /* 혹시 넘치면 ... 표시 (안전장치) */
        line-height: 1.2 !important;
        display: block !important;
        }
    .geneva-title { font-size: 15px; font-weight: 700; margin-top: 20px; margin-bottom: 20px; padding-left: 30px;
        text-align: right !important;      /* 텍스트를 오른쪽으로 */
        padding-right: 20px !important;    /* 오른쪽 벽에서 살짝 띄움 */
        }
    .main-title { font-size: 20px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; }
    .custom-container { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 15px; }
    .custom-item { flex: 1; background-color: #f8f9fa; padding: 10px 3px; border-radius: 10px; text-align: center; border-left: 4px solid #dee2e6; min-width: 0; }
    
    /* 금/은 박스 색상 구분 */
    .gold-box { background-color: #fdf2d0; border-left-color: #f1c40f; }
    .silver-box { background-color: #e9ecef; border-left-color: #adb5bd; }
    
    .label-text { font-size: 11px; color: #666; margin-bottom: 3px; white-space: nowrap; }
    .value-text { font-size: 15px; font-weight: 800; color: #1E1E1E; white-space: nowrap; }
    .delta-text { font-size: 11px; font-weight: 600; margin-top: 2px; display: block; }
    
    /* 등락 색상 */
    .up { color: #d9534f; }   /* 상승: 빨강 */
    .down { color: #0275d8; } /* 하락: 파랑 */
    .equal { color: #666; }    /* 동일: 회색 */
    
    /* 차트 영역 터치 스크롤 간섭 방지 */
    .stPlotlyChart { touch-action: pan-y !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 네이버 금융 데이터 파싱 함수
def get_naver_data():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # 환율 파싱
        ex_url = "https://finance.naver.com/marketindex/"
        ex_res = requests.get(ex_url, headers=headers)
        ex_soup = BeautifulSoup(ex_res.text, 'html.parser')
        exchange_rate = float(ex_soup.select_one(".usd .value").text.replace(',', ''))
        
        # 국제 금 파싱
        gold_url = "https://finance.naver.com/marketindex/worldGoldDetail.naver?marketindexCd=CMDT_GC"
        gold_res = requests.get(gold_url, headers=headers)
        gold_soup = BeautifulSoup(gold_res.text, 'html.parser')
        intl_gold = float(gold_soup.select_one(".no_today .no_up .value").text.replace(',', ''))
        
        # 국제 은 파싱
        silver_url = "https://finance.naver.com/marketindex/worldSilverDetail.naver?marketindexCd=CMDT_SI"
        silver_res = requests.get(silver_url, headers=headers)
        silver_soup = BeautifulSoup(silver_res.text, 'html.parser')
        intl_silver = float(silver_soup.select_one(".no_today .no_up .value").text.replace(',', ''))
        
        return {
            'ex': exchange_rate,
            'gold': intl_gold,
            'silver': intl_silver
        }
    except:
        return None

# 3. 차트용 데이터 (yfinance 유지 - 1개월 추이용)
@st.cache_data(ttl=3600)
def get_chart_data():
    try:
        gold_t = yf.Ticker("GC=F")
        silver_t = yf.Ticker("SI=F")
        ex_t = yf.Ticker("KRW=X")
        
        g_h = gold_t.history(period="1mo")
        s_h = silver_t.history(period="1mo")
        e_h = ex_t.history(period="1mo")
        
        df = pd.DataFrame({
            'gold': g_h['Close'],
            'silver': s_h['Close'],
            'ex': e_h['Close']
        }).ffill()
        
        df['gold_don'] = (df['gold'] * df['ex']) / 31.1035 * 3.75
        df['silver_don'] = (df['silver'] * df['ex']) / 31.1035 * 3.75
        return df
    except:
        return None

# 등락 표시 함수
def get_delta_html(curr_val, prev_val, is_currency=False):
    diff = curr_val - prev_val
    if diff > 0:
        v = f"{diff:.2f}" if is_currency else f"{int(diff):,}"
        return f'<span class="delta-text up">▲ {v}</span>'
    elif diff < 0:
        v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
        return f'<span class="delta-text down">▼ {v}</span>'
    else:
        return '<span class="delta-text equal">- 0</span>'

# 실행
naver_curr = get_naver_data()
chart_df = get_chart_data()

st.markdown('<p class="gs-title">💰 국제 금/은 시세 리포트</p>', unsafe_allow_html=True)
st.markdown('<p class="geneva-title">by 제네바시계</p>', unsafe_allow_html=True)

if naver_curr and chart_df is not None:
    # 현재가는 네이버 실시간 파싱 정보 사용
    # 전날 대비 등락 계산을 위해 chart_df의 마지막에서 두번째 행 사용
    prev = chart_df.iloc[-2]
    
    curr_gold_don = (naver_curr['gold'] * naver_curr['ex']) / 31.1035 * 3.75
    curr_silver_don = (naver_curr['silver'] * naver_curr['ex']) / 31.1035 * 3.75

    # --- 금(Gold) 섹션 ---
    st.markdown('<p class="main-title">🟡 국제 금 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item gold-box">
                <div class="label-text">금 1돈 (3.75g)</div>
                <div class="value-text">{int(curr_gold_don):,}원</div>
                {get_delta_html(curr_gold_don, prev['gold_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">현재 달러 환율</div>
                <div class="value-text">{naver_curr['ex']:.2f}원</div>
                {get_delta_html(naver_curr['ex'], prev['ex'], True)}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    fig_g = px.line(chart_df, y='gold_don')
    fig_g.update_traces(line_color='#f1c40f')
    fig_g.update_layout(
        xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0),
        yaxis=dict(range=[chart_df['gold_don'].min()*0.995, chart_df['gold_don'].max()*1.005], tickformat=",.0f"),
        hovermode="x", dragmode=False
    )
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

    st.caption("공식: (국제시세 * 환율) / 31.1035 * 3.75")
    st.divider()

    # --- 은(Silver) 섹션 ---
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item silver-box">
                <div class="label-text">은 1돈 (3.75g)</div>
                <div class="value-text">{int(curr_silver_don):,}원</div>
                {get_delta_html(curr_silver_don, prev['silver_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 은 ($/oz)</div>
                <div class="value-text">${naver_curr['silver']:.2f}</div>
                {get_delta_html(naver_curr['silver'], prev['silver'], True)}
            </div>
        </div>
        """, unsafe_allow_html=True)

    fig_s = px.line(chart_df, y='silver_don')
    fig_s.update_traces(line_color='#adb5bd')
    fig_s.update_layout(
        xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0),
        yaxis=dict(range=[chart_df['silver_don'].min()*0.98, chart_df['silver_don'].max()*1.02], tickformat=",.0f"),
        hovermode="x", dragmode=False
    )
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

else:
    st.error("데이터 로드 실패. 서버 연결 상태를 확인해주세요.")

st.caption("공식: (국제시세 * 환율) / 31.1035 * 3.75")
