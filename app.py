import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="금 국제 시세 리포트", layout="centered")

# CSS 디자인 (등락 표시를 위한 스타일 추가)
st.markdown("""
    <style>
    .main-title { font-size: 22px; font-weight: 700; margin-bottom: 15px; }
    .custom-container { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 20px; }
    .custom-item { flex: 1; background-color: #fdf2d0; padding: 12px 5px; border-radius: 10px; text-align: center; border-left: 4px solid #f1c40f; }
    .label-text { font-size: 11px; color: #666; margin-bottom: 3px; }
    .value-text { font-size: 16px; font-weight: 800; color: #1E1E1E; white-space: nowrap; }
    .delta-text { font-size: 12px; font-weight: 600; margin-top: 2px; }
    .up { color: #d9534f; }   /* 상승: 빨간색 */
    .down { color: #0275d8; } /* 하락: 파란색 */
    .equal { color: #666; }    /* 동일: 회색 */
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 불러오기
@st.cache_data(ttl=3600)
def get_data():
    try:
        gold_ticker = yf.Ticker("GC=F")
        ex_ticker = yf.Ticker("KRW=X")
        
        gold = gold_ticker.history(period="1mo")
        exchange = ex_ticker.history(period="1mo")
        
        if len(gold) < 2 or len(exchange) < 2:
            return None

        df = pd.DataFrame({'gold': gold['Close'], 'ex': exchange['Close']}).ffill()
        df['base_price'] = (df['gold'] * df['ex']) / 31.1035 * 3.75
        return df
    except:
        return None

def get_delta_info(current, previous):
    diff = current - previous
    if diff > 0:
        return f'<span class="delta-text up">▲ {int(diff):,}원</span>'
    elif diff < 0:
        return f'<span class="delta-text down">▼ {int(abs(diff)):,}원</span>'
    else:
        return f'<span class="delta-text equal">- 0원</span>'

data = get_data()

st.markdown('<p class="main-title">💰 금 국제 시세 리포트</p>', unsafe_allow_html=True)

if data is not None:
    curr = data.iloc[-1]
    prev = data.iloc[-2] # 전날 데이터
    
    # 등락 정보 계산
    price_delta_html = get_delta_info(curr['base_price'], prev['base_price'])
    ex_diff = curr['ex'] - prev['ex']
    ex_delta_html = f'<span class="delta-text up">▲ {ex_diff:.2f}</span>' if ex_diff > 0 else f'<span class="delta-text down">▼ {abs(ex_diff):.2f}</span>' if ex_diff < 0 else '<span class="delta-text">-</span>'

    # 3. 상단 지표 (전날 대비 등락 포함)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item">
                <div class="label-text">국제 금 1돈</div>
                <div class="value-text">{int(curr['base_price']):, }원</div>
                {price_delta_html}
            </div>
            <div class="custom-item">
                <div class="label-text">현재 달러 환율</div>
                <div class="value-text">{curr['ex']:.2f}원</div>
                {ex_delta_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 4. 차트 출력
    st.markdown('<p style="font-size:16px; font-weight:600; margin-top:10px;">📈 최근 30일 시세 추이</p>', unsafe_allow_html=True)
    y_min, y_max = data['base_price'].min() * 0.995, data['base_price'].max() * 1.005
    fig = px.line(data, y='base_price')
    fig.update_traces(line_color='#f1c40f') # 금색 선
    fig.update_layout(
        xaxis_title=None, yaxis_title=None,
        yaxis=dict(range=[y_min, y_max], tickformat=",.0f"),
        margin=dict(l=0, r=0, t=10, b=0), height=320,
        hovermode="x unified", dragmode=False
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
    
    st.caption(f"기준: 국제 금 ${curr['gold']:.2f} / t oz")

else:
    st.error("데이터 서버 요청 제한. 15~30분 후 다시 접속해 주세요.")

st.caption("공식: (국제금시세 * 환율) / 31.1035 * 3.75")
