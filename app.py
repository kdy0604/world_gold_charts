import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime, timedelta
import pytz

# 1. 페이지 및 시간 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 5px; color: #1e1e1e; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 5px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .ref-time { font-size: 12px; color: #777; font-weight: 400; display: block; margin-bottom: 10px; }
    .fx-container { background-color: #f1f3f9; padding: 12px 18px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #dbe2ef; display: flex; justify-content: space-between; align-items: center; }
    .price-container { display: flex; gap: 10px; margin-bottom: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-sub { font-size: 11px; color: #666; margin-bottom: 5px; display: block; }
    .up { color: #d9534f; font-weight: 600; font-size: 12px; } .down { color: #0275d8; font-weight: 600; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 통합 함수 (종가 + 실시간)
@st.cache_data(ttl=120) # 2분마다 갱신
def get_combined_intl_data():
    try:
        # 야후 파이낸스에서 실시간 시세(Ticker)와 과거 이력 동시 호출
        tickers = ["GC=F", "SI=F", "KRW=X"]
        data = yf.download(tickers, period="1mo", interval="1d", progress=False)
        
        # 'Close' 데이터 추출 및 정리
        df = data['Close'].ffill().dropna()
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
        
        # 실시간 현재가(Live Price) 가져오기
        live_data = {}
        for t in tickers:
            ticker_obj = yf.Ticker(t)
            # fast_info 또는 info에서 현재가 추출 (주말/휴장 시 마지막 종가 유지)
            live_data[t] = ticker_obj.fast_info.last_price
            
        # 오늘 날짜로 데이터 프레임에 강제 추가 (차트 끝점 갱신)
        today_kst = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
        
        # 마지막 데이터 날짜가 오늘이 아니라면 실시간 행 추가
        if df.index[-1] < today_kst:
            new_row = pd.DataFrame({
                'gold': [live_data["GC=F"]],
                'silver': [live_data["SI=F"]],
                'ex': [live_data["KRW=X"]]
            }, index=[today_kst])
            df = pd.concat([df, new_row])
        else:
            # 이미 오늘 날짜 행이 있다면 현재가로 업데이트
            df.iloc[-1] = [live_data["GC=F"], live_data["SI=F"], live_data["KRW=X"]]

        # 계산식 적용
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        
        update_time = datetime.now(KST).strftime('%Y-%m-%d %H:%M')
        return df, update_time
    except:
        return None, None

# 차트/유틸리티 함수 생략 (기존과 동일)
def update_chart_layout(fig, y_min, y_max):
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(range=[y_min, y_max], autorange=False, fixedrange=True, title=None),
        xaxis=dict(fixedrange=True, title=None),
        dragmode=False, hovermode="x unified", template="plotly_white")
    return fig

def get_delta_html(curr, prev, prefix="", is_percent=True):
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    return f'<span class="{color}">{sign} {prefix}{abs(diff):,.2f} ({pct:+.2f}%)</span>'

# 데이터 실행
df_intl, intl_time = get_combined_intl_data()
# 국내 데이터 부분은 이전 코드와 동일하게 유지 (중략)

# --- 출력 섹션 ---
st.markdown('<p class="gs-title">📊 금/은 마켓 실시간 대시보드</p>', unsafe_allow_html=True)

if df_intl is not None:
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    
    # 환율
    st.markdown(f'<div class="fx-container"><span style="font-size:14px;font-weight:600;">현재 원/달러 환율</span><div style="text-align:right;"><span style="font-size:18px;font-weight:800;">{curr["ex"]:,.2f}원</span> {get_delta_html(curr["ex"], prev["ex"])}</div></div>', unsafe_allow_html=True)

    # 국제 금 시세
    st.markdown(f'<p class="main-title">🟡 국제 금 시세 (Gold)</p><span class="ref-time">실시간 갱신: {intl_time} (KST)</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="price-container"><div class="price-box"><span class="val-sub">국제 시세 (1oz)</span><span class="val-main">${curr["gold"]:,.2f}</span>{get_delta_html(curr["gold"], prev["gold"], "$")}</div><div class="price-box"><span class="val-sub">국내 환산가 (1돈)</span><span class="val-main">{int(curr["gold_don"]):,}원</span>{get_delta_html(curr["gold_don"], prev["gold_don"])}</div></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["온스당 달러 ($/oz)", "돈당 원화 (₩/돈)"])
    with tab1:
        y_min, y_max = df_intl['gold'].min() * 0.99, df_intl['gold'].max() * 1.01
        fig = px.line(df_intl, x=df_intl.index, y='gold')
        st.plotly_chart(update_chart_layout(fig, y_min, y_max), use_container_width=True, config={'displayModeBar': False})
    with tab2:
        y_min, y_max = df_intl['gold_don'].min() * 0.99, df_intl['gold_don'].max() * 1.01
        fig = px.line(df_intl, x=df_intl.index, y='gold_don')
        st.plotly_chart(update_chart_layout(fig, y_min, y_max).update_traces(line_color='#f1c40f'), use_container_width=True, config={'displayModeBar': False})
