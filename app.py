import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="국내 은행 가이드 시세", layout="centered")

# 디자인 고도화 (국내 은행 리포트 스타일)
st.markdown("""
    <style>
    .report-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #e1e4e8; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .bank-header { color: #0046ff; font-weight: 800; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; }
    .price-main { font-size: 28px; font-weight: 800; color: #1a1a1a; margin: 5px 0; }
    .diff-label { font-size: 14px; font-weight: 600; }
    .up { color: #d9534f; } .down { color: #0275d8; }
    </style>
    """, unsafe_allow_html=True)

# 2. 등락 계산 함수
def format_delta(curr, prev, is_usd=False):
    diff = curr - prev
    pct = (diff / prev) * 100
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    
    val_str = f"{abs(diff):.2f}" if is_usd else f"{int(abs(diff)):,}"
    return f'<span class="{color}">{sign} {val_str} ({pct:+.2f}%)</span>'

# 3. 데이터 로드
@st.cache_data(ttl=300)
def get_market_data():
    try:
        # 국제 금(GC=F), 환율(KRW=X), 은(SI=F)
        tickers = yf.download(["GC=F", "KRW=X", "SI=F"], period="1mo", interval="1d")['Close']
        df = tickers.ffill().rename(columns={"GC=F": "gold", "KRW=X": "ex", "SI=F": "silver"})
        return df
    except:
        return None

df = get_market_data()

st.title("🏦 금융 시장 지표 리포트")
st.caption("실시간 국제 금융 데이터를 기반으로 산출된 정보입니다.")

if df is not None:
    c = df.iloc[-1]
    p = df.iloc[-2]
    
    # 금 1돈 환산
    gold_don = (c['gold'] / 31.1035) * c['ex'] * 3.75
    prev_gold_don = (p['gold'] / 31.1035) * p['ex'] * 3.75

    # --- 리포트 섹션 ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
            <div class="report-card">
                <div class="bank-header">● 국제 금 시세 (1돈)</div>
                <div class="price-main">{int(gold_don):,}원</div>
                <div class="diff-label">{format_delta(gold_don, prev_gold_don)}</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="report-card">
                <div class="bank-header">● 원/달러 환율</div>
                <div class="price-main">{c['ex']:.2f}원</div>
                <div class="diff-label">{format_delta(c['ex'], p['ex'], True)}</div>
            </div>
        """, unsafe_allow_html=True)

    # 차트
    fig = px.line(df, y=(df['gold']/31.1035)*df['ex']*3.75, title="금 시세 흐름 (1돈/원)")
    fig.update_layout(xaxis_title=None, yaxis_title=None, height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.info("💡 국내 은행 파싱은 보안 정책상 차단될 확률이 높습니다. 현재 리포트는 글로벌 금융 시장 실시간 데이터를 기반으로 제공됩니다.")

else:
    st.error("데이터 서버에 연결할 수 없습니다.")
