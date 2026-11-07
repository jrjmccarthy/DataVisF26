# app.py
import pandas as pd
import streamlit as st
import plotly
import plotly.express as px

st.set_page_config(page_title="My Dashboard", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv('gapminder_data.tsv', 
                        sep='\t')
    df["year"] = df["year"].astype(int)   # make sure it's a plain integer
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")
continents = st.sidebar.multiselect(
    "Continent", df["continent"].unique(), default=list(df["continent"].unique())
)

min_year, max_year = int(df["year"].min()), int(df["year"].max())
if min_year < max_year:
    year_range = st.sidebar.slider("Year", min_year, max_year, (min_year, max_year))
else:
    year_range = (min_year, max_year)   # slider errors if min == max

min_val, max_val = float(df["lifeExp"].min()), float(df["lifeExp"].max())
value_range = st.sidebar.slider("lifeExp", min_val, max_val, (min_val, max_val))

# Apply filters
mask = (
    df["continent"].isin(continents)
    & df["year"].between(*year_range)
    & df["lifeExp"].between(*value_range)
)
filtered = df[mask]

# Layout
st.title("My Dashboard")
c1, c2, c3 = st.columns(3)
c1.metric("Rows", f"{len(filtered):,}")
c2.metric("Global Mean Life Expectancy", f"{filtered['lifeExp'].mean():,.0f}")
c3.metric("Global Mean Life Expectancy, 2007", f"{filtered['lifeExp'][filtered['year'] == 2007].mean():,.1f}")

yearly = filtered.groupby(["year", "continent"], as_index=False)["lifeExp"].sum()
line_fig = px.line(yearly, x="year", y="lifeExp", color="continent", markers=True)
line_fig.update_xaxes(dtick=1)   # whole-number year ticks, no 2019.5

left, right = st.columns(2)
left.plotly_chart(line_fig, use_container_width=True)
right.plotly_chart(
    px.bar(filtered.groupby("continent", as_index=False)["lifeExp"].sum(),
           x="continent", y="lifeExp"),
    use_container_width=True,
)

st.dataframe(filtered, use_container_width=True)