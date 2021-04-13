import requests
import config
import pandas as pd
import datetime
import streamlit as st
import altair as alt
from data import Data
from numpy import nan
from scipy.integrate import cumtrapz
from streamlit import config as st_config


def smooth_data(df, window):
    df['R(t) (smoothed)'] = df.set_index('Date')['R(t)'].rolling(f'{window}d').mean().values
    df['New Cases (smoothed)'] = df.set_index('Date')['New Cases'].rolling(f'{window}d').mean().values
    df['Active Cases (smoothed)'] = df.set_index('Date')['Active Cases'].rolling(f'{window}s').mean().values
    return df


def plot_R(data, window):
    df = smooth_data(data.data, window)
    df['R(t) (smoothed)'] = df['R(t) (smoothed)'].round(1)
    df['New Cases (smoothed)'] = df['New Cases (smoothed)'].round(0).astype(int)

    min_date = data.data['Date'].min()
    # Add a yval so that we can move the Points
    int_df = data.province.interventions
    int_df = int_df[int_df['Date'] >= min_date]
    int_df['yval'] = 1

    scale = alt.Scale(
        domain=['R(t) (smoothed)', 'New Cases (smoothed)', 'New Cases'],
        range=['#662E9B', 'blue', 'grey']
    )

    nearest = alt.selection(
        type='single',
        nearest=True,
        on='mouseover',
        fields=['Date'],
        empty='none'
    )

    # Transparent selectors across the chart. This is what tells us
    # the x-value of the cursor
    selectors = alt.Chart(df).mark_point().encode(
        x='Date:T',
        opacity=alt.value(0),
    ).add_selection(
        nearest
    )

    color=alt.condition(
        alt.datum['R(t) (smoothed)'] > 1.0,
        alt.value('red'),
        alt.value('green')
    )

    R = alt.Chart(df).mark_line(stroke='#662E9B').transform_fold(
            fold=['R(t) (smoothed)', 'New Cases (smoothed)'],
            as_ = ['Timeseries', 'value']
        ).encode(
            x=alt.X('Date:T', axis=alt.Axis(title='Date')),
            y=alt.Y('R(t) (smoothed)', axis=alt.Axis(title='R(t)')),
            color=alt.Color('Timeseries:N', scale=scale)
        )

    C = alt.Chart(df).mark_line(stroke='blue').encode(
        x=alt.X('Date:T', axis=alt.Axis(title='Date')),
        y=alt.Y('New Cases (smoothed)', axis=alt.Axis(title='New Cases'))
    )

    R_points = R.mark_point().encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        color=color
    )
    C_points = C.mark_point().encode(
        opacity=alt.condition(nearest, alt.value(1), alt.value(0))
    )

    R_text = R.mark_text(align='left', dx=5, dy=-5).encode(
        text=alt.condition(
            nearest, 
            'R(t) (smoothed):Q', 
            alt.value(' ')
        ),
        color=color
    )

    # Draw some rectangles to shade
    areas = R.mark_rule(opacity=0.2).encode(
        color=color
    )


    C_text = C.mark_text(align='left', dx=5, dy=-5, stroke='blue').encode(
        text=alt.condition(
            nearest, 
            'New Cases (smoothed):Q', 
            alt.value(' ')
        )
    )

    # Draw a rule at the location of the selection
    rules = alt.Chart(df).mark_rule(color='gray').encode(        x='Date:T',
    ).transform_filter(
        nearest
    )

    date_text = rules.mark_text(align='left', dx=5, dy=0, stroke='blue').encode(text='Date:T')

    # Draw triangles for the interventions
    shape_scale = alt.Scale(
        domain=['Tighten', 'Ease', 'Event'],
        range=['triangle-up', 'triangle-down', 'diamond']
    )
    shape_color_scale = alt.Scale(
        domain=['Tighten', 'Ease', 'Event'],
        range=['red', 'green', 'blue']
    )
    interventions = alt.Chart(int_df).mark_point(size=500, filled=True).encode(
        x=alt.X('Date:T'),
        y=alt.Y('yval:Q', title=''),
        shape=alt.Shape(
            'Type:N', 
            scale=shape_scale, 
            title='Intervention Type'
        ),
        tooltip=alt.Tooltip(['Measure', 'Date', 'Type']),
        color=alt.Color('Type:N', scale=shape_color_scale)
    )

    # Draw the R=1 reference line
    reference = alt.Chart(pd.DataFrame({'y':[1]})) \
                   .mark_rule(strokeDash=[10,10], stroke='green') \
                   .encode(y=alt.Y('y:Q', axis=alt.Axis(title='')))

    layer1 = R + selectors + rules + R_points + R_text + date_text + reference
    daily_cases_df = data.data[['Date', 'New Cases']].copy()
    daily_case_chart = alt.Chart(daily_cases_df).mark_bar(opacity=0.25, color='grey').encode(
        x=alt.X('Date:T'),
        y=alt.Y('New Cases:Q')
    )
    layer2 = C + C_points + C_text + daily_case_chart

    layer3 = interventions + areas
    chart = alt.layer(layer1, layer2).resolve_scale(y='independent')
    chart = alt.layer(chart, layer3).resolve_scale(x='shared', color='independent', shape='independent')


    # chart = alt.layer(chart, daily_case_chart).resolve_scale(x='shared')
    return chart


def plot_immunity(data):
    df = data.data[['Date', 'Immunity (Lower Bound)', 'Immunity (Upper Bound)']].copy()
    df = df.set_index('Date').rolling(window='14d').mean().reset_index()

    chart = alt.Chart(df).mark_area(opacity=0.5).encode(
        x='Date:T',
        y=alt.Y('Immunity (Lower Bound):Q', title='Immunity %', axis=alt.Axis(format='%')),
        y2=alt.Y2('Immunity (Upper Bound):Q', title=''),
        tooltip=alt.Tooltip('Date')
    )

    return chart


def integrate_a(df_in):
    # Start from rest @ x=0
    # v_0 = 0
    # x_0 = 0
    # x = x_0 + v_0(t-t_0) + 0.5 * a(t - t_0)^2
    df_out = df_in.copy()
    df_out['delta_t'] = df_in['Date'].diff() / pd.Timedelta('1 s')
    delta_t = df_out['delta_t'].fillna(0).cumsum().values

    a = df_in['Acceleration'].values
    v = cumtrapz(a, x=delta_t)
    x = cumtrapz(v[:], x=delta_t[1:])


    df_out['Velocity'] = 0
    df_out['Position'] = 0
    df_out.loc[1:, 'Velocity'] = v
    df_out.loc[2:, 'Position'] = x
    return df_out


def plot_acceleration():

    df = pd.DataFrame({
        'Date': pd.date_range(
            start=pd.to_datetime('2020-01-01 00:00:00'),
            end=pd.to_datetime('2020-01-01 00:05:00'),
            freq='1 s'
        )
    })
    n_time = df['Date'].count()
    df['Acceleration'] = 0
    df.loc[10:20, 'Acceleration'] = 0.1
    df.loc[50:55, 'Acceleration'] = -.1
    df.loc[150:153, 'Acceleration'] = -.1

    df = integrate_a(df)

    A = alt.Chart(df).mark_line(stroke='green').encode(
        x=alt.X('Date:T', axis=alt.Axis(title='Date')),
        y=alt.Y('Acceleration:Q', axis=alt.Axis(title='a(t)')),
    )

    X = alt.Chart(df).mark_line(stroke='red').encode(
        x=alt.X('Date:T', axis=alt.Axis(title='Date')),
        y=alt.Y('Velocity:Q', axis=alt.Axis(title='v(t)')),
    )

    chart = alt.layer(A, X).resolve_scale(y='independent')

    return chart

def app():

    today = pd.to_datetime(datetime.datetime.now().date())

    prov_options = list(config.province_data['name'].values)
    prov_options = [p for p in prov_options if p not in ['Repatriated', 'Acceleration']]
    default_index = prov_options.index('Saskatchewan')
    province_selection = st.sidebar.selectbox(
        "Select Province", 
        options=prov_options,
        index=default_index
    )
    
    data = Data(province_selection)

    st.sidebar.write("Limit the view of the data:")
    d1 = st.sidebar.date_input(label='Start Date', value=pd.to_datetime('03-01-2020'))
    d2 = st.sidebar.date_input(label='End Date', value=today)

    date_mask = data.data['Date'] >= pd.to_datetime(d1)
    date_mask = date_mask & (data.data['Date'] <= pd.to_datetime(d2))
    data.data = data.data[date_mask]

    st.markdown("""
    # Intervention Analysis

    The purpose of this visualization is to explore the effects of interventions on the spread of Covid-19 within Canada. 
    Further, I am also tracking the immunity level within each province.
    """)

    st.markdown("""
    ## Some background and how to understand the visualizations

    My analysis of how quickly Covid-19 spreads is based on the SIR model and focuses on the Basic Reproduction Number as a diagnostic.
    See [here](https://en.wikipedia.org/wiki/Compartmental_models_in_epidemiology) for more details.

    The equations of this model are as follows:
    """)
    st.markdown(r"""
    $$\frac{dS}{dt} = - \frac{\beta I S}{N},$$

    $$\frac{dI}{dt} = \frac{\beta I S}{N} - \gamma I,$$

    $$\frac{dR}{dt} = \gamma I$$

    Here, $S$ is the number of people who are susceptible, 
    $I$ is the number of infected, 
    $R$ is the number of people who are are no longer susceptible 
    (due to Recovery, Death, Natural Immunity, or Vaccination)

    The ratio, $R_0 = \frac{\beta}{\gamma}$ is called the Basic Reproduction number. It represents how many people an infected person will infect.
    Mathematically, when $R_0 > 1$ the equations indicate exponential growth of new infections.

    **The goal of interventions, and indeed Social Distancing is to get $R < 1$.**

    This can be a confusing point, so I am going to show an example a little closer to our everyday experience.
    Imagine you are in a car. If you start from 0 velocity and press the gas pedal, you'll gain an acceleration.
    That is, the longer you hold the gas pedal, the more your velocity (or speed) will increase. If you hit the brakes, 
    your acceleration will be negative and your velocity will decrease.

    The following plot demonstrates this. The green line represents the acceleration and the red line is the velocity. When the green line is $> 0$, the red line will increase.
    When the green line is $< 0$, the red line will decrease. If the green line is 0, the red line will stay the same.
    """)

    # When one solves these equations, some constants of integration fall out
    # """)
    st.altair_chart(plot_acceleration(), use_container_width=True)

    st.write("""
    To bring this back to Covid, the $R$ value is like the acceleration and the rate of new cases is like the velocity.
    """)

    st.write("""
    ## Provincial Interventions
    This next part is missing data for many provinces since the interventions have to be entered manually. 
    Currently, Saskatchewan and some of Quebec have interventions entered.
    """)

    st.markdown("""
    In the following plot: 
    * the Blue line represents new cases by day
    * the grey line represents the $R$ value
    * the symbols are a Red up arrow for tighted restrictions, Green down arrow for eased restrictions and Blue diamond for events like holidays
    * you can hover over the chart to get more information
    * the $R$ line is color coded so that if it is $<1$ it is green, else it is red 

    There is a very important consideration while interpretting the following: 
    There is a lag between when an intervention is implemented and when we would expect to see an effect.
    This lag is an empirical measurement and appears to be about 14 days. This lag is related to how long a person is infectious; 
    how long before an infected person becomes infectious; and how long it takes to reach a statistically significant difference. 
    (Plus many more potential interactions)
    """)
    # st.write(data.province.interventions)
    st.altair_chart(plot_R(data, 7), use_container_width=True)


    st.markdown("## The Path to Herd Immunity")
    st.markdown("""
    If one solves the SIR model for some initial conditions, 
    infections eventually slow down and stop all together as the number of susceptible people reaches a threshold. This
    threshold represents "Herd Immunity". However, there is no single value for when a population reaches the immunity 
    level to qualify for Herd Immunity. 
    Any such value would be strongly dependent on local conditions. Many epidemiologists suggest 
    immunity levels anywhere from 70% on the low end to 90% on the high end.

    In the following, I have calculated a reasonable range of possible immunity levels by province. That is, the lower bound is set
    by the number of reported cases + the number who have recieved a first does of a vaccine.

    The upper bound of that range is harder to quantify. Recently, the [CDC](https://www.cdc.gov/coronavirus/2019-ncov/cases-updates/burden.html) 
    has estimated that (especially early in the pandemic) 1 in 4.6 infections were reported. This is for the US, however it is not unreasonable to
    assume a similar value for Canada. For simplicity, I chose a value of 5. 
    The upper bound is calculated as the number of daily cases * 5 + # vaccinated.
    """)
    st.altair_chart(plot_immunity(data), use_container_width=True)

    with st.beta_expander("Footnotes"):
        st.markdown("""
            Case and vaccine data come from the [Covid-19 Canada Open Data Working Group](https://opencovid.ca/) and
            [here](https://health-infobase.canada.ca/src/data/covidLive/covid19-download.csv)
        """)


if __name__ == "__main__":
    st.set_page_config(layout='wide')

    app()
