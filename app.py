import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. 페이지 설정 및 디자인
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
    .up { color: #d9534f; } .down { color: #0275d8; } .equal { color: #666; }
    </style>
    """, unsafe_allow_html=True)

# 2. 등락 계산 함수 (상단 배치)
def get_delta_html(curr, prev, is_currency=False):
    diff = curr - prev
    if abs(diff) < 0.001: return '<span class="delta-text equal">- 0</span>'
    if diff > 0:
        v = f"{diff:.2f}" if is_currency else f"{int(diff):,}"
        return f'<span class="delta-text up">▲ {v}</span>'
    v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
    return f'<span class="delta-text down">▼ {v}</span>'

# 3. 데이터 로드 (yfinance 기반)
@st.cache_data(ttl=600)
def load_international_data():
    try:
        # GC=F(금 선물), SI=F(은 선물), KRW=X(원/달러 환율)
        g = yf.Ticker("GC=F").history(period="1mo")
        s = yf.Ticker("SI=F").history(period="1mo")
        e = yf.Ticker("KRW=X").history(period="1mo")
        
        df = pd.DataFrame({'gold': g['Close'], 'silver': s['Close'], 'ex': e['Close']}).ffill()
        
        # 국제 시세 기반 1돈(3.75g) 환산 공식
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        
        return df
    except:
        return None

# 데이터 실행
data = load_international_data()

st.markdown('<p class="gs-title">💰 국제 금/은 시세 리포트</p>', unsafe_allow_html=True)
st.markdown('<p class="geneva-title">by 제네바시계</p>', unsafe_allow_html=True)

if data is not None:
    curr = data.iloc[-1]
    prev = data.iloc[-2]

    # --- 금(Gold) 섹션 ---
    st.markdown('<p class="main-title">🟡 국제 금 시세 (1돈 환산)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item gold-box">
                <div class="label-text">금 1돈 (원화 환산)</div>
                <div class="value-text">{int(curr['gold_don']):,}원</div>
                {get_delta_html(curr['gold_don'], prev['gold_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 금 ($/oz)</div>
                <div class="value-text">${curr['gold']:.1f}</div>
                {get_delta_html(curr['gold'], prev['gold'], True)}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    fig_g = px.line(data, y='gold_don')
    fig_g.update_traces(line_color='#f1c40f', line_width=3)
    fig_g.update_layout(xaxis_title=None, yaxis_title=None, height=220, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False})

    # --- 환율 정보 ---
    st.markdown(f"""
        <div style="text-align: right; padding: 10px; background: #f8f9fa; border-radius: 8px; margin: 10px 0;">
            <span style="font-size: 12px; color: #666;">기준 환율: <b>{curr['ex']:.2f}원</b></span>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- 은(Silver) 섹션 ---
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (1돈 환산)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item silver-box">
                <div class="label-text">은 1돈 (원화 환산)</div>
                <div class="value-text">{int(curr['silver_don']):,}원</div>
                {get_delta_html(curr['silver_don'], prev['silver_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 은 ($/oz)</div>
                <div class="value-text">${curr['silver']:.2f}</div>
                {get_delta_html(curr['silver'], prev['silver'], True)}
            </div>
        </div>
        """, unsafe_allow_html=True)

    fig_s = px.line(data, y='silver_don')
    fig_s.update_traces(line_color='#adb5bd', line_width=3)
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=220, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(tickformat=",.0f"), hovermode="x", dragmode=False)
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

    st.caption("데이터 출처: Yahoo Finance (국제 선물 시세 기준)")
else:
    st.error("데이터 로드에 실패했습니다. 잠시 후 다시 시도해 주세요.")
