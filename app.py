# app.py
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Gapminder Dashboard", layout="wide")

# ---------- Colors: each one means the same thing on every chart ----------
# Red        = the focus country (bubbles, bars, KPI accent). Never used for anything else.
# Gray       = the world / global mean (reference lines on the bubbles, bar in the bar charts).
# Continents = their own hue, in the bubbles and in the bars.
FOCUS_RED = "#D7191C"
WORLD_GRAY = "#B0B0B0"
WORLD_GRAY_TEXT = "#7F7F7F"
continent_colors = {
    "Asia": "#1F78B4",       # strong blue
    "Europe": "#EDC948",     # gold
    "Africa": "#4CA64C",     # green
    "Americas": "#9B59B6",   # violet
    "Oceania": "#8C6D4F",    # brown
}

# Opacity has ONE meaning: faded = context, solid = the thing being read.
BG_OPACITY = 0.30

# ---------- Sizes (tweak these to fit your screen) ----------
BAR_H = 225                    # each of the two bar charts
GAP = 8                        # approx. gap between stacked charts
BUBBLE_H = 2 * BAR_H + GAP     # bubble chart spans exactly the two bars, so edges line up
LEFT_W, RIGHT_W = 1.35, 1      # bubble chart gets more width: it is the main chart

# ---------- Styling ----------
st.markdown(
    f"""
    <style>
    .block-container {{padding-top: 2.2rem; padding-bottom: 0.5rem;}}
    div[data-testid="stVerticalBlock"] {{gap: 0.4rem;}}
    .hdr {{display: flex; align-items: baseline; gap: 0.8rem; margin-bottom: 0.2rem;}}
    .hdr .ttl {{font-size: 1.15rem; font-weight: 600;}}
    .hdr .chip {{font-size: 0.75rem; padding: 0.05rem 0.5rem; border-radius: 10px;
                 background: rgba(128,128,128,0.18);}}
    .kpi {{border: 1px solid rgba(128,128,128,0.35); border-left: 5px solid {FOCUS_RED};
           border-radius: 6px; padding: 0.4rem 0.8rem; height: 128px; box-sizing: border-box;}}
    .kpi .lbl {{font-size: 0.75rem; opacity: 0.75;}}
    .kpi .val {{font-size: 1.5rem; font-weight: 600; line-height: 1.2;}}
    .kpi .sub {{font-size: 0.78rem; opacity: 0.8; line-height: 1.3;}}
    .kpi.headline .val {{font-size: 3.4rem; font-weight: 800; line-height: 1.05;}}
    </style>
    """,
    unsafe_allow_html=True,
)

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

# ---------- Data ----------
filtered = df[df["continent"].isin(continents)]
year_df = df[df["year"] == snapshot_year]
continent_year_df = year_df[year_df["continent"] == focus_continent]

def country_value(country, year, column):
    s = df.loc[(df["country"] == country) & (df["year"] == year), column]
    return s.iloc[0] if not s.empty else None

def fmt(value, decimals=0, prefix=""):
    return "N/A" if value is None else f"{prefix}{value:,.{decimals}f}"

def fmt_pop(value):
    if value is None:
        return "N/A"
    return f"{value / 1e6:,.1f}M" if value >= 1e6 else f"{value:,.0f}"

def rank_text(column):
    """Rank of the focus country within its continent for the snapshot year (1 = highest)."""
    value = country_value(focus, snapshot_year, column)
    if value is None:
        return "N/A"
    rank = int((continent_year_df[column] > value).sum()) + 1
    return f"#{rank} of {len(continent_year_df)} in {focus_continent}"

def kpi_card(label, value, subs, headline=False):
    cls = "kpi headline" if headline else "kpi"
    sub_html = "".join(f'<div class="sub">{s}</div>' for s in subs)
    return (f'<div class="{cls}"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div>{sub_html}</div>')

# ---------- Header (year stated once) ----------
st.markdown(
    f'<div class="hdr"><span class="ttl">{focus}\'s Gapminder Dashboard</span>'
    f'<span class="chip">Snapshot year: {snapshot_year}</span></div>',
    unsafe_allow_html=True,
)

# ---------- KPIs: headline is the biggest thing on screen ----------
le = country_value(focus, snapshot_year, "lifeExp")
continent_le_mean = continent_year_df["lifeExp"].mean()
head_subs = [rank_text("lifeExp")]
if le is not None:
    # Neutral gray text on purpose: no green/red deltas, so red stays "focus country"
    head_subs.append(f"{le - continent_le_mean:+.1f} yrs vs {focus_continent} mean")

kpi_left, kpi_right = st.columns([LEFT_W, RIGHT_W])
kpi_left.markdown(
    kpi_card("Life expectancy (years)", fmt(le, 1), head_subs, headline=True),
    unsafe_allow_html=True,
)
gdp_col, pop_col = kpi_right.columns(2)
gdp_col.markdown(
    kpi_card("GDP per capita",
             fmt(country_value(focus, snapshot_year, "gdpPercap"), 0, "$"),
             [rank_text("gdpPercap")]),
    unsafe_allow_html=True,
)
pop_col.markdown(
    kpi_card("Population",
             fmt_pop(country_value(focus, snapshot_year, "pop")),
             [rank_text("pop")]),
    unsafe_allow_html=True,
)

# ---------- Bubble chart ----------
data_year = filtered[filtered["year"] == snapshot_year]
focus_df = df[df["country"] == focus].sort_values("year")

# Fixed scale so bubble sizes don't change when filters change
sizeref = 2.0 * df["pop"].max() / (100 ** 2)

# Fixed axis ranges so the chart doesn't jump around when the filters change
X_MIN, X_MAX = 200, 130000
Y_MIN, Y_MAX = 20, 85

fig = go.Figure()

# World reference lines (gray = world, same as the gray bars)
world_le = year_df["lifeExp"].mean()
world_gdp = year_df["gdpPercap"].mean()
fig.add_trace(go.Scatter(
    x=[X_MIN, X_MAX], y=[world_le, world_le],
    mode="lines+text", text=["", "World mean"], textposition="top left",
    textfont=dict(size=10, color=WORLD_GRAY_TEXT), cliponaxis=False,
    line=dict(color=WORLD_GRAY, width=1, dash="dot"),
    hoverinfo="skip", showlegend=False,
))
fig.add_trace(go.Scatter(
    x=[world_gdp, world_gdp], y=[Y_MIN, Y_MAX],
    mode="lines+text", text=["World mean", ""], textposition="top right",
    textfont=dict(size=10, color=WORLD_GRAY_TEXT), cliponaxis=False,
    line=dict(color=WORLD_GRAY, width=1, dash="dot"),
    hoverinfo="skip", showlegend=False,
))

# Continent bubbles (faded = context). Legend lists only the selected continents.
for continent, color in continent_colors.items():
    cdf = data_year[data_year["continent"] == continent]
    fig.add_trace(go.Scatter(
        x=cdf["gdpPercap"],
        y=cdf["lifeExp"],
        mode="markers",
        name=continent,
        showlegend=continent in continents,
        marker=dict(size=cdf["pop"], sizemode="area", sizeref=sizeref,
                    sizemin=4, color=color, opacity=BG_OPACITY,
                    line=dict(width=0.5, color="white")),
        customdata=cdf[["country", "pop"]],
        hovertemplate=("<b>%{customdata[0]}</b><br>"
                       "GDP per capita: $%{x:,.0f}<br>"
                       "Life expectancy: %{y:.1f}<br>"
                       "Population: %{customdata[1]:,.0f}<extra></extra>"),
    ))

# Focus country path: solid for the snapshot year, faded for the other years.
# Year labels on the first, last and snapshot points make the path read as time.
focus_opacity = [1.0 if y == snapshot_year else BG_OPACITY for y in focus_df["year"]]
label_years = {focus_df["year"].min(), focus_df["year"].max(), snapshot_year}
focus_text = [str(y) if y in label_years else "" for y in focus_df["year"]]

fig.add_trace(go.Scatter(
    x=focus_df["gdpPercap"],
    y=focus_df["lifeExp"],
    mode="lines+markers+text",
    name=focus,
    text=focus_text,
    textposition="top center",
    textfont=dict(size=10),
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

# Title compares to the selected continent, or "World" for anything but exactly one
comparison_label = continents[0] if len(continents) == 1 else "World"

fig.update_layout(
    title=dict(text=f"{focus}'s Development Over Time Compared to {comparison_label} ({snapshot_year})",
               font=dict(size=13)),
    xaxis_title="GDP per capita ($)",
    yaxis_title="Life expectancy (years)",
    template="plotly_white",
    legend=dict(x=0.02, y=0.98),
    height=BUBBLE_H,
    margin=dict(l=10, r=10, t=36, b=10),
    font=dict(size=11),
)

tick_vals = np.logspace(2, 5, 8)
fig.update_xaxes(
    type="log",
    range=[np.log10(X_MIN), np.log10(X_MAX)],
    tickmode="array",
    tickvals=tick_vals,
    ticktext=[f"${x:,.0f}" for x in tick_vals],
)
fig.update_yaxes(range=[Y_MIN, Y_MAX])

# Key for bubble size
fig.add_annotation(
    xref="paper", yref="paper", x=0.99, y=0.02, xanchor="right", yanchor="bottom",
    text="Bubble size = population", showarrow=False,
    font=dict(size=10, color=WORLD_GRAY_TEXT),
)

# ---------- Comparison bar charts ----------
# Always: focus country, its continent's mean, and the global mean.
# Plus: the mean of every other continent selected in the sidebar filter.
extra_continents = [c for c in continents if c != focus_continent]

def comparison_bar(column, metric_name, prefix="", decimals=1):
    # (label, value, color, is_focus)
    items = [
        (focus, country_value(focus, snapshot_year, column), FOCUS_RED, True),
        (f"{focus_continent} mean", continent_year_df[column].mean(),
         continent_colors[focus_continent], False),
        ("Global mean", year_df[column].mean(), WORLD_GRAY, False),
    ]
    for c in extra_continents:
        items.append((f"{c} mean",
                      year_df.loc[year_df["continent"] == c, column].mean(),
                      continent_colors[c], False))

    items = [i for i in items if i[1] is not None and not pd.isna(i[1])]
    items.sort(key=lambda t: t[1], reverse=True)   # highest to lowest

    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    colors = [i[2] for i in items]
    # Same outline treatment for the focus country as on the bubble chart
    line_colors = ["black" if i[3] else "white" for i in items]
    line_widths = [0.75 if i[3] else 0.5 for i in items]

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
        title=dict(text=metric_name, font=dict(size=13)),
        xaxis=dict(range=[0, max(values) * 1.2]),
        yaxis=dict(autorange="reversed"),   # first (highest) bar on top
        template="plotly_white",
        height=BAR_H,                        # fixed; more bars = thinner bars
        bargap=0.25,
        margin=dict(l=10, r=10, t=36, b=10),
        font=dict(size=11),
        showlegend=False,
    )
    return bar

le_bar = comparison_bar("lifeExp", "Life Expectancy (years)", decimals=1)
gdp_bar = comparison_bar("gdpPercap", "GDP per Capita ($)", prefix="$", decimals=0)

# ---------- Layout: cards group related charts; top and bottom edges line up ----------
left, right = st.columns([LEFT_W, RIGHT_W])
with left.container(border=True):
    st.plotly_chart(fig, width="stretch")
with right.container(border=True):
    st.plotly_chart(le_bar, width="stretch")
    st.plotly_chart(gdp_bar, width="stretch")