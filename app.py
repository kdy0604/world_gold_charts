import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

# 2. 데이터 수집 함수 (네이버 내부 API 활용)
@st.cache_data(ttl=300)
def get_naver_gold_history():
    # 네이버 국제금(GCcv1) 일별 시세 API (최근 30일치)
    url = "https://pollux.stock.naver.com/api/jsonp/marketindex/getMarketIndexDay.nhn?marketindexCd=G_GC%40COMEX&pageSize=30&page=1"
    
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15.0)"}
    res = requests.get(url, headers=headers)
    
    # JSONP 형식을 JSON으로 변환
    content = res.text
    json_data = eval(content[content.find('(')+1 : content.rfind(')')])
    
    data_list = []
    for item in json_data['result']:
        data_list.append({
            '날짜': pd.to_datetime(item['localTrdDt']),
            '종가': float(item['closePrice'].replace(',', ''))
        })
    
    df = pd.DataFrame(data_list).set_index('날짜').sort_index()
    return df

# 3. 환율 수집
def get_current_fx():
    url = "https://marketindex.naver.com/api/iuser/marketindex/getChartData.nhn?marketindexCd=FX_USDKRW&periodType=day"
    res = requests.get(url).json()
    return float(res['result'][-1]['closePrice'])

# --- 실행 로직 ---
try:
    # 데이터 로드
    df_gold = get_naver_gold_history()
    fx_rate = get_current_fx()
    
    # 금 돈당 원화 환산 (공식 정산가 기준)
    df_gold['won_don'] = (df_gold['종가'] / 31.1034) * fx_rate * 3.75
    
    st.markdown("### 🟡 국제 금 시세 (네이버 공식 데이터)")
    st.write(f"현재 적용 환율: **{fx_rate:,.2f}원**")

    # 상단 요약 박스
    curr_p = df_gold['종가'].iloc[-1]
    prev_p = df_gold['종가'].iloc[-2]
    curr_won = df_gold['won_don'].iloc[-1]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("국제 정산가 ($/oz)", f"${curr_p:,.1f}", f"{curr_p - prev_p:+.1f}")
    with col2:
        st.metric("국내 환산가 (₩/돈)", f"{int(curr_won):,}원")

    # 차트 구성
    # [수정포인트] 터치 시 금액이 나오도록 customdata 설정
    fig = px.line(df_gold, y='won_don', markers=True, 
                  title="최근 30일 원화 환산가 추이 (정산가 기준)")
    
    fig.update_traces(
        line_color='#f1c40f',
        customdata=df_gold[['won_don']], 
        hovertemplate="날짜: %{x}<br>가격: %{customdata[0]:,.0f}원<extra></extra>"
    )
    
    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        yaxis_title=None,
        xaxis_title=None,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
