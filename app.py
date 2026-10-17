import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ──────────────────────────────────────────────────────────────
# 1. 데이터 로드 · 전처리
# ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path: str = "seoul_temperature.csv") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")

    # 날짜 값 앞의 탭 문자 제거
    df["날짜"] = df["날짜"].astype(str).str.strip("\t")
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")

    for col in ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["날짜"])
    return df


df = load_data()

# 파생 컬럼
df["연도"] = df["날짜"].dt.year
df["월"] = df["날짜"].dt.month
df["일"] = df["날짜"].dt.day
df["일교차"] = df["최고기온(℃)"] - df["최저기온(℃)"]

# 연도별 집계
yearly = (
    df.groupby("연도")
    .agg(
        평균기온=("평균기온(℃)", "mean"),
        최고기온=("최고기온(℃)", "mean"),
        최저기온=("최저기온(℃)", "mean"),
        평균일교차=("일교차", "mean"),
    )
    .reset_index()
)
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
df_selected = df[(df["연도"] >= start_year) & (df["연도"] <= end_year)]

# ──────────────────────────────────────────────────────────────
# 3. 연도별 평균기온 + 5년 이동평균 꺾은선 그래프
# ──────────────────────────────────────────────────────────────
fig1 = go.Figure()

fig1.add_trace(
    go.Scatter(
        x=selected["연도"],
        y=selected["평균기온"],
        mode="lines+markers",
        name="연평균기온",
        line=dict(color="#1f77b4", width=2.5),
        marker=dict(size=6),
    )
)
fig1.add_trace(
    go.Scatter(
        x=selected["연도"],
        y=selected["5년이동평균"],
        mode="lines",
        name="5년 이동평균",
        line=dict(color="#d62728", width=2.5, dash="dash"),
    )
)
fig1.update_layout(
    title=f"{start_year}년 ~ {end_year}년 서울 연평균기온 추이",
    xaxis_title="연도",
    yaxis_title="기온 (℃)",
    hovermode="x unified",
    height=420,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig1, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# 4. 월별 히트맵 (가로축: 월 1~12, 세로축: 연도, 색: 평균기온)
# ──────────────────────────────────────────────────────────────
heat = (
    df_selected.groupby(["연도", "월"])["평균기온(℃)"].mean()
    .unstack(fill_value=None)
    .reset_index()
)

heat_plot = heat.copy()
heat_plot = heat_plot[heat_plot["연도"] >= start_year]
heat_plot = heat_plot[heat_plot["연도"] <= end_year]
heat_mat = heat_plot.iloc[:, 1:].values.astype(float)
heat_mat[heat_mat == -float("inf")] = None

fig_heatmap = go.Figure(
    data=go.Heatmap(
        z=heat_mat,
        x=list(range(1, 13)),
        y=heat_plot["연도"].tolist(),
        colorscale="RdYlBu_r",
        colorbar=dict(title="평균기온 (℃)"),
        hoverongaps=False,
    )
)
fig_heatmap.update_layout(
    title=f"{start_year}년 ~ {end_year}년 월별 평균기온 히트맵",
    xaxis_title="월",
    yaxis_title="연도",
    xaxis=dict(tickmode="array", tickvals=list(range(1, 13))),
    height=420,
    template="plotly_white",
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# 5. 최고기온 상위 10일 / 최저기온 하위 10일
# ──────────────────────────────────────────────────────────────
top10_high = (
    df_selected.nlargest(10, "최고기온(℃)")
    .loc[:, ["날짜", "최고기온(℃)"]]
    .reset_index(drop=True)
)
top10_high.insert(1, "순위", range(1, 11))

bottom10_low = (
    df_selected.nsmallest(10, "최저기온(℃)")
    .loc[:, ["날짜", "최저기온(℃)"]]
    .reset_index(drop=True)
)
bottom10_low.insert(1, "순위", range(1, 11))

col1, col2 = st.columns(2)

with col1:
    st.subheader("최고기온 상위 10일")
    st.dataframe(
        top10_high.style.format({"날짜": lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""}),
        use_container_width=True,
        hide_index=True,
    )

with col2:
    st.subheader("최저기온 하위 10일")
    st.dataframe(
        bottom10_low.style.format({"날짜": lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""}),
        use_container_width=True,
        hide_index=True,
    )

# ──────────────────────────────────────────────────────────────
# 6. 일교차 컬럼 기반 연도별 평균 일교차 그래프
# ──────────────────────────────────────────────────────────────
fig_range = go.Figure()
fig_range.add_trace(
    go.Scatter(
        x=selected["연도"],
        y=selected["평균일교차"],
        mode="lines+markers",
        name="평균 일교차",
        line=dict(color="#2ca02c", width=2.5),
        marker=dict(size=6),
    )
)
fig_range.update_layout(
    title=f"{start_year}년 ~ {end_year}년 연도별 평균 일교차",
    xaxis_title="연도",
    yaxis_title="일교차 (℃)",
    hovermode="x unified",
    height=400,
    template="plotly_white",
)
st.plotly_chart(fig_range, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# 7. 선택 구간 요약
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
