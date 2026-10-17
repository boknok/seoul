# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ──────────────────────────────────────────────────────────────
# 1. 데이터 로드 · 전처리
# ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path: str = "seoul_temperature.csv") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")

    # 날짜 값 앞에 붙은 탭 문자 제거 (strip 처리)
    df["날짜"] = df["날짜"].astype(str).str.strip("\t")
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")

    # 기온 컬럼을 수치형으로 변환
    for col in ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["날짜"])
    return df


df = load_data()

# 연도 컬럼 추가
df["연도"] = df["날짜"].dt.year

# 연도별 집계: 평균·최고·최저
yearly = (
    df.groupby("연도")
    .agg(
        평균기온=("평균기온(℃)", "mean"),
        최고기온=("최고기온(℃)", "mean"),
        최저기온=("최저기온(℃)", "mean"),
    )
    .reset_index()
)

# 5년 이동평균 (최소 1개 데이터부터 계산)
yearly["5년이동평균"] = yearly["평균기온"].rolling(window=5, min_periods=1).mean()

# ──────────────────────────────────────────────────────────────
# 2. 사이드바 · 연도 범위 슬라이더
# ──────────────────────────────────────────────────────────────
min_year = int(yearly["연도"].min())
max_year = int(yearly["연도"].max())

start_year, end_year = st.sidebar.slider(
    "연도 범위",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),
    step=1,
)

selected = yearly[(yearly["연도"] >= start_year) & (yearly["연도"] <= end_year)]

# ──────────────────────────────────────────────────────────────
# 3. 연도별 평균기온 + 5년 이동평균 꺾은선 그래프
# ──────────────────────────────────────────────────────────────
fig = go.Figure()

# 연도별 평균기온 (파란 실선)
fig.add_trace(
    go.Scatter(
        x=selected["연도"],
        y=selected["평균기온"],
        mode="lines+markers",
        name="연평균기온",
        line=dict(color="#1f77b4", width=2.5),
        marker=dict(size=6, symbol="circle"),
    )
)

# 5년 이동평균 (빨간 점선)
fig.add_trace(
    go.Scatter(
        x=selected["연도"],
        y=selected["5년이동평균"],
        mode="lines",
        name="5년 이동평균",
        line=dict(color="#d62728", width=2.5, dash="dash"),
    )
)

fig.update_layout(
    title=f"{start_year}년 ~ {end_year}년 서울 연평균기온 추이",
    xaxis_title="연도",
    yaxis_title="기온 (℃)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    height=480,
    margin=dict(l=40, r=20, t=60, b=40),
    xaxis=dict(tickmode="linear", tick0=start_year, dtick=1),
    template="plotly_white",
)

st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# 4. 선택 구간의 평균 · 최고 · 최저 기온
# ──────────────────────────────────────────────────────────────
st.subheader(f"{start_year}년 ~ {end_year}년 구간 기온 요약")

summary = pd.DataFrame(
    {
        "지표": ["평균 기온", "최고 기온", "최저 기온"],
        "값 (℃)": [
            round(selected["평균기온"].mean(), 2),
            round(selected["최고기온"].mean(), 2),
            round(selected["최저기온"].mean(), 2),
        ],
    }
)

st.dataframe(summary, use_container_width=True, hide_index=True)

st.info(
    f"※ {start_year}년~{end_year}년에 해당하는 총 {len(selected)}개 연도 데이터를 기준으로 계산했습니다."
)
