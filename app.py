# app.py
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="My Dashboard", layout="wide")

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

years = sorted(df["year"].unique())
snapshot_year = st.sidebar.selectbox("Snapshot year", years, index=len(years) - 1)

#continents = st.sidebar.multiselect(
#    "Continent", df["continent"].unique(), default=list(df["continent"].unique())
#)

min_year, max_year = int(df["year"].min()), int(df["year"].max())
#year_range = st.sidebar.slider("Year range (bar chart)", min_year, max_year, (min_year, max_year))

min_val, max_val = float(df["lifeExp"].min()), float(df["lifeExp"].max())
#value_range = st.sidebar.slider("Life expectancy", min_val, max_val, (min_val, max_val))

# ---------- Filtered data (for the bubble background and bar chart) ----------
#mask = (
#    df["continent"].isin(continents)
#    & df["year"].between(*year_range)
#)
filtered = df

# ---------- Helpers ----------
def country_value(country, year, column):
    s = df.loc[(df["country"] == country) & (df["year"] == year), column]
    return s.iloc[0] if not s.empty else None

def fmt(value, decimals=0, prefix=""):
    return "N/A" if value is None else f"{prefix}{value:,.{decimals}f}"

# ---------- KPIs (use the focus country, ignoring the other filters) ----------
st.title("My Dashboard")
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"{focus} Life Expectancy, {snapshot_year}",
          fmt(country_value(focus, snapshot_year, "lifeExp"), 1))
c2.metric(f"Global Mean Life Expectancy, {snapshot_year}",
          fmt(df.loc[df["year"] == snapshot_year, "lifeExp"].mean(), 1))
c3.metric(f"{focus} Population, {snapshot_year}",
          fmt(country_value(focus, snapshot_year, "pop")))
c4.metric(f"{focus} GDP per Capita, {snapshot_year}",
          fmt(country_value(focus, snapshot_year, "gdpPercap"), 0, "$"))

# ---------- Bubble chart ----------
data_year = filtered[filtered["year"] == snapshot_year]
focus_df = df[df["country"] == focus].sort_values("year")

continent_colors = {
    "Asia": "#4C78A8",
    "Europe": "#F2CF5B",
    "Africa": "#E45756",
    "Americas": "#72B7B2",
    "Oceania": "#B279A2",
}

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
                    sizemin=4, color=color, opacity=0.30,
                    line=dict(width=0.5, color="white")),
        customdata=cdf[["country", "pop"]],
        hovertemplate=("<b>%{customdata[0]}</b><br>"
                       "GDP per capita: $%{x:,.0f}<br>"
                       "Life expectancy: %{y:.1f}<br>"
                       "Population: %{customdata[1]:,.0f}<extra></extra>"),
    ))

# Focus country's historical path
fig.add_trace(go.Scatter(
    x=focus_df["gdpPercap"],
    y=focus_df["lifeExp"],
    mode="lines+markers",
    name=focus,
    line=dict(color="black", width=1.5),
    marker=dict(size=focus_df["pop"], sizemode="area", sizeref=sizeref,
                sizemin=4, color="#FF00BF", opacity=1,
                line=dict(width=0.5, color="white")),
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

# ---------- Layout ----------
left, right = st.columns(2)
left.plotly_chart(fig, use_container_width=True)

bar_df = filtered.groupby("continent", as_index=False)["lifeExp"].mean()
bar_fig = px.bar(bar_df, x="continent", y="lifeExp",
                 title="Mean Life Expectancy by Continent (filtered years)")
right.plotly_chart(bar_fig, use_container_width=True)