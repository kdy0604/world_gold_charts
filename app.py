import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

st.markdown("""
    <style>
    .gs-title { font-size: 20px; font-weight: 800; color: #1e1e1e; }
    .price-box { background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; margin-bottom: 15px; }
    .val-main { font-size: 22px; font-weight: 800; color: #d9534f; }
    .ref-time { font-size: 11px; color: #999; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 수집: 네이버 금융 웹페이지 직접 크롤링 (API 아님)
@st.cache_data(ttl=600)
def get_gold_data_from_web():
    try:
        # 네이버 금융 국제금 일별 시세 페이지 (표 형태)
        url = "https://finance.naver.com/marketindex/worldDailyQuote.naver?fdtc=2&marketindexCd=G_GC@COMEX"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 테이블의 행(tr)들을 찾아서 데이터 추출
        rows = soup.select('table.tbl_exchange tr')
        data_list = []
        
        for row in rows:
            cols = row.select('td')
            if len(cols) >= 2:
                date = cols[0].text.strip()
                price = float(cols[1].text.strip().replace(',', ''))
                data_list.append({'날짜': pd.to_datetime(date), '종가': price})
        
        df = pd.DataFrame(data_list).set_index('날짜').sort_index()
        return df
    except Exception as e:
        return None

# 3. 환율 수집 (가장 안정적인 기본 API)
def get_simple_fx():
    try:
        url = "https://marketindex.naver.com/api/iuser/marketindex/getChartData.nhn?marketindexCd=FX_USDKRW&periodType=day"
        res = requests.get(url).json()
        return float(res['result'][-1]['closePrice'])
    except:
        return 1350.0

# --- 메인 실행 ---
df = get_gold_data_from_web()
fx = get_simple_fx()

if df is not None and not df.empty:
    # 원화 환산
    df['won_don'] = (df['종가'] / 31.1034) * fx * 3.75
    
    curr_p = df['종가'].iloc[-1]
    prev_p = df['종가'].iloc[-2]
    curr_won = df['won_don'].iloc[-1]
    
    st.markdown('<p class="gs-title">🟡 국제 금 (네이버 공식 정산가 기준)</p>', unsafe_allow_html=True)
    
    # 상단 요약 박스
    diff = curr_p - prev_p
    sign = "▲" if diff >= 0 else "▼"
    color = "#d9534f" if diff >= 0 else "#0275d8"
    
    st.markdown(f"""
    <div class="price-box">
        <div style="font-size:13px; color:#666;">뉴욕 정산가: ${curr_p:,.2f} (<span style="color:{color};">{sign}{abs(diff):,.2f}</span>)</div>
        <div style="font-size:14px; margin-top:8px; font-weight:bold;">국내 환산가 (1돈)</div>
        <div class="val-main">{int(curr_won):,}원</div>
        <div class="ref-time">기준 환율: {fx:,.2f}원</div>
    </div>
    """, unsafe_allow_html=True)

    # 4. 차트 (터치 시 원 단위 표시 기능 포함)
    fig = px.line(df, y='won_don', markers=True)
    
    fig.update_traces(
        line_color='#f1c40f',
        customdata=df[['won_don']],
        hovertemplate="날짜: %{x}<br>가격: %{customdata[0]:,.0f}원<extra></extra>"
    )
    
    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=20, b=0),
        template="plotly_white",
        hovermode="x unified",
        yaxis=dict(fixedrange=True, title=None),
        xaxis=dict(fixedrange=True, title=None, tickformat='%m-%d')
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.caption("※ 네이버 금융의 공식 일별 정산 데이터를 기반으로 합니다.")
else:
    st.error("데이터 수집 주소를 변경 중입니다. 잠시 후 새로고침 해주세요.")
