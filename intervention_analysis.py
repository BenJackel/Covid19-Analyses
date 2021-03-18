import requests
import config
import pandas as pd
import datetime
import streamlit as st
import altair as alt
from data import Data
from numpy import nan


def smooth_data(df, window):
    df['R(t) (smoothed)'] = df.set_index('Date')['R(t)'].rolling(f'{window}d').mean().values
    df['New Cases (smoothed)'] = df.set_index('Date')['New Cases'].rolling(f'{window}d').mean().values
    df['Active Cases (smoothed)'] = df.set_index('Date')['Active Cases'].rolling(f'{window}s').mean().values
    return df


def plot_R_altair(data, window):
    df = smooth_data(data.data, window)
    df['R(t) (smoothed)'] = df['R(t) (smoothed)'].round(1)
    df['New Cases (smoothed)'] = df['New Cases (smoothed)'].round(0).astype(int)

    min_date = data.data['Date'].min()
    # Add a yval so that we can move the Points
    int_df = data.province.interventions
    int_df = int_df[int_df['Date'] >= min_date]
    int_df['yval'] = 1

    scale = alt.Scale(
        domain=['R(t) (smoothed)', 'New Cases (smoothed)'],
        range=['gray', 'blue']
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

    R = alt.Chart(df).mark_line(stroke='gray').transform_fold(
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


    C_text = C.mark_text(align='left', dx=5, dy=-5).encode(
        text=alt.condition(
            nearest, 
            'New Cases (smoothed):Q', 
            alt.value(' ')
        )
    )

    # Draw a rule at the location of the selection
    rules = alt.Chart(df).mark_rule(color='gray').encode(
        x='Date:T',
    ).transform_filter(
        nearest
    )

    date_text = rules.mark_text(align='left', dx=5, dy=0).encode(text='Date:T')

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
    reference = alt.Chart(pd.DataFrame({'y':[1]})).mark_rule(strokeDash=[10,10]).encode(y='y')

    layer1 = R + selectors + rules + R_points + R_text + date_text + reference + areas
    layer2 = C + C_points + C_text
    layer3 = interventions
    chart = alt.layer(layer1, layer2).resolve_scale(y='independent')
    chart = alt.layer(chart, layer3).resolve_scale(x='shared', color='independent', shape='independent')
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


def app():
    prov_options = list(config.province_data['name'].values)
    default_index = prov_options.index('Saskatchewan')
    province_selection = st.sidebar.selectbox(
        "Select Province", 
        options=prov_options,
        index=default_index
    )
    
    data = Data(province_selection)

    st.write(data.province.interventions)

    st.write(data.data[['Date', 'New Vaccinated', 'Total Vaccinated']])

    col1, _, _, _ = st.beta_columns(4)
    with col1:
        d1 = st.sidebar.date_input(label='Start Date', value=pd.to_datetime('03-01-2020'))
        date_mask = data.data['Date'] >= pd.to_datetime(d1)
        data.data = data.data[date_mask]

    st.altair_chart(plot_R_altair(data, 7), use_container_width=True)

    st.altair_chart(plot_immunity(data), use_container_width=True)

if __name__ == "__main__":
    st.set_page_config(layout='wide')

    app()
