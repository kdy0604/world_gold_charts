import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, time
import pytz

# 1. 페이지 및 시간 설정
st.set_page_config(page_title="제네바시계 마켓", layout="centered")
KST = pytz.timezone('Asia/Seoul')
now_kst = datetime.now(KST)

st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 20px; color: #1e1e1e; border-bottom: 2px solid #333; padding-bottom: 10px; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .price-container { display: flex; gap: 10px; margin-bottom: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-label { font-size: 11px; color: #666; margin-bottom: 5px; display: block; }
    .up { color: #d9534f; font-weight: 600; font-size: 12px; } .down { color: #0275d8; font-weight: 600; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 유틸리티 함수
def format_delta(curr, prev):
    if curr is None or prev is None: return ""
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    return f'<span class="{color}">{sign} {abs(diff):,.2f} ({pct:+.2f}%)</span>'

# 3. 데이터 로드 (에러 방지를 위해 개별 호출)
@st.cache_data(ttl=300)
def get_safe_data(period="5d", interval="10m"):
    try:
        # 데이터 개별 로드 (구조적 에러 원천 차단)
        g_raw = yf.download("GC=F", period=period, interval=interval, progress=False)['Close']
        s_raw = yf.download("SI=F", period=period, interval=interval, progress=False)['Close']
        e_raw = yf.download("KRW=X", period=period, interval=interval, progress=False)['Close']
        
        # 데이터 통합
        df = pd.concat([g_raw, s_raw, e_raw], axis=1)
        df.columns = ['gold', 'silver', 'ex']
        df = df.ffill().bfill()
        
        # 시간대 변환
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC').tz_convert('Asia/Seoul')
        else:
            df.index = df.index.tz_convert('Asia/Seoul')
            
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        
        # 오늘 08:00 기준 필터링
        today_8am = KST.localize(datetime.combine(now_kst.date(), time(8, 0)))
        df_filtered = df[df.index >= today_8am]
        
        # 데이터가 너무 적으면 최근 144개(약 24시간) 반환
        return df_filtered if len(df_filtered) > 10 else df.tail(144)
    except:
        return None

# KRX 데이터 로드
@st.cache_data(ttl=3600)
def get_krx_data():
    try:
        service_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
        url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
        params = {'serviceKey': service_key, 'numOfRows': '30', 'resultType': 'xml'}
        res = requests.get(url, params=params, timeout=10)
        root = ET.fromstring(res.text)
        items = root.findall('.//item')
        hist = [{'날짜': pd.to_datetime(i.find('basDt').text), '종가': float(i.find('clpr').text)*3.75, '등락률': float(i.find('flctRt').text if i.find('flctRt') is not None else 0)} for i in items]
        return pd.DataFrame(hist).sort_values('날짜')
    except: return None

# 데이터 준비
df_intl = get_safe_data()
df_daily = get_safe_data(period="1mo", interval="1d")
df_krx = get_krx_data()

st.markdown('<p class="gs-title">📊 금/은 마켓 대시보드</p>', unsafe_allow_html=True)

# --- 1. 국제 금 ---
st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
if df_intl is not None:
    c_rt = df_intl.iloc[-1]
    c_da, p_da = df_daily.iloc[-1], df_daily.iloc[-2]
    
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(c_rt['gold_don']):,}원</span>{format_delta(c_da['gold_don'], p_da['gold_don'])}</div>
            <div class="price-box"><span class="val-label">국제 시세 (1oz)</span><span class="val-main">${c_rt['gold']:.2f}</span>{format_delta(c_da['gold'], p_da['gold'])}</div>
        </div>
    """, unsafe_allow_html=True)

    t1, t2 = st.tabs(["실시간/주말유지", "한달 기록"])
    with t1:
        fig = px.line(df_intl, y='gold_don', template="plotly_white")
        y_min, y_max = df_intl['gold_don'].min() * 0.999, df_intl['gold_don'].max() * 1.001
        fig.update_traces(line_color='#f1c40f').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_min, y_max], autorange=False), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with t2:
        fig = px.line(df_daily, y='gold_don', template="plotly_white")
        y_m_min, y_m_max = df_daily['gold_don'].min() * 0.98, df_daily['gold_don'].max() * 1.02
        fig.update_traces(line_color='#f1c40f').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_m_min, y_m_max], autorange=False), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

# --- 2. 국내 금 (KRX) ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx is not None:
    latest = df_krx.iloc[-1]
    st.markdown(f"""<div class="price-box" style="margin-bottom:15px;"><span class="val-label">KRX 종가 (1돈 환산)</span><span class="val-main">{int(latest['종가']):,}원</span><span class="{'up' if latest['등락률'] > 0 else 'down'}">{'▲' if latest['등락률'] > 0 else '▼'} {latest['등락률']}%</span></div>""", unsafe_allow_html=True)
    y_k_min, y_k_max = df_krx['종가'].min() * 0.995, df_krx['종가'].max() * 1.005
    fig_krx = px.area(df_krx, x='날짜', y='종가', template="plotly_white")
    fig_krx.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)')
    fig_krx.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_k_min, y_k_max], autorange=False), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_krx, use_container_width=True)

# --- 3. 국제 은 ---
st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
if df_intl is not None:
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(c_rt['silver_don']):,}원</span>{format_delta(c_da['silver_don'], p_da['silver_don'])}</div>
            <div class="price-box"><span class="val-label">국제 시세 (1oz)</span><span class="val-main">${c_rt['silver']:.2f}</span>{format_delta(c_da['silver'], p_da['silver'])}</div>
        </div>
    """, unsafe_allow_html=True)
    t3, t4 = st.tabs(["실시간/주말유지", "한달 기록"])
    with t3:
        fig = px.line(df_intl, y='silver_don', template="plotly_white")
        y_s_min, y_s_max = df_intl['silver_don'].min() * 0.995, df_intl['silver_don'].max() * 1.005
        fig.update_traces(line_color='#adb5bd').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_s_min, y_s_max], autorange=False), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with t4:
        fig = px.line(df_daily, y='silver_don', template="plotly_white")
        y_sm_min, y_sm_max = df_daily['silver_don'].min() * 0.97, df_daily['silver_don'].max() * 1.03
        fig.update_traces(line_color='#adb5bd').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(range=[y_sm_min, y_sm_max], autorange=False), xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
