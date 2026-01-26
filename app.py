import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="국제 금/은 시세 리포트", layout="centered")

st.markdown("""
    <style>
    .block-container { max-width: 90% !important; padding-left: 5% !important; padding-right: 5% !important; }
    .gs-title { font-size: clamp(20px, 7vw, 30px) !important; font-weight: 700; margin-top: 20px; margin-bottom: 5px; line-height: 1.2 !important; display: block !important; }
    .geneva-title { font-size: 14px; font-weight: 700; margin-top: 5px; margin-bottom: 20px; text-align: right !important; padding-right: 15px !important; color: #888; }
    .main-title { font-size: 19px; font-weight: 700; margin-top: 25px; margin-bottom: 12px; }
    .custom-container { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 15px; }
    .custom-item { flex: 1; background-color: #f8f9fa; padding: 12px 5px; border-radius: 12px; text-align: center; border-left: 4px solid #dee2e6; min-width: 0; }
    .gold-box { background-color: #fff9e6; border-left-color: #f1c40f; }
    .silver-box { background-color: #f1f3f5; border-left-color: #adb5bd; }
    .label-text { font-size: 11px; color: #666; margin-bottom: 4px; white-space: nowrap; }
    .value-text { font-size: 16px; font-weight: 800; color: #1E1E1E; white-space: nowrap; }
    .delta-text { font-size: 11px; font-weight: 600; margin-top: 3px; display: block; }
    .ex-info { text-align: right; padding: 10px; background: #f8f9fa; border-radius: 8px; margin-top: -10px; margin-bottom: 20px; border: 1px solid #eee; }
    .up { color: #d9534f; } .down { color: #0275d8; } .equal { color: #666; }
    </style>
    """, unsafe_allow_html=True)

# 2. 등락 계산 함수
def get_delta_html(curr, prev, is_currency=False):
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    if abs(diff) < 0.001: return '<span class="delta-text equal">- 0 (0.00%)</span>'
    sign = "▲" if diff > 0 else "▼"
    color = "up" if diff > 0 else "down"
    v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
    return f'<span class="delta-text {color}">{sign} {v} ({pct:+.2f}%)</span>'

# 3. 데이터 로드
@st.cache_data(ttl=600)
def load_data():
    try:
        # 금(GC=F), 은(SI=F), 환율(KRW=X)
        tickers = ["GC=F", "SI=F", "KRW=X"]
        data = yf.download(tickers, period="1mo", interval="1d")['Close']
        df = data.ffill().rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        return df
    except: return None

df = load_data()

st.markdown('<p class="gs-title">💰 국제 금/은 시세 리포트</p>', unsafe_allow_html=True)
st.markdown('<p class="geneva-title">by 제네바시계</p>', unsafe_allow_html=True)

if df is not None:
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    # --- 금(Gold) 섹션 ---
    st.markdown('<p class="main-title">🟡 국제 금 시세</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item gold-box">
                <div class="label-text">금 1돈 (원화 환산)</div>
                <div class="value-text">{int(curr['gold_don']):,}원</div>
                {get_delta_html(curr['gold_don'], prev['gold_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 금 (USD/oz)</div>
                <div class="value-text">${curr['gold']:.1f}</div>
                {get_delta_html(curr['gold'], prev['gold'], True)}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    fig_g = px.line(df, y='gold_don')
    fig_g.update_traces(line_color='#f1c40f', line_width=3)
    fig_g.update_layout(xaxis_title=None, yaxis_title=None, height=220, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False})

    # 환율 부가정보 (차트 아래 배치)
    st.markdown(f"""
        <div class="ex-info">
            <span style="font-size: 12px; color: #666;">기준 환율: <b>{curr['ex']:.2f}원</b></span>
            <span style="font-size: 11px;"> {get_delta_html(curr['ex'], prev['ex'], True)}</span>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- 은(Silver) 섹션 ---
    st.markdown('<p class="main-title">⚪ 국제 은 시세</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item silver-box">
                <div class="label-text">은 1돈 (원화 환산)</div>
                <div class="value-text">{int(curr['silver_don']):,}원</div>
                {get_delta_html(curr['silver_don'], prev['silver_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 은 (USD/oz)</div>
                <div class="value-text">${curr['silver']:.2f}</div>
                {get_delta_html(curr['silver'], prev['silver'], True)}
            </div>
        </div>
    """, unsafe_allow_html=True)

    fig_s = px.line(df, y='silver_don')
    fig_s.update_traces(line_color='#adb5bd', line_width=3)
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=220, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

    st.caption("데이터 제공: Yahoo Finance (전일 종가 대비 변동률)")
else:
    st.error("데이터 로딩 실패")
