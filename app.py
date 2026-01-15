import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="금 시세 계산기", layout="centered")

st.title("💰 실시간 국제 금 1돈 시세")

# 데이터 캐싱 시간을 20분으로 늘려 'Too Many Requests' 방지
@st.cache_data(ttl=1200)
def get_gold_data():
    # 데이터 가져오기 (금: GC=F, 환율: KRW=X)
    gold = yf.Ticker("GC=F").history(period="1mo")
    exchange = yf.Ticker("KRW=X").history(period="1mo")
    
    df = pd.DataFrame({
        'gold_usd': gold['Close'],
        'usd_krw': exchange['Close']
    }).ffill()
    
    # 1돈 당 원화 계산
    df['price_krw_don'] = (df['gold_usd'] * df['usd_krw']) / 31.1035 * 3.75
    return df

try:
    data = get_gold_data()
    current_price = data['price_krw_don'].iloc[-1]
    current_ex = data['usd_krw'].iloc[-1]
    
    # 상단 지표
    col1, col2 = st.columns(2)
    col1.metric("금 1돈 (3.75g)", f"{int(current_price):,} 원")
    col2.metric("현재 환율", f"{current_ex:.2f} 원/$")

    # --- 차트 부분 수정 ---
    st.subheader("📈 최근 30일 금 1돈 시세 추이")
    
    # Y축 최솟값과 최댓값을 데이터 기준으로 설정 (여유공간 1%만 줌)
    y_min = data['price_krw_don'].min() * 0.99
    y_max = data['price_krw_don'].max() * 1.01

    fig = px.line(data, y='price_krw_don', render_mode='svg')
    
    # 차트 레이아웃 설정: Y축 범위를 데이터에 밀착시켜 굴곡 강조
    fig.update_yaxes(range=[y_min, y_max], nticks=10)
    fig.update_layout(
        xaxis_title=None,
        yaxis_title="원(KRW)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=400,
        hovermode="x unicode"
    )
    
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중입니다. 잠시 후 새로고침 해주세요. (오류: {e})")

st.caption("공식: (국제금시세 * 환율) / 31.1035 * 3.75")
