import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="금/은 국제 시세 리포트", layout="centered")

# CSS 디자인
st.markdown("""
    <style>
    .main-title { font-size: 20px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; }
    .custom-container { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 15px; }
    .custom-item { flex: 1; background-color: #f8f9fa; padding: 10px 3px; border-radius: 10px; text-align: center; border-left: 4px solid #dee2e6; min-width: 0; }
    .gold-box { background-color: #fdf2d0; border-left-color: #f1c40f; }
    .silver-box { background-color: #e9ecef; border-left-color: #adb5bd; }
    .label-text { font-size: 11px; color: #666; margin-bottom: 3px; white-space: nowrap; }
    .value-text { font-size: 15px; font-weight: 800; color: #1E1E1E; white-space: nowrap; }
    .delta-text { font-size: 11px; font-weight: 600; margin-top: 2px; display: block; }
    .up { color: #d9534f; }
    .down { color: #0275d8; }
    .equal { color: #666; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 불러오기 함수 (금, 은, 환율 통합)
@st.cache_data(ttl=3600)
def get_all_data():
    try:
        gold_t = yf.Ticker("GC=F")   # 금 선물
        silver_t = yf.Ticker("SI=F") # 은 선물
        ex_t = yf.Ticker("KRW=X")   # 환율
        
        g_h = gold_t.history(period="1mo")
        s_h = silver_t.history(period="1mo")
        e_h = ex_t.history(period="1mo")
        
        if g_h.empty or s_h.empty or e_h.empty: return None

        df = pd.DataFrame({
            'gold': g_h['Close'],
            'silver': s_h['Close'],
            'ex': e_h['Close']
        }).ffill()
        
        # 1돈(3.75g) 환산 공식 적용
        df['gold_don'] = (df['gold'] * df['ex']) / 31.1035 * 3.75
        df['silver_don'] = (df['silver'] * df['ex']) / 31.1035 * 3.75
        return df
    except:
        return None

def get_delta_html(curr_val, prev_val, is_currency=False):
    diff = curr_val - prev_val
    if diff > 0:
        v = f"{diff:.2f}" if is_currency else f"{int(diff):,}"
        return f'<span class="delta-text up">▲ {v}</span>'
    elif diff < 0:
        v = f"{abs(diff):.2f}" if is_currency else f"{int(abs(diff)):,}"
        return f'<span class="delta-text down">▼ {v}</span>'
    else:
        return '<span class="delta-text equal">- 0</span>'

data = get_all_data()

if data is not None:
    curr = data.iloc[-1]
    prev = data.iloc[-2]

    # --- 금(Gold) 섹션 ---
    st.markdown('<p class="main-title">🟡 국제 금 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item gold-box">
                <div class="label-text">금 1돈 (3.75g)</div>
                <div class="value-text">{int(curr['gold_don']):,}원</div>
                {get_delta_html(curr['gold_don'], prev['gold_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">현재 달러 환율</div>
                <div class="value-text">{curr['ex']:.2f}원</div>
                {get_delta_html(curr['ex'], prev['ex'], True)}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    fig_g = px.line(data, y='gold_don')
    fig_g.update_traces(line_color='#f1c40f')
    fig_g.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0),
                        yaxis=dict(range=[data['gold_don'].min()*0.99, data['gold_don'].max()*1.01], tickformat=",.0f"),
                        hovermode="x unified", dragmode=False)
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

    st.divider()

    st.caption("공식: (국제금시세 * 환율) / 31.1035 * 3.75")

    # --- 은(Silver) 섹션 ---
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (1돈)</p>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="custom-container">
            <div class="custom-item silver-box">
                <div class="label-text">은 1돈 (3.75g)</div>
                <div class="value-text">{int(curr['silver_don']):,}원</div>
                {get_delta_html(curr['silver_don'], prev['silver_don'])}
            </div>
            <div class="custom-item">
                <div class="label-text">국제 은 ($/oz)</div>
                <div class="value-text">${curr['silver']:.2f}</div>
                <span class="delta-text">{get_delta_html(curr['silver'], prev['silver'], True)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    fig_s = px.line(data, y='silver_don')
    fig_s.update_traces(line_color='#adb5bd') # 은색 선
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0),
                        yaxis=dict(range=[data['silver_don'].min()*0.98, data['silver_don'].max()*1.02], tickformat=",.0f"),
                        hovermode="x unified", dragmode=False)
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

else:
    st.error("데이터 로드 실패. 잠시 후 새로고침 해주세요.")

st.caption("공식: (국제시세 * 환율) / 31.1035 * 3.75")
