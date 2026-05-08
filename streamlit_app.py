"""Streamlit app: explore RSECon program classifications across years.

Run locally:
    uv run streamlit run streamlit_app.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st

CSV_PATH = Path("classifications.csv")
CLASSIFICATIONS_PATH = Path("CLASSIFICATIONS.md")

CATEGORY_ORDER = ["Software", "Research", "Community"]
CATEGORY_COLORS = {
    "Software": "#2E86AB",  # steel blue
    "Research": "#A23B72",  # deep magenta
    "Community": "#F18F01",  # warm amber
}

st.set_page_config(
    page_title="RSECon program classification",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------- styling --
st.markdown(
    """
    <style>
        /* Tighten the default top padding so the title sits closer to the top */
        .block-container { padding-top: 2.5rem; padding-bottom: 4rem; }
        h1, h2, h3 { font-family: "Iowan Old Style", Georgia, serif; letter-spacing: -0.01em; }
        h1 { font-weight: 700; }
        /* Sidebar accent */
        section[data-testid="stSidebar"] { border-right: 1px solid #E5DDD0; }
        /* Metric cards a bit warmer */
        div[data-testid="stMetric"] {
            background: #F4ECDD;
            border-radius: 6px;
            padding: 0.6rem 0.9rem;
        }
        /* Rule between sections */
        hr { border: none; border-top: 1px solid #E5DDD0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Use a clean plotly template for the warm-cream backdrop.
pio.templates["rsecon"] = pio.templates["simple_white"]
pio.templates["rsecon"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Georgia, serif", size=13, color="#2C2C2C"),
    title=dict(font=dict(size=16, color="#2C2C2C")),
    margin=dict(l=20, r=20, t=40, b=20),
)
pio.templates.default = "rsecon"


@st.cache_data
def load_data(mtime: float) -> pd.DataFrame:
    # mtime is part of the cache key so the cache invalidates whenever the CSV
    # is regenerated.
    del mtime
    df = pd.read_csv(CSV_PATH)
    df["year"] = df["year"].astype(int)
    df["submission_type"] = df["submission_type"].fillna("(none)")
    return df


if not CSV_PATH.exists():
    st.error(f"{CSV_PATH} not found. Run `uv run python build_csv.py` first.")
    st.stop()
df = load_data(CSV_PATH.stat().st_mtime)

# ============================================================== HEADER ====
st.title("RSECon program classification")
st.markdown(
    """
    A data view of the **Research Software Engineering Conference (RSECon)** programmes
    for **2023, 2024, and 2025**. Every accepted submission's abstract is read by an LLM
    (Claude Opus 4.7) and classified into one of three buckets — **Software**,
    **Research**, or **Community** — with a short written justification.

    The aim is to ask: *what kind of work is the RSE community presenting at its annual
    conference, and how is that mix changing year on year?* Use the sidebar to filter,
    the charts to compare years and session formats, and the table at the bottom to read
    the model's reasoning on individual submissions.
    """
)

# ============================================== CLASSIFICATION SCHEME ====
st.subheader("How submissions are classified")
st.markdown(
    "Below is how we defined the three categories for classification. The LLM was given these definitions as part of its prompt, and used them to classify each submission into one of the three buckets based on the submissions title and abstract."
)

if CLASSIFICATIONS_PATH.exists():
    scheme_text = CLASSIFICATIONS_PATH.read_text()
    # Hide the "Other" fallback item in the dashboard without touching the source file.
    scheme_text = (
        re.sub(
            r"\n*\d+\.\s*Other:.*?(?=\n\d+\.|\Z)",
            "",
            scheme_text,
            flags=re.DOTALL,
        ).rstrip()
        + "\n"
    )
    st.markdown(scheme_text)
else:
    st.info("CLASSIFICATIONS.md not found.")

st.markdown("---")

# ================================================= FILTERS (SIDEBAR) ====
with st.sidebar:
    st.header("Filters")
    years = st.multiselect(
        "Year", sorted(df["year"].unique()), default=sorted(df["year"].unique())
    )
    primaries = st.multiselect("Category", CATEGORY_ORDER, default=CATEGORY_ORDER)
    sub_types = sorted(df["submission_type"].unique())
    types = st.multiselect("Submission type", sub_types, default=sub_types)

mask = (
    df["year"].isin(years)
    & df["primary_category"].isin(primaries)
    & df["submission_type"].isin(types)
)
view = df[mask].copy()

# ================================================== HEADLINE METRICS ====
m1, m2, m3, m4 = st.columns(4)
m1.metric("Submissions", len(view))
m2.metric("Years", view["year"].nunique() if len(view) else 0)
m3.metric(
    "% Software",
    f"{(view['primary_category'] == 'Software').mean() * 100:.0f}%"
    if len(view)
    else "—",
)
m4.metric(
    "% Research",
    f"{(view['primary_category'] == 'Research').mean() * 100:.0f}%"
    if len(view)
    else "—",
)

if not len(view):
    st.warning("No submissions match the current filters.")
    st.stop()

# ============================================== CHART: BY YEAR =========
st.subheader("Category by year")
counts = view.groupby(["year", "primary_category"]).size().reset_index(name="count")
fig = px.bar(
    counts,
    x="year",
    y="count",
    color="primary_category",
    category_orders={"primary_category": CATEGORY_ORDER},
    color_discrete_map=CATEGORY_COLORS,
    barmode="group",
    text="count",
)
fig.update_traces(textposition="outside")
fig.update_layout(xaxis=dict(tickmode="linear"), bargap=0.25, legend_title_text="")
st.plotly_chart(fig, use_container_width=True)

# ===================================== CHART: BY SUBMISSION TYPE ========
st.subheader("Category by submission type")
type_counts = (
    view.groupby(["submission_type", "primary_category"])
    .size()
    .reset_index(name="count")
)
type_order = view["submission_type"].value_counts().index.tolist()
fig2 = px.bar(
    type_counts,
    x="submission_type",
    y="count",
    color="primary_category",
    category_orders={
        "primary_category": CATEGORY_ORDER,
        "submission_type": type_order,
    },
    color_discrete_map=CATEGORY_COLORS,
    barmode="stack",
)
fig2.update_layout(xaxis_tickangle=-25, legend_title_text="", xaxis_title="")
st.plotly_chart(fig2, use_container_width=True)

# ========================================= EXPLORE TABLE ================
st.subheader("Explore individual submissions")
search = st.text_input(
    "Search title, reasoning, or abstract",
    placeholder="e.g. 'plasma', 'training', 'JAX'",
)
table = view
if search:
    s = search.lower()
    table = view[
        view["title"].str.lower().str.contains(s, na=False)
        | view["reasoning"].str.lower().str.contains(s, na=False)
        | view["abstract"].str.lower().str.contains(s, na=False)
    ]

st.caption(f"{len(table)} matching submissions")

st.dataframe(
    table[
        [
            "year",
            "submission_type",
            "primary_category",
            "title",
            "reasoning",
        ]
    ]
    .rename(columns={"primary_category": "category"})
    .reset_index(drop=True),
    use_container_width=True,
    hide_index=False,
    height=500,
)
