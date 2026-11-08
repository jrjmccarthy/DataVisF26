# app.py
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="My Dashboard", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("gapminder_data.tsv", sep="\t")
    df["year"] = df["year"].astype(int)
    return df

df = load_data()

PINK = "#FF00BF"
GLOBAL_GRAY = "#7F7F7F"
continent_colors = {
    "Asia": "#4C78A8",
    "Europe": "#F2CF5B",
    "Africa": "#E45756",
    "Americas": "#72B7B2",
    "Oceania": "#B279A2",
}

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
    "Continent (bubble chart)",
    options=list(df["continent"].unique()),
    default=[focus_continent],
    key=f"continents_{focus}",
)

min_val, max_val = float(df["lifeExp"].min()), float(df["lifeExp"].max())
value_range = st.sidebar.slider("Life expectancy (bubble chart)",
                                min_val, max_val, (min_val, max_val))

# ---------- Filtered data (bubble chart background) ----------
mask = (
    df["continent"].isin(continents)
    & df["lifeExp"].between(*value_range)
)
filtered = df[mask]

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

# ---------- KPIs ----------
st.title("My Dashboard")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"{focus} Life Expectancy, {snapshot_year}",
          fmt(country_value(focus, snapshot_year, "lifeExp"), 1))
c2.metric(f"Life Exp. Rank in {focus_continent}, {snapshot_year}",
          rank_text("lifeExp"))
c3.metric(f"{focus} GDP per Capita, {snapshot_year}",
          fmt(country_value(focus, snapshot_year, "gdpPercap"), 0, "$"))
c4.metric(f"GDP per Capita Rank in {focus_continent}, {snapshot_year}",
          rank_text("gdpPercap"))
c5.metric(f"{focus} Population, {snapshot_year}",
          fmt(country_value(focus, snapshot_year, "pop")))

# ---------- Bubble chart ----------
data_year = filtered[filtered["year"] == snapshot_year]
focus_df = df[df["country"] == focus].sort_values("year")

# Fixed scale so bubble sizes don't change when filters change
sizeref = 2.0 * df["pop"].max() / (100 ** 2)
BG_OPACITY = 0.30

fig = go.Figure()

for continent, color in continent_colors.items():
    cdf = data_year[data_year["continent"] == continent]
    fig.add_trace(go.Scatter(
        x=cdf["gdpPercap"],
        y=cdf["lifeExp"],
        mode="markers",
        name=continent,
        marker=dict(size=cdf["pop"], sizemode="area", sizeref=sizeref,
                    sizemin=4, color=color, opacity=BG_OPACITY,
                    line=dict(width=0.5, color="white")),
        customdata=cdf[["country", "pop"]],
        hovertemplate=("<b>%{customdata[0]}</b><br>"
                       "GDP per capita: $%{x:,.0f}<br>"
                       "Life expectancy: %{y:.1f}<br>"
                       "Population: %{customdata[1]:,.0f}<extra></extra>"),
    ))

# Focus country: full opacity for the snapshot year, same as the others otherwise
focus_opacity = [1.0 if y == snapshot_year else BG_OPACITY for y in focus_df["year"]]

fig.add_trace(go.Scatter(
    x=focus_df["gdpPercap"],
    y=focus_df["lifeExp"],
    mode="lines+markers",
    name=focus,
    line=dict(color="black", width=0.75),
    marker=dict(size=focus_df["pop"], sizemode="area", sizeref=sizeref,
                sizemin=4, color=PINK, opacity=focus_opacity,
                line=dict(width=0.75, color="black")),
    customdata=focus_df[["year", "pop"]],
    hovertemplate=(f"<b>{focus}</b><br>"
                   "Year: %{customdata[0]}<br>"
                   "GDP per capita: $%{x:,.0f}<br>"
                   "Life expectancy: %{y:.1f}<br>"
                   "Population: %{customdata[1]:,.0f}<extra></extra>"),
))

fig.update_layout(
    title=f"{focus}'s Development Compared to the World ({snapshot_year})",
    xaxis_title="GDP per capita ($)",
    yaxis_title="Life Expectancy (years)",
    template="plotly_white",
    legend=dict(x=0.02, y=0.98),
    height=650,
)

tick_vals = np.logspace(2, 5, 8)
fig.update_xaxes(
    type="log",
    tickmode="array",
    tickvals=tick_vals,
    ticktext=[f"${x:,.0f}" for x in tick_vals],
)

# ---------- Comparison bar charts (country vs. continent mean vs. global mean) ----------
def comparison_bar(column, metric_name, prefix="", decimals=1):
    items = [
        (focus, country_value(focus, snapshot_year, column), PINK),
        (f"{focus_continent} mean", continent_year_df[column].mean(),
         continent_colors[focus_continent]),
        ("Global mean", year_df[column].mean(), GLOBAL_GRAY),
    ]
    items = [i for i in items if i[1] is not None]
    items.sort(key=lambda t: t[1], reverse=True)   # highest to lowest

    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    colors = [i[2] for i in items]

    bar = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{prefix}{v:,.{decimals}f}" for v in values],
        textposition="outside",
        hovertemplate=f"<b>%{{y}}</b><br>{metric_name}: {prefix}%{{x:,.{decimals}f}}<extra></extra>",
    ))
    bar.update_layout(
        title=f"{metric_name}: {focus} vs. {focus_continent} vs. World ({snapshot_year})",
        xaxis_title=metric_name,
        xaxis=dict(range=[0, max(values) * 1.2]),
        yaxis=dict(autorange="reversed"),   # first (highest) bar on top
        template="plotly_white",
        height=320,
        showlegend=False,
    )
    return bar

le_bar = comparison_bar("lifeExp", "Life Expectancy (years)", decimals=1)
gdp_bar = comparison_bar("gdpPercap", "GDP per Capita ($)", prefix="$", decimals=0)

# ---------- Layout ----------
left, right = st.columns(2)
left.plotly_chart(fig, use_container_width=True)
right.plotly_chart(le_bar, use_container_width=True)
right.plotly_chart(gdp_bar, use_container_width=True)