import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="금 시세 계산기", layout="centered")

st.title("💰 실시간 국제 금 1돈 시세")

# 캐싱 시간을 30분(1800초)으로 늘려 'Too Many Requests' 방지
@st.cache_data(ttl=1800)
def get_gold_data():
    # 데이터 가져오기 (금: GC=F, 환율: KRW=X)
    gold = yf.Ticker("GC=F").history(period="1mo")
    exchange = yf.Ticker("KRW=X").history(period="1mo")
    
    df = pd.DataFrame({
        'gold_usd': gold['Close'],
        'usd_krw': exchange['Close']
    }).ffill()
    
    # 1돈 당 원화 계산 (사용자 제공 공식)
    df['price_krw_don'] = (df['gold_usd'] * df['usd_krw']) / 31.1035 * 3.75
    return df

try:
    data = get_gold_data()
    current_price = data['price_krw_don'].iloc[-1]
    current_ex = data['usd_krw'].iloc[-1]
    last_gold_usd = data['gold_usd'].iloc[-1]
    
    # 지표 출력
    col1, col2 = st.columns(2)
    col1.metric("금 1돈 (3.75g)", f"{int(current_price):,} 원")
    col2.metric("현재 환율", f"{current_ex:.2f} 원/$")
    st.write(f"현재 국제 시세: ${last_gold_usd:.2f} / t oz")

    # --- 차트 설정 ---
    st.subheader("📈 최근 30일 금 1돈 시세 추이")
    
    # Y축을 데이터의 최솟값과 최댓값에 아주 가깝게 붙여 굴곡을 강조합니다.
    y_min = data['price_krw_don'].min() * 0.995
    y_max = data['price_krw_don'].max() * 1.005

    fig = px.line(data, y='price_krw_don')
    
    fig.update_layout(
        xaxis_title=None,
        yaxis_title="원(KRW)",
        yaxis=dict(range=[y_min, y_max], tickformat=",.0f"), # Y축 범위 고정 및 천단위 콤마
        margin=dict(l=10, r=10, t=10, b=10),
        height=400,
        hovermode="x unified" # 오류 수정됨
    )
    
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning("데이터를 가져오는 중입니다. 잠시 후(약 10분 뒤) 새로고침 해주세요.")
    st.info("현재 Yahoo Finance 서버의 요청 제한에 걸려있을 수 있습니다.")

st.caption("공식: (국제금시세 * 환율) / 31.1035 * 3.75")
