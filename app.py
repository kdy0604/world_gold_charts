import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="금/은 국제 시세", layout="centered")

# CSS 수정: 전체 컨테이너에 강제 여백 부여
st.markdown("""
    <style>
    /* 전체 앱의 최대 너비를 제한하고 중앙 정렬하여 양옆 스크롤 여백 확보 */
    .block-container {
        max-width: 90% !important;
        padding-left: 5% !important;
        padding-right: 5% !important;
    }
    
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
    
    /* 차트 영역에서 터치 스크롤을 방해하지 않도록 설정 */
    .stPlotlyChart { touch-action: pan-y !important; }
    </style>
    """, unsafe_allow_html=True)

# ... (중략: 데이터 로드 및 델타 함수는 이전과 동일) ...

if data is not None:
    curr = data.iloc[-1]
    prev = data.iloc[-2]

    # 금 섹션
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
    
    # 차트 출력 (columns 제거하고 바로 출력해도 CSS가 여백을 조절함)
    fig_g = px.line(data, y='gold_don')
    fig_g.update_traces(line_color='#f1c40f')
    fig_g.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0),
                        yaxis=dict(range=[data['gold_don'].min()*0.99, data['gold_don'].max()*1.01], tickformat=",.0f"),
                        hovermode="x", dragmode=False)
    st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

    st.divider()

    # 은 섹션 (금과 동일한 방식으로 처리)
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
                {get_delta_html(curr['silver'], prev['silver'], True)}
            </div>
        </div>
        """, unsafe_allow_html=True)

    fig_s = px.line(data, y='silver_don')
    fig_s.update_traces(line_color='#adb5bd')
    fig_s.update_layout(xaxis_title=None, yaxis_title=None, height=250, margin=dict(l=0,r=0,t=10,b=0),
                        yaxis=dict(range=[data['silver_don'].min()*0.98, data['silver_don'].max()*1.02], tickformat=",.0f"),
                        hovermode="x", dragmode=False)
    st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
