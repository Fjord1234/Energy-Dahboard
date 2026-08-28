"""
제주 재생에너지 탐구 — 한 페이지 읽기형 대시보드 (dashboard2)
탐구보고서 서론·본론·결론 구조 / 그래프 4개 / 글 중심
"""

from __future__ import annotations

from pathlib import Path

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

DATA_CANDIDATES = ["전처리완료.csv", "preprocessed_complete.csv"]

BG = "#0b1020"
PANEL = "#121833"
GRID = "#3a4570"
TEXT = "#f4f6ff"
SOFT = "#d5dcff"
ACCENT = "#a78bfa"
ACCENT2 = "#60a5fa"
SOLAR = "#c084fc"
WIND = "#38bdf8"
WARN = "#e9d5ff"


def load_data() -> pd.DataFrame:
    path = next((p for p in DATA_CANDIDATES if Path(p).exists()), None)
    if path is None:
        raise FileNotFoundError(
            "전처리완료.csv 파일이 없습니다. 코랩 작업 폴더에 CSV를 업로드하세요."
        )
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    for c in df.columns:
        if c != "date":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["renewable_total_kwh"] = df["solar_total_kwh"].fillna(0) + df["wind_total_kwh"].fillna(0)
    return df


DF = load_data()


def style_fig(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=TEXT), x=0.02, xanchor="left"),
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=13),
        margin=dict(l=52, r=24, t=56, b=44),
        legend=dict(font=dict(color=TEXT, size=12)),
        xaxis=dict(gridcolor=GRID, color=TEXT, title_font=dict(color=TEXT), tickfont=dict(color=TEXT)),
        yaxis=dict(gridcolor=GRID, color=TEXT, title_font=dict(color=TEXT), tickfont=dict(color=TEXT)),
        hovermode="x unified",
    )
    return fig


def corr(x: str, y: str) -> float | None:
    d = DF[[x, y]].dropna()
    return float(d[x].corr(d[y])) if len(d) >= 5 else None


def build_stats() -> dict:
    d = DF.dropna(subset=["solar_total_kwh", "wind_total_kwh"])
    solar_sum = float(DF["solar_total_kwh"].sum(min_count=1) or 0)
    wind_sum = float(DF["wind_total_kwh"].sum(min_count=1) or 0)
    total = solar_sum + wind_sum
    solar_win = int((d["solar_total_kwh"] > d["wind_total_kwh"]).sum()) if len(d) else 0
    wind_win = int((d["wind_total_kwh"] > d["solar_total_kwh"]).sum()) if len(d) else 0
    thr = float(DF["renewable_total_kwh"].quantile(0.9))
    high_days = int((DF["renewable_total_kwh"] >= thr).sum())
    return {
        "start": DF["date"].min().strftime("%Y년 %m월 %d일"),
        "end": DF["date"].max().strftime("%Y년 %m월 %d일"),
        "days": int(DF["date"].nunique()),
        "solar_sum": solar_sum,
        "wind_sum": wind_sum,
        "total": total,
        "solar_pct": (solar_sum / total * 100) if total else 0,
        "wind_pct": (wind_sum / total * 100) if total else 0,
        "solar_win": solar_win,
        "wind_win": wind_win,
        "compare_days": len(d),
        "r_wind": corr("wind_avg_ms", "wind_total_kwh"),
        "r_sun": corr("sunshine_hr", "solar_total_kwh"),
        "thr": thr,
        "high_days": high_days,
    }


S = build_stats()


def chart_daily() -> go.Figure:
    d = DF.dropna(subset=["solar_total_kwh", "wind_total_kwh"], how="all")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d["solar_total_kwh"], name="태양광", line=dict(color=SOLAR, width=1.5)))
    fig.add_trace(go.Scatter(x=d["date"], y=d["wind_total_kwh"], name="풍력", line=dict(color=WIND, width=1.5)))
    fig.update_yaxes(title_text="발전량 (kWh)")
    fig.update_xaxes(title_text="날짜")
    return style_fig(fig, "그림 1. 제주 태양광·풍력 일별 발전량")


def chart_wind_scatter() -> go.Figure:
    d = DF.dropna(subset=["wind_avg_ms", "wind_total_kwh"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["wind_avg_ms"], y=d["wind_total_kwh"], mode="markers",
        marker=dict(size=7, color=WIND, opacity=0.7),
        text=d["date"].dt.strftime("%Y-%m-%d"),
        hovertemplate="풍속 %{x:.1f} m/s<br>발전량 %{y:,.0f} kWh<br>%{text}<extra></extra>",
    ))
    fig.update_xaxes(title_text="평균 풍속 (m/s)")
    fig.update_yaxes(title_text="풍력 발전량 (kWh)")
    return style_fig(fig, "그림 2. 바람이 세면 풍력 발전량도 늘어날까?")


def chart_solar_scatter() -> go.Figure:
    d = DF.dropna(subset=["sunshine_hr", "solar_total_kwh"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["sunshine_hr"], y=d["solar_total_kwh"], mode="markers",
        marker=dict(size=7, color=SOLAR, opacity=0.7),
        text=d["date"].dt.strftime("%Y-%m-%d"),
        hovertemplate="일조 %{x:.1f}시간<br>발전량 %{y:,.0f} kWh<br>%{text}<extra></extra>",
    ))
    fig.update_xaxes(title_text="일조시간 (시간)")
    fig.update_yaxes(title_text="태양광 발전량 (kWh)")
    return style_fig(fig, "그림 3. 햇빛이 많으면 태양광 발전량도 늘어날까?")


def chart_compare() -> go.Figure:
    d = DF.dropna(subset=["solar_total_kwh", "wind_total_kwh"]).copy()
    d["winner"] = "비슷함"
    d.loc[d["solar_total_kwh"] > d["wind_total_kwh"], "winner"] = "태양광 우세"
    d.loc[d["wind_total_kwh"] > d["solar_total_kwh"], "winner"] = "풍력 우세"
    counts = d["winner"].value_counts().reindex(["태양광 우세", "풍력 우세", "비슷함"]).fillna(0)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=counts.index.tolist(), y=counts.values.tolist(),
        marker_color=[SOLAR, WIND, SOFT],
        text=[f"{int(v)}일" for v in counts.values],
        textposition="outside", textfont=dict(color=TEXT),
    ))
    fig.update_yaxes(title_text="일수")
    return style_fig(fig, "그림 4. 하루 중 어느 쪽이 더 많이 만들었을까?")


def section_css() -> str:
    return f"""
    <style>
      .report-wrap {{ color: {TEXT}; line-height: 1.85; font-size: 1.02em; }}
      .report-wrap h1 {{ color: {TEXT}; font-size: 1.75em; margin: 0 0 0.4em 0; }}
      .report-wrap h2 {{
        color: {TEXT}; font-size: 1.35em; margin: 2.2em 0 0.6em 0;
        padding-bottom: 0.35em; border-bottom: 2px solid {ACCENT};
      }}
      .report-wrap h3 {{ color: {ACCENT}; font-size: 1.12em; margin: 1.4em 0 0.5em 0; }}
      .report-wrap p {{ color: {SOFT}; margin: 0.6em 0; }}
      .report-wrap strong {{ color: {TEXT}; }}
      .report-wrap ul {{ color: {SOFT}; margin: 0.5em 0 0.8em 1.2em; }}
      .report-wrap li {{ margin: 0.35em 0; }}
      .report-wrap .lead {{
        background: {PANEL}; border-left: 4px solid {ACCENT2};
        padding: 14px 18px; border-radius: 0 12px 12px 0; margin: 1em 0;
        color: {SOFT};
      }}
      .report-wrap .note {{
        background: {PANEL}; border: 1px solid {GRID};
        padding: 12px 16px; border-radius: 12px; margin: 1em 0;
        color: {SOFT}; font-size: 0.95em;
      }}
      .report-wrap .kpi {{
        display: flex; flex-wrap: wrap; gap: 12px; margin: 1em 0;
      }}
      .report-wrap .kpi span {{
        background: {PANEL}; border: 1px solid {GRID};
        padding: 8px 14px; border-radius: 10px; color: {TEXT}; font-size: 0.95em;
      }}
    </style>
    """


def intro_html() -> str:
    return section_css() + f"""
    <div class="report-wrap">
      <h1>제주 재생에너지 탐구 보고서</h1>
      <p class="lead">
        이전 탐구에서는 탄소 배출이 늘어나면 지구가 어떻게 달라질지를 시뮬레이션으로 살펴보았습니다.
        그렇다면 <strong>탄소를 줄이려면 무엇이 필요할까?</strong> 하는 질문으로,
        이번에는 <strong>재생에너지</strong>에 주목했습니다.
        특히 내가 살고 있는 <strong>제주</strong>에는 풍력과 태양광 설비가 많이 들어와 있습니다.
        그런데 정말로 <strong>날씨에 따라 발전량이 달라질까?</strong>
        그리고 재생에너지가 <strong>너무 많이 만들어지면</strong> 또 어떤 일이 생길까?
        이 페이지는 그 질문에 답하기 위해, 제주의 기상 데이터와 발전 데이터를 한데 모아 읽는 탐구 보고서입니다.
      </p>

      <h2>1. 서론 — 왜 이 탐구를 했을까?</h2>

      <h3>(1) 탐구 동기</h3>
      <p>
        첫 번째 탐구에서 IPCC 자료를 바탕으로 2100년 지구의 모습을 시뮬레이션해 보면서,
        기후 위기가 ‘먼 나라 이야기’가 아니라는 것을 느꼈습니다.
        탄소를 줄이려면 화석연료 대신 <strong>태양광·풍력 같은 재생에너지</strong>를 써야 한다는 것도 알게 되었습니다.
        그때 문득, <strong>제주에는 이미 풍력·태양광이 많이 설치되어 있다</strong>는 사실이 떠올랐습니다.
        뉴스에서는 가끔 ‘제주, 재생에너지가 너무 많아 발전을 줄였다’는 말도 들었습니다.
        그래서 직접 데이터를 열어 보고, 날씨와 발전량의 관계를 확인해 보고 싶었습니다.
      </p>

      <h3>(2) 탐구 목적</h3>
      <ul>
        <li>제주에서 태양광·풍력이 실제로 얼마나 만들어지는지 확인한다.</li>
        <li>바람·햇빛(일조) 같은 날씨가 발전량과 어떤 관계인지 데이터로 본다.</li>
        <li>태양광과 풍력 중 언제, 어느 쪽이 더 많이 나오는지 비교한다.</li>
        <li>발전량이 지나치게 많아질 때 생길 수 있는 문제(출력제어)를 생각해 본다.</li>
      </ul>

      <h3>(3) 사용한 자료</h3>
      <p>
        <strong>{S['start']}</strong>부터 <strong>{S['end']}</strong>까지, 하루 단위로 맞춘 데이터입니다.
        기상청 자료(기온, 풍속, 일조·일사)와 제주에너지공사 태양광·풍력 발전량을 합쳤습니다.
        총 <strong>{S['days']}일</strong> 분량이며, 아래 숫자는 이 기간을 기준으로 계산했습니다.
      </p>
      <div class="kpi">
        <span>태양광 합계 {S['solar_sum']:,.0f} kWh</span>
        <span>풍력 합계 {S['wind_sum']:,.0f} kWh</span>
        <span>재생에너지 합계 {S['total']:,.0f} kWh</span>
      </div>
      <p class="note">
        ※ 태양광·풍력·기상 데이터를 모두 하루 단위로 맞춰 두었으며,
        2025년 4~6월 태양광 자료도 제주에너지공사 공공데이터를 추가해 채웠습니다.
        일사량(solar_radiation)만 일부 날짜에서 비어 있을 수 있습니다.
      </p>
    </div>
    """


def body1_html() -> str:
    return f"""
    <div class="report-wrap">
      <h2>2. 본론 (1) — 제주에는 재생에너지가 얼마나 있을까?</h2>

      <p>
        먼저 ‘제주에서 재생에너지가 실제로 얼마나 나오는가’를 봅니다.
        아래 <strong>그림 1</strong>은 매일의 태양광 발전량(보라)과 풍력 발전량(하늘색)을 시간 순서대로 그린 것입니다.
      </p>
      <p>
        전체 기간을 합치면 태양광이 약 <strong>{S['solar_pct']:.1f}%</strong>,
        풍력이 약 <strong>{S['wind_pct']:.1f}%</strong>를 차지합니다.
        즉, 제주의 재생에너지는 <strong>한쪽만 크게 치우친 것이 아니라, 태양광과 풍력이 함께</strong> 만들어지고 있습니다.
      </p>
      <p>
        그래프를 자세히 보면 <strong>풍력은 날마다 위아래로 크게 출렁이고</strong>,
        태양광은 상대적으로 완만하게 움직입니다.
        이는 풍력이 ‘바람이 부는 날’에, 태양광이 ‘햇빛이 잘 드는 날’에 영향을 받기 때문일 것이라고 예상할 수 있습니다.
        다음 절에서 그 관계를 숫자로 확인합니다.
      </p>
    </div>
    """


def body2_html() -> str:
    r_w = S["r_wind"]
    r_s = S["r_sun"]
    wind_desc = (
        f"풍속과 풍력 발전량의 상관계수는 약 <strong>{r_w:.2f}</strong>입니다. "
        "바람이 세질수록 발전량이 늘어나는 경향이 데이터에서도 보입니다."
        if r_w is not None else "풍속·풍력 데이터가 부족해 상관관계를 계산하지 못했습니다."
    )
    sun_desc = (
        f"일조시간과 태양광 발전량의 상관계수는 약 <strong>{r_s:.2f}</strong>입니다. "
        "햇빛이 길수록 태양광 발전량도 커지는 경향이 나타납니다."
        if r_s is not None else "일조·태양광 데이터가 부족해 상관관계를 계산하지 못했습니다."
    )
    return f"""
    <div class="report-wrap">
      <h2>3. 본론 (2) — 날씨에 따라 발전량도 달라질까?</h2>

      <p>
        우리는 일상에서 “바람이 많이 불면 풍력이 잘 나오고, 해가 잘 드는 날에는 태양광이 잘 나온다”고 말합니다.
        이 직관이 제주 데이터에서도 맞는지 <strong>산점도</strong>로 확인했습니다.
        가로축은 날씨(풍속 또는 일조시간), 세로축은 그날의 발전량입니다.
        점들이 <strong>오른쪽 위로 모일수록</strong> ‘날씨가 좋을수록 발전량도 많다’는 뜻입니다.
      </p>

      <h3>풍력과 바람</h3>
      <p>{wind_desc}</p>
      <p>
        다만 점이 한 줄로 딱 맞게 늘어서지는 않습니다.
        터빈 점검, 고장, 계절별 풍향 차이, 출력제어 등
        <strong>날씨 말고도 발전량에 영향을 주는 요인</strong>이 있기 때문입니다.
      </p>

      <h3>태양광과 햇빛</h3>
      <p>{sun_desc}</p>
      <p>
        태양광도 마찬가지로, 구름·먼지·패널 온도·설비 상태에 따라 같은 일조 시간이라도 발전량이 달라질 수 있습니다.
        그래도 전체적인 경향만 보면, <strong>햇빛이 긴 날일수록 태양광 발전량이 커지는 패턴</strong>을 확인할 수 있습니다.
      </p>
      <p class="lead">
        이 탐구를 통해 “재생에너지는 날씨에 크게 의존한다”는 말이 단순한 상식이 아니라,
        <strong>실제 제주 데이터에서도 확인되는 사실</strong>임을 알 수 있었습니다.
      </p>
    </div>
    """


def body3_html() -> str:
    return f"""
    <div class="report-wrap">
      <h2>4. 본론 (3) — 태양광과 풍력, 언제 무엇이 더 많을까?</h2>

      <p>
        재생에너지라고 해서 항상 같은 방식으로 나오지는 않습니다.
        <strong>그림 4</strong>는 같은 날 태양광과 풍력 발전량을 비교해,
        어느 쪽이 더 많았는지를 세어 본 결과입니다.
      </p>
      <p>
        비교 가능한 <strong>{S['compare_days']}일</strong> 가운데,
        태양광이 더 많았던 날은 <strong>{S['solar_win']}일</strong>,
        풍력이 더 많았던 날은 <strong>{S['wind_win']}일</strong>입니다.
      </p>
      <p>
        이 말은 제주에서 재생에너지를 운영할 때
        <strong>태양광만, 또는 풍력만 믿을 수는 없다</strong>는 뜻이기도 합니다.
        바람이 강한 날에는 풍력이, 햇빛이 좋은 날에는 태양광이 각각 역할을 합니다.
        두 에너지원이 서로 다른 날씨 조건에서 힘을 쓰기 때문에,
        함께 있을 때 전체 재생에너지 공급이 더 안정적일 수 있습니다.
      </p>

      <h2>5. 본론 (4) — 재생에너지가 너무 많으면 어떤 일이 생길까?</h2>

      <p>
        그렇다면 재생에너지는 <strong>많을수록 무조건 좋을까?</strong>
        꼭 그렇지는 않습니다.
        전기는 쓰는 만큼(수요) 맞춰 공급되어야 하는데,
        바람이 세고 해가 잘 드는 날에는 태양광과 풍력이 <strong>한꺼번에 많이</strong> 나올 수 있습니다.
      </p>
      <p>
        이때 전력 수요보다 공급이 더 커지면, 발전소의 출력을 일부러 줄여야 할 수 있습니다.
        제주에서는 이런 상황을 <strong>출력제어</strong>라고 부릅니다.
        즉, ‘에너지를 아깝게 버린다’기보다,
        <strong>전력망이 감당할 수 있는 범위를 넘지 않도록 조절하는 것</strong>입니다.
      </p>
      <p>
        이번 데이터에서 재생에너지 합계(태양광+풍력)가 특히 높았던 날 — 상위 10%에 해당하는 날 — 은
        약 <strong>{S['high_days']}일</strong>이며,
        그때 하루 발전량은 대략 <strong>{S['thr']:,.0f} kWh 이상</strong>이었습니다.
        출력제어 기록은 아직 이 대시보드에 연결하지 않았지만,
        앞으로는 ‘고발전일’과 ‘출력제어가 발생한 날’을 겹쳐 보면
        이 문제를 더 분명하게 설명할 수 있을 것입니다.
      </p>
    </div>
    """


def conclusion_html() -> str:
    return f"""
    <div class="report-wrap">
      <h2>6. 결론 — 탐구를 마치며</h2>

      <h3>(1) 탐구 결론</h3>
      <ul>
        <li>제주에서는 태양광과 풍력이 모두 꾸준히 생산되며, 둘 다 재생에너지의 중요한 축이다.</li>
        <li>바람이 세면 풍력이, 일조가 길면 태양광이 늘어나는 경향이 데이터에서도 확인된다.</li>
        <li>날마다 태양광·풍력 중 어느 쪽이 우세한지 달라지므로, 두 에너지원은 서로 보완 관계에 가깝다.</li>
        <li>발전량이 지나치게 많아지는 날이 존재하며, 이때 출력제어 같은 운영 문제가 생길 수 있다.</li>
      </ul>

      <h3>(2) 느낀 점</h3>
      <p>
        첫 번째 탐구에서 ‘탄소를 줄여야 한다’는 것을 배웠다면,
        이번 탐구에서는 <strong>재생에너지가 실제로 어떻게 작동하는지</strong>를 조금 더 가까이에서 볼 수 있었습니다.
        재생에너지는 날씨에 따라 움직이고, 그래서 예측이 중요하며,
        많다고 해서 끝이 아니라 <strong>전력 시스템 전체와 함께</strong> 생각해야 한다는 점이 인상 깊었습니다.
      </p>

      <h3>(3) 향후 과제</h3>
      <ul>
        <li>출력제어(발전 제한) 데이터를 추가해, 고발전일과 실제 제어 발생을 비교한다.</li>
        <li>날씨를 이용해 다음날 발전량을 미리 예측하는 프로그램을 만들어 본다.</li>
        <li>첫 번째 기후 시뮬레이션과 연결해, ‘탄소 감축 → 재생에너지 확대 → 실제 운영’의 흐름을 하나의 이야기로 정리한다.</li>
      </ul>

      <p class="note" style="margin-top:2em;">
        자료 출처: 기상청 기상자료개방포털(기온·풍속·일조/일사),
        제주에너지공사 태양광·풍력 발전 정보(공공데이터포털) ·
        전처리 파일: 전처리완료.csv
      </p>
    </div>
    """


CUSTOM_CSS = f"""
.gradio-container, .main, .contain, body {{
  background: {BG} !important;
  color: {TEXT} !important;
  font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif !important;
}}
.gradio-container *, .markdown, .prose, .prose *, label, span, p {{
  color: {TEXT} !important;
}}
.gr-group, .gr-box, .block {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
footer {{ display: none !important; }}
"""


def build_app() -> gr.Blocks:
    with gr.Blocks(title="제주 재생에너지 탐구 보고서", css=CUSTOM_CSS, theme=gr.themes.Base()) as app:
        gr.HTML(intro_html())

        gr.HTML(body1_html())
        gr.Plot(chart_daily())

        gr.HTML(body2_html())
        with gr.Row():
            gr.Plot(chart_wind_scatter())
            gr.Plot(chart_solar_scatter())

        gr.HTML(body3_html())
        gr.Plot(chart_compare())

        gr.HTML(conclusion_html())
    return app


if __name__ == "__main__":
    app = build_app()
    app.launch(share=True)
