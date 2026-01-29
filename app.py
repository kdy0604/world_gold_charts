import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# 1. 페이지 설정 및 스타일
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

st.markdown("""
    <style>
    .gs-title { font-size: 20px; font-weight: 800; color: #1e1e1e; }
    .price-box { background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 22px; font-weight: 800; color: #d9534f; }
    .delta { font-size: 12px; font-weight: 600; }
    .up { color: #d9534f; } .down { color: #0275d8; }
    </style>
    """, unsafe_allow_html=True)

# 2. 네이버 공식 정산가 수집 (스크래핑 방식 - 더 안정적)
@st.cache_data(ttl=600)
def get_naver_gold_official():
    try:
        data_list = []
        # 최근 2페이지를 긁어 약 20거래일(한 달치) 확보
        for page in range(1, 3):
            url = f"https://finance.naver.com/marketindex/worldDailyQuote.naver?fdtc=2&marketindexCd=G_GC@COMEX&page={page}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('table.tbl_exchange tr')
            
            for row in rows:
                cols = row.select('td')
                if len(cols) >= 2:
                    date = pd.to_datetime(cols[0].text.strip())
                    price = float(cols[1].text.strip().replace(',', ''))
                    data_list.append({'날짜': date, '종가': price})
        
        df = pd.DataFrame(data_list).drop_duplicates('날짜').set_index('날짜').sort_index()
        return df
    except:
        return None

# 3. 실시간 환율 수집
def get_fx_rate():
    try:
        url = "https://marketindex.naver.com/index.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        return float(soup.select_one("span.value").text.replace(',', ''))
    except:
        return 1350.0 # 실패 시 기본값

# --- 메인 실행 ---
df_gold = get_naver_gold_official()
fx = get_fx_rate()

if df_gold is not None:
    # 원화 환산 (돈당 가격)
    df_gold['won_don'] = (df_gold['종가'] / 31.1034) * fx * 3.75
    
    curr_p = df_gold['종가'].iloc[-1]
    prev_p = df_gold['종가'].iloc[-2]
    curr_won = df_gold['won_don'].iloc[-1]
    
    st.markdown('<p class="gs-title">🟡 국제 금 (네이버 공식 정산가)</p>', unsafe_allow_html=True)
    
    # 상단 요약 박스
    diff = curr_p - prev_p
    color = "up" if diff >= 0 else "down"
    sign = "▲" if diff >= 0 else "▼"
    
    st.markdown(f"""
    <div class="price-box">
        <div style="font-size:12px; color:#666;">공식 종가: ${curr_p:,.2f} <span class="{color}">{sign}{abs(diff):,.2f}</span></div>
        <div style="font-size:13px; margin-top:5px;">국내 환산가 (1돈)</div>
        <div class="val-main">{int(curr_won):,}원</div>
        <div style="font-size:11px; color:#999; margin-top:5px;">기준 환율: {fx:,.2f}원</div>
    </div>
    """, unsafe_allow_html=True)

    # 4. 차트 (금액 표시 기능 포함)
    fig = px.line(df_gold, y='won_don', markers=True)
    
    fig.update_traces(
        line_color='#f1c40f',
        customdata=df_gold[['won_don']],
        hovertemplate="날짜: %{x}<br>가격: %{customdata[0]:,.0f}원<extra></extra>"
    )
    
    fig.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=20, b=0),
        template="plotly_white",
        hovermode="x unified",
        yaxis=dict(fixedrange=True, title=None),
        xaxis=dict(fixedrange=True, title=None, tickformat='%m-%d')
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.error("네이버에서 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")
