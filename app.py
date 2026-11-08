# app.py
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Gapminder Dashboard", layout="wide")

# ---------- Colors ----------
# Red is reserved for the focus country. The continent colors avoid red hues
# and are spread across blue, gold, green, violet and brown so they stay distinct.
FOCUS_RED = "#D7191C"
GLOBAL_GRAY = "#7F7F7F"
continent_colors = {
    "Asia": "#1F78B4",       # strong blue
    "Europe": "#EDC948",     # gold
    "Africa": "#4CA64C",     # green
    "Americas": "#9B59B6",   # violet
    "Oceania": "#8C6D4F",    # brown
}
CONTINENT_OPACITY = 1.0        # continent bubbles and bars are fully solid
FOCUS_OTHER_YEAR_OPACITY = 0.30   # the focus country's non-snapshot years stay faded

# ---------- Compact styling ----------
st.markdown(
    """
    <style>
    .block-container {padding-top: 2.5rem; padding-bottom: 0.5rem;}
    div[data-testid="stVerticalBlock"] {gap: 0.4rem;}
    h3 {padding: 0; margin: 0;}

    /* Value KPIs: bold red values, bold titles */
    [data-testid="stMetricValue"] {font-size: 1.5rem; font-weight: 700;}
    [data-testid="stMetricLabel"] p {font-size: 1.05rem;}   /* all KPI titles = rank value size */
    .st-key-value_row [data-testid="stMetricValue"],
    .st-key-value_row [data-testid="stMetricValue"] * {color: #D7191C !important;}
    .st-key-value_row [data-testid="stMetricLabel"],
    .st-key-value_row [data-testid="stMetricLabel"] * {font-weight: 700 !important; color: #000 !important;}

    /* Rank KPIs: smaller than the value KPIs */
    .st-key-rank_row [data-testid="stMetricValue"] {font-size: 1.05rem; font-weight: 400;}
    .st-key-rank_row [data-testid="stMetricLabel"] p {font-size: 1.05rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Tweak these two numbers to make the charts taller or shorter
BUBBLE_H = 470
BAR_H = 230          # fixed: extra bars get thinner instead of the chart growing

@st.cache_data
def load_data():
    df = pd.read_csv("gapminder_data.tsv", sep="\t")
    df["year"] = df["year"].astype(int)
    return df

df = load_data()

# ---------- Sidebar ----------
st.sidebar.header("Filters")

country_list = sorted(df["country"].unique())
default_idx = country_list.index("Peru") if "Peru" in country_list else 0
focus = st.sidebar.selectbox("Focus country", country_list, index=default_idx)
focus_continent = df.loc[df["country"] == focus, "continent"].iloc[0]

years = sorted(df["year"].unique())
snapshot_year = st.sidebar.selectbox("Snapshot year", years, index=len(years) - 1)

# The key includes the focus country, so the default resets to that
# country's continent whenever a new focus country is picked.
continents = st.sidebar.multiselect(
    "Continent (bubble chart and bar charts)",
    options=list(df["continent"].unique()),
    default=[focus_continent],
    key=f"continents_{focus}",
)

# ---------- Filtered data (bubble chart background) ----------
filtered = df[df["continent"].isin(continents)]

# ---------- Helpers ----------
year_df = df[df["year"] == snapshot_year]
continent_year_df = year_df[year_df["continent"] == focus_continent]

def country_value(country, year, column):
    s = df.loc[(df["country"] == country) & (df["year"] == year), column]
    return s.iloc[0] if not s.empty else None

def fmt(value, decimals=0, prefix=""):
    return "N/A" if value is None else f"{prefix}{value:,.{decimals}f}"

def rank_text(column):
    """Rank of the focus country within its continent for the snapshot year (1 = highest)."""
    value = country_value(focus, snapshot_year, column)
    if value is None:
        return "N/A"
    rank = int((continent_year_df[column] > value).sum()) + 1
    return f"#{rank} of {len(continent_year_df)}"

# ---------- Title and KPIs ----------
st.markdown(
    f"### <span style='color:{FOCUS_RED}'>{focus}'s</span> Gapminder Dashboard, {snapshot_year}",
    unsafe_allow_html=True
)

# Row 1: numeric KPIs (bold)
with st.container(key="value_row"):
    n1, n2, n3 = st.columns(3)
    n1.metric(f"Life Expectancy",
              fmt(country_value(focus, snapshot_year, "lifeExp"), 1))
    n2.metric(f"GDP per Capita",
              fmt(country_value(focus, snapshot_year, "gdpPercap"), 0, "$"))
    n3.metric(f"Population",
              fmt(country_value(focus, snapshot_year, "pop")))

# Row 2: rank KPIs (smaller), directly beneath their numeric KPIs
with st.container(key="rank_row"):
    r1, r2, r3 = st.columns(3)
    r1.metric(f"Life Expectancy Rank in {focus_continent}", rank_text("lifeExp"))
    r2.metric(f"GDP per Capita Rank in {focus_continent}", rank_text("gdpPercap"))
    r3.metric(f"Population Rank in {focus_continent}", rank_text("pop"))

# ---------- Bubble chart ----------
data_year = filtered[filtered["year"] == snapshot_year]
focus_df = df[df["country"] == focus].sort_values("year")

# Fixed scale so bubble sizes don't change when filters change
sizeref = 2.0 * df["pop"].max() / (100 ** 2)

fig = go.Figure()

for continent, color in continent_colors.items():
    cdf = data_year[data_year["continent"] == continent]
    fig.add_trace(go.Scatter(
        x=cdf["gdpPercap"],
        y=cdf["lifeExp"],
        mode="markers",
        name=continent,
        marker=dict(size=cdf["pop"], sizemode="area", sizeref=sizeref,
                    sizemin=4, color=color, opacity=CONTINENT_OPACITY,
                    line=dict(width=0.5, color="white")),
        customdata=cdf[["country", "pop"]],
        hovertemplate=("<b>%{customdata[0]}</b><br>"
                       "GDP per capita: $%{x:,.0f}<br>"
                       "Life expectancy: %{y:.1f}<br>"
                       "Population: %{customdata[1]:,.0f}<extra></extra>"),
    ))

# Focus country: full opacity for the snapshot year, same as the others otherwise
focus_opacity = [1.0 if y == snapshot_year else FOCUS_OTHER_YEAR_OPACITY for y in focus_df["year"]]

fig.add_trace(go.Scatter(
    x=focus_df["gdpPercap"],
    y=focus_df["lifeExp"],
    mode="lines+markers",
    name=focus,
    showlegend=False,   # the legend entry comes from the solid proxy trace below
    line=dict(color="black", width=0.75),
    marker=dict(size=focus_df["pop"], sizemode="area", sizeref=sizeref,
                sizemin=4, color=FOCUS_RED, opacity=focus_opacity,
                line=dict(width=0.75, color="black")),
    customdata=focus_df[["year", "pop"]],
    hovertemplate=(f"<b>{focus}</b><br>"
                   "Year: %{customdata[0]}<br>"
                   "GDP per capita: $%{x:,.0f}<br>"
                   "Life expectancy: %{y:.1f}<br>"
                   "Population: %{customdata[1]:,.0f}<extra></extra>"),
))

# Legend-only entry: shows the selected country at full opacity
fig.add_trace(go.Scatter(
    x=[None], y=[None],
    mode="lines+markers",
    name=focus,
    line=dict(color="black", width=0.75),
    marker=dict(size=10, color=FOCUS_RED, opacity=1,
                line=dict(width=0.75, color="black")),
    hoverinfo="skip",
    showlegend=True,
))

# Title compares to the selected continent, or "World" for anything but exactly one
comparison_label = continents[0] if len(continents) == 1 else "World"

fig.update_layout(
    # Axis titles live in the subtitle instead of beside the axes
    title=dict(text=f"{focus}'s Development From 1952 to 2007 Compared to {comparison_label}",
               font=dict(size=14),
               subtitle=dict(text=f"GDP per Capita ($) Versus Life Expectancy (years) in {snapshot_year} with Bubble Sized by Population",
                             font=dict(size=12, color="#555555"))),
    template="plotly_white",
    legend=dict(x=0.02, y=0.98),
    height=BUBBLE_H,
    margin=dict(l=10, r=10, t=60, b=10),
    font=dict(size=11),
)

tick_vals = np.logspace(2, 5, 8)
fig.update_xaxes(
    type="log",
    tickmode="array",
    tickvals=tick_vals,
    ticktext=[f"${x:,.0f}" for x in tick_vals],
)

# ---------- Comparison bar charts ----------
# Always: focus country, its continent's mean, and the global mean.
# Plus: the mean of every other continent selected in the sidebar filter.
extra_continents = [c for c in continents if c != focus_continent]

def comparison_bar(column, metric_name, prefix="", decimals=1):
    # (label, value, solid color, is_continent, is_focus)
    items = [
        (focus, country_value(focus, snapshot_year, column), FOCUS_RED, False, True),
        (f"{focus_continent} mean", continent_year_df[column].mean(),
         continent_colors[focus_continent], True, False),
        ("Global mean", year_df[column].mean(), GLOBAL_GRAY, False, False),
    ]
    for c in extra_continents:
        items.append((f"{c} mean",
                      year_df.loc[year_df["continent"] == c, column].mean(),
                      continent_colors[c], True, False))

    items = [i for i in items if i[1] is not None and not pd.isna(i[1])]
    items.sort(key=lambda t: t[1], reverse=True)   # highest to lowest

    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    colors = [i[2] for i in items]   # solid colors, no fading
    # Black outline around the selected country's bar only
    line_colors = ["black" if i[4] else "white" for i in items]
    line_widths = [0.75 if i[4] else 0.5 for i in items]

    if extra_continents:
        title = f"{metric_name}: {focus} vs. Continents vs. World"
    else:
        title = f"{metric_name}: {focus} vs. {focus_continent} vs. World"

    bar = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color=colors, line=dict(color=line_colors, width=line_widths)),
        text=[f"{prefix}{v:,.{decimals}f}" for v in values],
        textposition="outside",
        hovertemplate=f"<b>%{{y}}</b><br>{metric_name}: {prefix}%{{x:,.{decimals}f}}<extra></extra>",
    ))
    bar.update_layout(
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(range=[0, max(values) * 1.2]),
        yaxis=dict(autorange="reversed"),   # first (highest) bar on top
        template="plotly_white",
        height=BAR_H,                        # fixed; more bars = thinner bars
        bargap=0.25,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(size=11),
        showlegend=False,
    )
    return bar

le_bar = comparison_bar("lifeExp", "Life Expectancy (years)", decimals=1)
gdp_bar = comparison_bar("gdpPercap", "GDP per Capita ($)", prefix="$", decimals=0)

# ---------- Layout ----------
left, right = st.columns(2)
left.plotly_chart(fig, width="stretch")
right.plotly_chart(le_bar, width="stretch")
right.plotly_chart(gdp_bar, width="stretch")