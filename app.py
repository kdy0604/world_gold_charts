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
    .price-text { font-size: 25px !important; font-weight: 800; color: #1E1E1E;} #  margin-bottom: -5px;  삭제
    .exchange-text { font-size: 18px !important; font-weight: 600; color: #444; }
    .stMetric { padding: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <style>
    /* 가로 정렬을 강제하는 컨테이너 */
    .custom-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        margin-bottom: 15px;
    }
    .custom-item {
        flex: 1;
        background-color: #fdf2d0;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        min-width: 0; /* 글자가 넘칠 때 레이아웃 깨짐 방지 */
    }
    .label-text { font-size: 13px; color: #666; margin-bottom: 5px; }
    .value-text { font-size: 18px; font-weight: 800; color: #1E1E1E; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

try:
    data = get_data()
    curr = data.iloc[-1]
    
    st.markdown('<p style="font-size:20px; font-weight:700;">💰 금 시세 대시보드</p>', unsafe_allow_html=True)

    # --- 줄바꿈 없는 가로 병렬 레이아웃 ---
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item">
                <div class="label-text">금 1돈 (3.75g)</div>
                <div class="value-text">{int(curr['kr_estimate']):, }원</div>
            </div>
            <div class="custom-item">
                <div class="label-text">현재 환율</div>
                <div class="value-text">{curr['ex']:.2f}원</div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )
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
    except Exception as e:
    st.error("데이터 로딩 중...")



st.caption("공식: (국제금시세 * 환율) / 31.1035 * 3.75")
