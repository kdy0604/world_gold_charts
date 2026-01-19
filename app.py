import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. 페이지 설정 및 모바일 최적화 CSS
st.set_page_config(page_title="금 시세", layout="centered")

st.markdown("""
    <style>
    /* 제목 스타일 */
    .main-title { font-size: 22px; font-weight: 700; margin-bottom: 15px; text-align: left; }
    
    /* 가로 정렬(Flexbox) 컨테이너 */
    .custom-container {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 20px;
    }
    /* 개별 항목 박스 */
    .custom-item {
        flex: 1;
        background-color: #fdf2d0;
        padding: 12px 5px;
        border-radius: 10px;
        text-align: center;
        border-left: 4px solid #f1c40f;
    }
    .label-text { font-size: 12px; color: #666; margin-bottom: 5px; }
    .value-text { font-size: 17px; font-weight: 800; color: #1E1E1E; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 불러오기 함수
@st.cache_data(ttl=1800)
def get_data():
    gold = yf.Ticker("GC=F").history(period="1mo")
    exchange = yf.Ticker("KRW=X").history(period="1mo")
    df = pd.DataFrame({'gold': gold['Close'], 'ex': exchange['Close']}).ffill()
    
    # 계산 공식 (1.5% 국내 유통 마진 포함)
    df['base_price'] = (df['gold'] * df['ex']) / 31.1035 * 3.75
    df['kr_estimate'] = df['base_price'] * 1.015 
    return df

try:
    data = get_data()
    curr = data.iloc[-1]
    
    # 제목 출력
    st.markdown('<p class="main-title">💰 실시간 금 국제 시세 리포트</p>', unsafe_allow_html=True)

    # 3. 가로 병렬 배치 (금값과 환율)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item">
                <div class="label-text">국내 금 1돈 예상가</div>
                <div class="value-text">{int(curr['kr_estimate']):, }원</div>
            </div>
            <div class="custom-item">
                <div class="label-text">현재 달러 환율</div>
                <div class="value-text">{curr['ex']:.2f}원</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 4. 차트 설정 (터치/스크롤 방지 적용)
    st.markdown('<p style="font-size:16px; font-weight:600; margin-top:10px;">📈 최근 30일 시세 추이</p>', unsafe_allow_html=True)
    
    y_min, y_max = data['kr_estimate'].min() * 0.995, data['kr_estimate'].max() * 1.005
    
    fig = px.line(data, y='kr_estimate')
    
    # 차트 레이아웃 및 터치 방지(dragmode=False)
    fig.update_layout(
        xaxis_title=None, yaxis_title=None,
        yaxis=dict(range=[y_min, y_max], tickformat=",.0f"),
        margin=dict(l=0, r=0, t=10, b=0), 
        height=320,
        hovermode="x unified",
        dragmode=False  # 차트 위에서 손가락으로 드래그해도 화면 스크롤이 되도록 설정
    )
    
    # 차트 출력 및 줌 방지(scrollZoom: False)
    st.plotly_chart(
        fig, 
        use_container_width=True, 
        config={
            'displayModeBar': False, 
            'scrollZoom': False,
            'staticPlot': False # 툴팁(금액 보기)은 살리고 이동만 막음
        }
    )

    st.caption(f"기준: 국제 금 ${curr['gold']:.2f} / t oz")

except Exception as e:
    st.warning("데이터를 업데이트 중입니다. 잠시 후 새로고침 해주세요.")

st.info("💡 (국제시세 * 환율 / 31.1035 * 3.75) 공식에 국내 유통 마진 1.5%를 반영한 예상가입니다.")
