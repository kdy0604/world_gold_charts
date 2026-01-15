import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="금 1돈 시세 계산기", layout="centered")

st.title("💰 실시간 국제 금 1돈 시세")

@st.cache_data(ttl=600)
def get_gold_data():
    # 1. 데이터 가져오기 (최근 1개월)
    gold = yf.Ticker("GC=F").history(period="1mo")
    exchange = yf.Ticker("KRW=X").history(period="1mo")
    
    # 2. 날짜 기준으로 두 데이터 합치기 (데이터가 없는 날은 직전 값으로 채움)
    df = pd.DataFrame({
        'gold_usd': gold['Close'],
        'usd_krw': exchange['Close']
    }).ffill()
    
    # 3. 1돈 당 원화 계산 공식 적용
    # 공식: (금달러 * 환율) / 31.1035 * 3.75
    df['price_krw_don'] = (df['gold_usd'] * df['usd_krw']) / 31.1035 * 3.75
    
    return df

try:
    data = get_gold_data()
    current_price = data['price_krw_don'].iloc[-1]
    current_ex = data['usd_krw'].iloc[-1]
    last_gold_usd = data['gold_usd'].iloc[-1]

    # 메인 지표
    col1, col2 = st.columns(2)
    col1.metric("금 1돈 (3.75g)", f"{int(current_price):,} 원")
    col2.metric("현재 환율", f"{current_ex:.2f} 원/$")

    st.write(f"현재 국제 시세: ${last_gold_usd:.2f} / t oz")

    # 차트 시각화 (1돈 가격 기준)
    st.subheader("📈 최근 30일 금 1돈 시세 추이 (원)")
    st.line_chart(data['price_krw_don'])

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")

st.caption("공식: (국제금시세 * 환율) / 31.1035 * 3.75")
