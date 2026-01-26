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

# 차트 공통 설정
def update_chart_layout(fig, y_min, y_max):
    fig.update_layout(
        height=300, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(range=[y_min, y_max], fixedrange=True, title=None),
        xaxis=dict(fixedrange=True, title=None),
        dragmode=False, hovermode="x unified", template="plotly_white"
    )
    return fig

def get_delta_html(curr, prev, prefix="", is_percent=True):
    if prev == 0: return ""
    diff = curr - prev
    pct = (diff / prev) * 100
    color = "up" if diff > 0 else "down"
    sign = "▲" if diff > 0 else "▼"
    res = f'<span class="{color}">{sign} {prefix}{abs(diff):,.2f}'
    if is_percent: res += f' ({pct:+.2f}%)'
    res += '</span>'
    return res

# 2. 국제 데이터 (계산식 전면 수정)
@st.cache_data(ttl=120)
def get_intl_full_data():
    try:
        # 야후 파이낸스 데이터 호출
        df = yf.download(["GC=F", "SI=F", "KRW=X"], period="3mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill()
        
        # 실시간 현재가로 마지막 행 업데이트 (오늘 날짜 반영)
        today_val = {}
        for t, col in zip(["GC=F", "SI=F", "KRW=X"], ["gold", "silver", "ex"]):
            live = yf.Ticker(t).fast_info.last_price
            if live and live > 0:
                df.iloc[-1, df.columns.get_loc(col)] = live
        
        # 모든 행에 대해 돈당 가격 계산 (이미지 3번의 급락 현상 방지)
        # 1온스 = 31.1034768g, 1돈 = 3.75g
        df['gold_don'] = (df['gold'] / 31.1034768) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1034768) * df['ex'] * 3.75
        
        update_time = datetime.now(KST).strftime('%Y-%m-%d %H:%M')
        return df, update_time
    except Exception as e:
        return None, f"Error: {e}"

# 3. 국내 데이터 (KeyError 방지)
@st.cache_data(ttl=3600)
def get_krx_safe_data():
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    raw_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    try:
        res = requests.get(url, params={'serviceKey': unquote(raw_key), 'numOfRows': '500', 'resultType': 'xml'}, timeout=15)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        if not items: return None, None
        
        data_list = []
        for item in items:
            name = item.findtext('itmsNm', '')
            if "금" in name and "99.99" in name and "미니" not in name:
                data_list.append({
                    '날짜': pd.to_datetime(item.findtext('basDt')),
                    '종가': float(item.findtext('clpr', 0)) * 3.75,
                    '등락률': float(item.findtext('flctRt', 0))
                })
        df_k = pd.DataFrame(data_list).drop_duplicates('날짜').sort_values('날짜')
        return df_k, df_k['날짜'].iloc[-1].strftime('%Y-%m-%d')
    except: return None, None

# 데이터 로드
df_intl, intl_time = get_intl_full_data()
df_krx, krx_date = get_krx_safe_data()

st.markdown('<p class="gs-title">📊 금/은 마켓 실시간 대시보드</p>', unsafe_allow_html=True)

# --- 섹션 1: 국제 금 ---
if df_intl is not None and not df_intl.empty:
    curr, prev = df_intl.iloc[-1], df_intl.iloc[-2]
    
    st.markdown(f'<div class="fx-container"><span style="font-size:14px;font-weight:600;">현재 원/달러 환율</span><div style="text-align:right;"><span style="font-size:18px;font-weight:800;">{curr["ex"]:,.2f}원</span> {get_delta_html(curr["ex"], prev["ex"])}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<p class="main-title">🟡 국제 금 시세 (Gold) <span class="ref-time">실시간: {intl_time} (KST)</span></p>', unsafe_allow_html=True)
    st.markdown(f"""<div class="price-container">
        <div class="price-box"><span class="val-sub">국제 시세 (1oz)</span><span class="val-main">${curr["gold"]:,.2f}</span>{get_delta_html(curr["gold"], prev["gold"], "$")}</div>
        <div class="price-box"><span class="val-sub">국내 환산가 (1돈)</span><span class="val-main">{int(curr["gold_don"]):,}원</span>{get_delta_html(curr["gold_don"], prev["gold_don"])}</div>
    </div>""", unsafe_allow_html=True)

    t1, t2 = st.tabs(["온스당 달러 ($/oz)", "돈당 원화 (₩/돈)"])
    with t1:
        st.plotly_chart(update_chart_layout(px.line(df_intl, y='gold'), df_intl['gold'].min()*0.98, df_intl['gold'].max()*1.02), use_container_width=True, config={'displayModeBar': False})
    with t2:
        st.plotly_chart(update_chart_layout(px.line(df_intl, y='gold_don').update_traces(line_color='#f1c40f'), df_intl['gold_don'].min()*0.98, df_intl['gold_don'].max()*1.02), use_container_width=True, config={'displayModeBar': False})

# --- 섹션 2: 국내 금 ---
if df_krx is not None and not df_krx.empty:
    latest_k = df_krx.iloc[-1]
    st.markdown(f'<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식) <span class="ref-time">기준일: {krx_date}</span></p>', unsafe_allow_html=True)
    st.markdown(f"""<div class="price-box" style="margin-bottom:15px;"><span class="val-sub">KRX 종가 (1돈 환산)</span><span class="val-main">{int(latest_k['종가']):,}원</span><span class="{'up' if latest_k['등락률'] > 0 else 'down'}">{'▲' if latest_k['등락률'] > 0 else '▼'} {abs(latest_k['등락률'])}%</span></div>""", unsafe_allow_html=True)
    st.plotly_chart(update_chart_layout(px.area(df_krx, x='날짜', y='종가').update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)'), df_krx['종가'].min()*0.98, df_krx['종가'].max()*1.02), use_container_width=True, config={'displayModeBar': False})

# --- 섹션 3: 국제 은 ---
if df_intl is not None:
    st.markdown(f'<p class="main-title">⚪ 국제 은 시세 (Silver) <span class="ref-time">실시간: {intl_time} (KST)</span></p>', unsafe_allow_html=True)
    st.markdown(f"""<div class="price-container">
        <div class="price-box"><span class="val-sub">국제 시세 (1oz)</span><span class="val-main">${curr["silver"]:,.2f}</span>{get_delta_html(curr["silver"], prev["silver"], "$")}</div>
        <div class="price-box"><span class="val-sub">국내 환산가 (1돈)</span><span class="val-main">{int(curr["silver_don"]):,}원</span>{get_delta_html(curr["silver_don"], prev["silver_don"])}</div>
    </div>""", unsafe_allow_html=True)
    s1, s2 = st.tabs(["온스당 달러 ($/oz)", "돈당 원화 (₩/돈)"])
    with s1:
        st.plotly_chart(update_chart_layout(px.line(df_intl, y='silver').update_traces(line_color='#adb5bd'), df_intl['silver'].min()*0.95, df_intl['silver'].max()*1.05), use_container_width=True, config={'displayModeBar': False})
    with s2:
        st.plotly_chart(update_chart_layout(px.line(df_intl, y='silver_don').update_traces(line_color='#adb5bd'), df_intl['silver_don'].min()*0.95, df_intl['silver_don'].max()*1.05), use_container_width=True, config={'displayModeBar': False})
