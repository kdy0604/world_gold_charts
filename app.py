import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")

st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 20px; color: #1e1e1e; border-bottom: 2px solid #333; padding-bottom: 10px; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .fx-container { background-color: #f1f3f9; padding: 12px 18px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #dbe2ef; display: flex; justify-content: space-between; align-items: center; }
    .fx-value { font-size: 18px; font-weight: 800; color: #111; }
    .price-box { background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; margin-bottom: 10px; }
    .val-main { font-size: 22px; font-weight: 800; color: #111; display: block; }
    .up { color: #d9534f; font-weight: 600; } .down { color: #0275d8; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# 2. 국제 데이터 로드
@st.cache_data(ttl=3600)
def get_intl_data():
    try:
        df = yf.download(["GC=F", "SI=F", "KRW=X"], period="3mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill().dropna()
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        return df
    except: return None

# 3. 국내 데이터 로드 (필터링 로직 유연화)
@st.cache_data(ttl=3600)
def get_krx_data():
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    raw_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    try:
        res = requests.get(url, params={'serviceKey': unquote(raw_key), 'numOfRows': '300', 'resultType': 'xml'}, timeout=15)
        root = ET.fromstring(res.content)
        data_list = []
        
        for item in root.findall('.//item'):
            # 종목명을 가져와서 모든 공백 제거 및 대문자화
            name = item.findtext('itmsNm', '').replace(' ', '').upper()
            
            # 정확히 일치하지 않더라도 '금99.99'가 포함되어 있고 '미니'가 없으면 선택
            if "금99.99" in name and "미니" not in name:
                d_val = item.findtext('basDt')
                p_val = item.findtext('clpr')
                if d_val and p_val:
                    data_list.append({
                        '날짜': pd.to_datetime(d_val),
                        '종가': float(p_val) * 3.75,
                        '등락률': float(item.findtext('flctRt', 0))
                    })
        
        if not data_list: return None
        return pd.DataFrame(data_list).drop_duplicates('날짜').sort_values('날짜')
    except: return None

df_intl = get_intl_data()
df_krx = get_krx_data()

st.markdown('<p class="gs-title">📊 금/은 마켓 대시보드</p>', unsafe_allow_html=True)

# --- 섹션 1: 환율 및 국제 금 ---
if df_intl is not None and len(df_intl) >= 2:
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    diff_ex = curr['ex'] - prev['ex']
    
    st.markdown(f"""
        <div class="fx-container">
            <span style="font-size:14px; color:#555; font-weight:600;">현재 원/달러 환율</span>
            <div style="text-align:right;">
                <span class="fx-value">{curr['ex']:,.2f}원</span>
                <span class="{'up' if diff_ex > 0 else 'down'}" style="font-size:14px; margin-left:8px;">
                    {'▲' if diff_ex > 0 else '▼'} {abs(diff_ex):.2f}
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="price-box"><span style="font-size:12px; color:#666;">국내 환산가 (1돈)</span><span class="val-main">{int(curr["gold_don"]):,}원</span></div>', unsafe_allow_html=True)
    
    y_min, y_max = df_intl['gold_don'].min() * 0.995, df_intl['gold_don'].max() * 1.005
    fig_g = px.line(df_intl, y='gold_don', template="plotly_white")
    fig_g.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_min, y_max], autorange=False), xaxis_title=None, yaxis_title=None)
    fig_g.update_traces(line_color='#f1c40f', line_width=3)
    st.plotly_chart(fig_g, use_container_width=True)

# --- 섹션 2: 국내 금 시세 (KRX) ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx is not None and not df_krx.empty:
    latest_k = df_krx.iloc[-1]
    st.markdown(f"""
        <div class="price-box">
            <span style="font-size:12px; color:#666;">오늘의 KRX 종가 (1돈)</span>
            <span class="val-main">{int(latest_k['종가']):,}원</span>
            <span class="{'up' if latest_k['등락률'] > 0 else 'down'}">
                {'▲' if latest_k['등락률'] > 0 else '▼'} {abs(latest_k['등락률'])}%
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    yk_min, yk_max = df_krx['종가'].min() * 0.995, df_krx['종가'].max() * 1.005
    fig_k = px.area(df_krx, x='날짜', y='종가', template="plotly_white")
    fig_k.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[yk_min, yk_max], autorange=False), xaxis_title=None, yaxis_title=None)
    fig_k.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)')
    st.plotly_chart(fig_k, use_container_width=True)
else:
    # 필터링이 실패했을 경우를 위해 모든 종목명을 리스트로 보여주는 디버깅용 메시지 (나중에는 삭제 가능)
    st.info("국내 데이터를 필터링 중입니다. 잠시만 기다려주세요.")
