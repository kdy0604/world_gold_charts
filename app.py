import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, time
import pytz

# 1. 페이지 설정 및 한국 시간 설정
st.set_page_config(page_title="제네바시계 실시간 마켓", layout="centered")
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

# 2. 등락 표시 함수
def format_delta(curr, prev):
    if curr is None or prev is None: return ""
    diff = curr - prev
    pct = (diff / prev) * 100 if prev != 0 else 0
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    return f'<span class="{color}">{sign} {abs(diff):,.2f} ({pct:+.2f}%)</span>'

# 3. 데이터 로드 (국제 시세) - 로직 보강
@st.cache_data(ttl=600)
def get_intl_data():
    try:
        # 최근 7일치를 넉넉하게 가져와서 주말 공백을 메움
        tickers = ["GC=F", "SI=F", "KRW=X"]
        data = yf.download(tickers, period="7d", interval="10m", progress=False)
        
        if data.empty or 'Close' not in data:
            return None
            
        df = data['Close'].ffill().bfill() # 앞뒤 공백 모두 메움
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
        
        # 시간대 변환 (UTC -> KST)
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC').tz_convert('Asia/Seoul')
        else:
            df.index = df.index.tz_convert('Asia/Seoul')
        
        df['gold_don'] = (df['gold'] / 31.1035) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1035) * df['ex'] * 3.75
        
        # 필터링 조건: 오늘 8시 이후 데이터가 5개 이상이면 오늘치만, 아니면 최근 24시간치(144개)
        today_8am = KST.localize(datetime.combine(now_kst.date(), time(8, 0)))
        df_today = df[df.index >= today_8am]
        
        if len(df_today) > 5:
            return df_today
        else:
            return df.tail(144) # 최근 약 24시간 분량의 거래 데이터
    except Exception as e:
        print(f"Error: {e}")
        return None

# 4. 국내 KRX 데이터 로드
@st.cache_data(ttl=3600)
def get_krx_data():
    service_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    params = {'serviceKey': service_key, 'numOfRows': '35', 'resultType': 'xml'}
    try:
        res = requests.get(url, params=params, timeout=15)
        root = ET.fromstring(res.text)
        items = root.findall('.//item')
        hist = [{'날짜': pd.to_datetime(i.find('basDt').text), '종가': float(i.find('clpr').text)*3.75, '등락률': float(i.find('flctRt').text if i.find('flctRt') is not None else 0)} for i in items if i.find('clpr') is not None]
        return pd.DataFrame(hist).sort_values('날짜')
    except: return None

# 데이터 준비
df_intl = get_intl_data()
df_daily = yf.download(["GC=F", "SI=F", "KRW=X"], period="1mo", interval="1d", progress=False)['Close'].ffill()
df_daily = df_daily.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"})
df_daily['gold_don'] = (df_daily['gold'] / 31.1035) * df_daily['ex'] * 3.75
df_daily['silver_don'] = (df_daily['silver'] / 31.1035) * df_daily['ex'] * 3.75
df_krx = get_krx_data()

# 화면 출력
st.markdown('<p class="gs-title">📊 금/은 마켓 대시보드</p>', unsafe_allow_html=True)

# 1. 국제 금
st.markdown('<p class="main-title">🟡 국제 금 시세 (Gold)</p>', unsafe_allow_html=True)
if df_intl is not None and not df_intl.empty:
    c_rt = df_intl.iloc[-1]
    c_da, p_da = df_daily.iloc[-1], df_daily.iloc[-2]
    
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(c_rt['gold_don']):,}원</span>{format_delta(c_da['gold_don'], p_da['gold_don'])}</div>
            <div class="price-box"><span class="val-label">국제 시세 (1oz)</span><span class="val-main">${c_rt['gold']:.2f}</span>{format_delta(c_da['gold'], p_da['gold'])}</div>
        </div>
    """, unsafe_allow_html=True)

    t1, t2 = st.tabs(["실시간/주말유지 (10분)", "한달 기록 (일)"])
    with t1:
        fig = px.line(df_intl, y='gold_don', template="plotly_white")
        # Y축 자동 최적화 로직 보강
        y_range = [df_intl['gold_don'].min() * 0.998, df_intl['gold_don'].max() * 1.002]
        fig.update_traces(line_color='#f1c40f').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(range=y_range, autorange=False))
        st.plotly_chart(fig, use_container_width=True)
    with t2:
        fig = px.line(df_daily, y='gold_don', template="plotly_white")
        y_range_d = [df_daily['gold_don'].min() * 0.98, df_daily['gold_don'].max() * 1.02]
        fig.update_traces(line_color='#f1c40f').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(range=y_range_d, autorange=False))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("국제 금 시세를 불러오는 중입니다...")

# 2. 국내 금
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx is not None and not df_krx.empty:
    latest = df_krx.iloc[-1]
    st.markdown(f"""<div class="price-box" style="margin-bottom:15px;"><span class="val-label">KRX 종가 (1돈 환산)</span><span class="val-main">{int(latest['종가']):,}원</span><span class="{'up' if latest['등락률'] > 0 else 'down'}">{'▲' if latest['등락률'] > 0 else '▼'} {latest['등락률']}%</span></div>""", unsafe_allow_html=True)
    
    y_min_krx, y_max_krx = df_krx['종가'].min() * 0.995, df_krx['종가'].max() * 1.005
    fig_krx = px.area(df_krx, x='날짜', y='종가', template="plotly_white")
    fig_krx.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)')
    fig_krx.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(range=[y_min_krx, y_max_krx], autorange=False))
    st.plotly_chart(fig_krx, use_container_width=True)

# 3. 국제 은 (금과 동일 로직 적용)
st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
if df_intl is not None and not df_intl.empty:
    st.markdown(f"""
        <div class="price-container">
            <div class="price-box"><span class="val-label">국내 환산가 (1돈)</span><span class="val-main">{int(c_rt['silver_don']):,}원</span>{format_delta(c_da['silver_don'], p_da['silver_don'])}</div>
            <div class="price-box"><span class="val-label">국제 시세 (1oz)</span><span class="val-main">${c_rt['silver']:.2f}</span>{format_delta(c_da['silver'], p_da['silver'])}</div>
        </div>
    """, unsafe_allow_html=True)
    t3, t4 = st.tabs(["실시간/주말유지 (10분)", "한달 기록 (일)"])
    with t3:
        fig = px.line(df_intl, y='silver_don', template="plotly_white")
        y_range_s = [df_intl['silver_don'].min() * 0.99, df_intl['silver_don'].max() * 1.01]
        fig.update_traces(line_color='#adb5bd').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(range=y_range_s, autorange=False))
        st.plotly_chart(fig, use_container_width=True)
    with t4:
        fig = px.line(df_daily, y='silver_don', template="plotly_white")
        y_range_sd = [df_daily['silver_don'].min() * 0.97, df_daily['silver_don'].max() * 1.03]
        fig.update_traces(line_color='#adb5bd').update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0), xaxis_title=None, yaxis_title=None, yaxis=dict(range=y_range_sd, autorange=False))
        st.plotly_chart(fig, use_container_width=True)
