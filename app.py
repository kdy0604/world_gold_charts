import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. 페이지 설정 (모바일 최적화)
st.set_page_config(page_title="금 시세", layout="centered")

# 2. CSS를 이용한 글자 크기 및 여백 미세 조정
st.markdown("""
    <style>
    .main-title { font-size: 24px !important; font-weight: 700; margin-bottom: 10px; }
    .sub-title { font-size: 16px !important; color: #666; }
    .price-text { font-size: 30px !important; font-weight: 800; color: #1E1E1E; margin-bottom: -5px; }
    .exchange-text { font-size: 18px !important; font-weight: 600; color: #444; }
    .stMetric { padding: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=1800)
def get_gold_data():
    gold = yf.Ticker("GC=F").history(period="1mo")
    exchange = yf.Ticker("KRW=X").history(period="1mo")
    df = pd.DataFrame({'gold_usd': gold['Close'], 'usd_krw': exchange['Close']}).ffill()
    df['price_krw_don'] = (df['gold_usd'] * df['usd_krw']) / 31.1035 * 3.75
    return df

try:
    data = get_gold_data()
    current_price = data['price_krw_don'].iloc[-1]
    current_ex = data['usd_krw'].iloc[-1]
    last_gold_usd = data['gold_usd'].iloc[-1]
    
    # 상단 텍스트 (크기 조절됨)
    st.markdown('<p class="main-title">💰 실시간 금 1돈 국제 시세</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p class="sub-title">금 1돈 (3.75g)</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="price-text">{int(current_price):,} 원</p>', unsafe_allow_html=True)
    with col2:
        st.markdown('<p class="sub-title">현재 환율</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="exchange-text">{current_ex:.2f} 원/$</p>', unsafe_allow_html=True)

    st.write(f"🌐 국제 시세: ${last_gold_usd:.2f} / t oz")

    # --- 차트 설정 (모바일에서 보기 좋게 여백 제거) ---
    y_min, y_max = data['price_krw_don'].min() * 0.995, data['price_krw_don'].max() * 1.005
    fig = px.line(data, y='price_krw_don')
    fig.update_layout(
        xaxis_title=None, yaxis_title=None,
        yaxis=dict(range=[y_min, y_max], tickformat=",.0f"),
        margin=dict(l=0, r=0, t=10, b=0), # 차트 여백 최소화
        height=300, # 차트 높이 줄임
        hovermode="x unified",
        dragmode=False,  # 차트 위에서 드래그(슬라이딩) 기능을 끔
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.warning("데이터 로딩 중... 잠시 후 새로고침 하세요.")

st.caption("공식: (국제금시세 * 환율) / 31.1035 * 3.75")
