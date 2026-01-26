import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# 1. 페이지 설정
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 5px; color: #1e1e1e; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 5px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 22px; font-weight: 800; color: #d9534f; display: block; }
    .val-sub { font-size: 12px; color: #666; margin-bottom: 5px; display: block; }
    .up { color: #d9534f; font-weight: 600; } .down { color: #0275d8; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 파싱: 네이버 국내 실시간 시세 (89만원대 일치화) ---
def get_naver_gold_data():
    try:
        url = "https://finance.naver.com/marketindex/goldDetail.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 실시간 현재가 (1g 기준) -> 이미지의 238,000원 추출
        price_tag = soup.select_one("div.day_data p.no_today em span.blind")
        price_1g = float(price_tag.text.replace(',', ''))
        
        # 전일 대비 등락
        diff_tag = soup.select_one("div.day_data p.no_ex em span.blind")
        diff_val = float(diff_tag.text.replace(',', ''))
        
        # 전일 대비 등락 기호 (up/down)
        direction = "up" if "상승" in str(soup.select_one("div.day_data p.no_ex em")) else "down"
        
        return {
            'price_don': price_1g * 3.75,
            'diff_don': diff_val * 3.75,
            'direction': direction,
            'price_1g': price_1g
        }
    except:
        return None

# --- 3. 데이터 로드: 국내 금 차트 (네이버 일별 시세 활용) ---
@st.cache_data(ttl=600)
def get_krx_chart_data():
    try:
        # 네이버 금융 일별 시세 페이지 (최근 데이터 확보용)
        url = "https://finance.naver.com/marketindex/worldDailyQuote.naver?marketindexCd=G_KRX_GOLD&fdtc=0"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        df_list = pd.read_html(res.text)
        df = df_list[0].dropna()
        df.columns = ['날짜', '종가', '전일대비', '등락률', '거래량', '거래대금']
        
        df['날짜'] = pd.to_datetime(df['날짜'])
        df = df.sort_values('날짜')
        df['종가_돈'] = df['종가'] * 3.75
        df.set_index('날짜', inplace=True)
        return df
    except:
        return None

# --- 4. 데이터 로드: 국제 금/은/환율 (Yahoo Finance) ---
@st.cache_data(ttl=120)
def get_intl_data():
    try:
        df = yf.download(["GC=F", "SI=F", "KRW=X"], period="2mo", interval="1d", progress=False)['Close']
        df = df.rename(columns={"GC=F": "gold", "SI=F": "silver", "KRW=X": "ex"}).ffill().dropna()
        
        # 실시간 반영
        for t, col in zip(["GC=F", "SI=F", "KRW=X"], ["gold", "silver", "ex"]):
            live = yf.Ticker(t).fast_info.last_price
            if live > 0: df.iloc[-1, df.columns.get_loc(col)] = live
            
        df['gold_don'] = (df['gold'] / 31.1034) * df['ex'] * 3.75
        df['silver_don'] = (df['silver'] / 31.1034) * df['ex'] * 3.75
        return df
    except: return None

# 데이터 실행
naver_gold = get_naver_gold_data()
df_krx = get_krx_chart_data()
df_intl = get_intl_data()

st.markdown('<p class="gs-title">📊 금/은 마켓 실시간 대시보드</p>', unsafe_allow_html=True)

# --- [섹션 1] 국내 금 시세 (이미지 일치화) ---
st.markdown('<p class="main-title">🇰🇷 국내 금 시세 (KRX 기준 실시간)</p>', unsafe_allow_html=True)
if naver_gold:
    color = "up" if naver_gold['direction'] == "up" else "down"
    sign = "▲" if naver_gold['direction'] == "up" else "▼"
    
    st.markdown(f"""
        <div class="price-box">
            <span class="val-sub">현재 국내 시세 (1돈 기준)</span>
            <span class="val-main">{int(naver_gold['price_don']):,}<small>원</small></span>
            <span class="{color}" style="font-size:14px;">{sign} {int(naver_gold['diff_don']):,}원</span>
            <span style="font-size:12px; color:#888; display:block; margin-top:5px;">데이터 기준: {datetime.now(KST).strftime('%m월 %d일 %H:%M')}</span>
        </div>
    """, unsafe_allow_html=True)

if df_krx is not None:
    # 차트 상단 0으로 떨어지는 구간 방지를 위해 오늘 데이터 업데이트
    if naver_gold:
        today = df_krx.index[-1]
        df_krx.loc[today, '종가_돈'] = naver_gold['price_don']

    fig_k = px.area(df_krx, y='종가_돈', labels={'종가_돈':'원/돈'})
    fig_k.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), template="plotly_white",
                        yaxis=dict(range=[df_krx['종가_돈'].min()*0.99, df_krx['종가_돈'].max()*1.01], title=None),
                        xaxis=dict(title=None))
    st.plotly_chart(fig_k.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)'), use_container_width=True)

# --- [섹션 2] 국제 금 시세 ---
if df_intl is not None:
    curr = df_intl.iloc[-1]
    st.markdown(f'<p class="main-title">🟡 국제 금 시세 (Gold) <span style="font-size:12px; font-weight:400; color:#888;">환율: {curr["ex"]:,.2f}원</span></p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1: st.markdown(f'<div class="price-box"><span class="val-sub">국제 시세 (1oz)</span><span style="font-size:18px; font-weight:800;">${curr["gold"]:,.2f}</span></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="price-box"><span class="val-sub">국내 환산가 (1돈)</span><span style="font-size:18px; font-weight:800;">{int(curr["gold_don"]):,}원</span></div>', unsafe_allow_html=True)

    fig_g = px.line(df_intl, y='gold_don')
    fig_g.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), template="plotly_white", yaxis=dict(title=None), xaxis=dict(title=None))
    st.plotly_chart(fig_g.update_traces(line_color='#f1c40f'), use_container_width=True)

# --- [섹션 3] 국제 은 시세 ---
if df_intl is not None:
    st.markdown('<p class="main-title">⚪ 국제 은 시세 (Silver)</p>', unsafe_allow_html=True)
    fig_s = px.line(df_intl, y='silver_don')
    fig_s.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), template="plotly_white", yaxis=dict(title=None), xaxis=dict(title=None))
    st.plotly_chart(fig_s.update_traces(line_color='#adb5bd'), use_container_width=True)
