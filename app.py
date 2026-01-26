import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from datetime import datetime
import pytz

# 1. 페이지 설정 및 시간
st.set_page_config(page_title="제네바시계 마켓 대시보드", layout="centered")
KST = pytz.timezone('Asia/Seoul')

# 스타일 설정
st.markdown("""
    <style>
    .gs-title { font-size: 26px; font-weight: 800; margin-bottom: 5px; color: #1e1e1e; }
    .main-title { font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 5px; border-left: 5px solid #4361ee; padding-left: 10px; }
    .ref-time { font-size: 12px; color: #777; font-weight: 400; display: block; margin-bottom: 10px; }
    .price-box { flex: 1; background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; }
    .val-main { font-size: 20px; font-weight: 800; color: #111; display: block; }
    .val-sub { font-size: 11px; color: #666; margin-bottom: 5px; display: block; }
    .up { color: #d9534f; font-weight: 600; font-size: 12px; } .down { color: #0275d8; font-weight: 600; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 국내 KRX 데이터 로드 (날짜 정합성 강화)
@st.cache_data(ttl=3600)
def get_krx_final_data():
    url = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getGoldPriceInfo"
    raw_key = "ca42a8df54920a2536a7e5c4efe6594b2265a445a39ebc36244d108c5ae9e87a"
    try:
        res = requests.get(url, params={'serviceKey': unquote(raw_key), 'numOfRows': '300', 'resultType': 'xml'}, timeout=15)
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
        # 데이터프레임 생성 및 날짜순 정렬
        df_k = pd.DataFrame(data_list).drop_duplicates('날짜').sort_values('날짜')
        
        # 마지막 데이터 날짜 가져오기
        last_date = df_k['날짜'].iloc[-1].strftime('%Y-%m-%d')
        return df_k, last_date
    except:
        return None, None

df_krx, krx_date = get_krx_final_data()

# --- 화면 출력 ---
st.markdown('<p class="gs-title">📊 금/은 마켓 실시간 대시보드</p>', unsafe_allow_html=True)

# (국제 금/은 섹션은 생략 - 이전과 동일하게 유지)

# --- 국내 금 시세 섹션 ---
st.markdown(f'<p class="main-title">🇰🇷 국내 금 시세 (KRX 공식)</p>', unsafe_allow_html=True)
if df_krx is not None:
    latest_k = df_krx.iloc[-1]
    
    # 1. 상단 금액 박스 (기준일 명시)
    st.markdown(f"""
        <div class="price-box" style="margin-bottom:15px;">
            <span class="val-sub">KRX 공식 종가 (1돈 기준)</span>
            <span class="val-main">{int(latest_k['종가']):,}원</span>
            <span class="{'up' if latest_k['등락률'] > 0 else 'down'}">
                {'▲' if latest_k['등락률'] > 0 else '▼'} {abs(latest_k['등락률'])}% 
                <small style="color:#888; font-weight:400; font-size:11px;">({krx_date} 기준)</small>
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. 국내 차트 (여백 없이 실제 데이터 날짜까지만 표시)
    fig_k = px.area(df_krx, x='날짜', y='종가')
    fig_k.update_layout(
        height=300, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(range=[df_krx['종가'].min()*0.98, df_krx['종가'].max()*1.02], fixedrange=True, title=None),
        xaxis=dict(
            fixedrange=True, 
            title=None,
            range=[df_krx['날짜'].min(), df_krx['날짜'].max()] # 차트 범위를 데이터 날짜로 고정
        ),
        dragmode=False, hovermode="x unified", template="plotly_white"
    )
    st.plotly_chart(fig_k.update_traces(line_color='#4361ee', fillcolor='rgba(67, 97, 238, 0.1)'), use_container_width=True, config={'displayModeBar': False})
    
    st.markdown(f'<span class="ref-time">* 국내 시세는 평일 오후 4시경 확정되는 KRX 종가 데이터를 기준으로 하며, 주말/공휴일에는 변동되지 않습니다.</span>', unsafe_allow_html=True)
