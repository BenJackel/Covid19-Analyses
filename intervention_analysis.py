import requests
import config
import io
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.colors as mcolors
import datetime
import seaborn as sns
import streamlit as st


colors = list(mcolors.XKCD_COLORS.values())

class Data():
    def __init__(self, province):
        self.as_of_date = datetime.datetime.today().date()
        self.province = config.Province(province)
        self.data = get_case_data(self.as_of_date).query(f'Province=="{self.province.name}"')  
        self.__add_vaccinated()
        self.__add_immunity()
        self.__calculate_R()

    def __add_vaccinated(self):
        df = self.data.copy()
        vaccine_data = get_vaccine_history(self.as_of_date)
        df = df.merge(vaccine_data, on=['Date', 'Province'], how='left')
        df['Total Vaccinated'] = df['Total Vaccinated'].fillna(0).astype(int)
        df['New Vaccinated'] = df['New Vaccinated'].fillna(0).astype(int)
        self.data = df
        return self

    def __add_immunity(self):
        df = self.data.copy()
        df['Immunity (Lower Bound)'] = (df['Total Cases'] + df['Total Vaccinated']) / self.province.population
        df['Immunity (Upper Bound)'] = (df['Total Cases']*5 + df['Total Vaccinated']) / self.province.population
        self.data = df
        return self

    def __calculate_R(self):
        df = self.data.sort_values(['Date']).copy()
        df['S'] = self.province.population - df['Total Cases']
        df['I'] = df['Active Cases']
        df['R'] = df['Total Recovered'] + df['Total Deaths']

        df[['S', 'I', 'R']] = df[['S', 'I', 'R']] / self.province.population

        R = df['I'].shift(-1) - df['I'].shift(1)
        R /= df['S'].shift(-1) - df['S'].shift(1)
        R += 1
        R *= df['S']
        R = 1 / R
        R = R.clip(upper=10, lower=0)
        df['R(t)'] = R
        df = df.drop(['I', 'S', 'R'], 1)
        self.data = df
        return self


@st.cache(allow_output_mutation=True)
def get_case_data(as_of_date):
    data_url = 'https://health-infobase.canada.ca/src/data/covidLive/covid19-download.csv'
    resp = requests.get(data_url)
    if resp.content:
        df = pd.read_csv(io.BytesIO(resp.content), parse_dates=['date'])

    col_names = {
        'prname': 'Province',
        'date': 'Date',
        'numtoday': 'New Cases',
        'numrecover': 'Total Recovered',
        'numdeathstoday': 'New Deaths',
        'numtotal': 'Total Cases',
        'numdeaths': 'Total Deaths',
        'numrecoveredtoday': 'New Recovered',
        'numactive': 'Active Cases'
    }


    df.rename(columns=col_names, inplace=True)
    df = df[col_names.values()]
    df = df.fillna(0)
    int_cols = {col: int for col in df.columns[~df.columns.isin(['Province', 'Date'])].to_list()}
    df = df.astype(dtype=int_cols)
    return df


@st.cache(allow_output_mutation=True)
def get_vaccine_history(as_of_date):
    data_url = 'https://api.opencovid.ca/timeseries?stat=avaccine&loc=prov'
    resp = requests.get(data_url)
    df = pd.DataFrame(resp.json()['avaccine'])
    df.rename(columns={
        'date_vaccine_administered': 'Date',
        'province': 'Province',
        'avaccine': 'New Vaccinated',
        'cumulative_avaccine': 'Total Vaccinated'
    }, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'])
    # Normalize province names
    prov_names = config.province_names
    df['Province'] = df['Province'].apply(lambda x: prov_names.get(x, x))
    return df


def smooth_data(df, window):
    df['R(t) (smoothed)'] = df.set_index('Date')['R(t)'].rolling(f'{window}d').mean().values
    df['New Cases (smoothed)'] = df.set_index('Date')['New Cases'].rolling(f'{window}d').mean().values
    df['Active Cases (smoothed)'] = df.set_index('Date')['Active Cases'].rolling(f'{window}s').mean().values
    return df


def plot_R(data, window):
    df = smooth_data(data.data, window)
    fig, ax = plt.subplots(figsize=(21,9))
    ax1 = df.set_index('Date')['R(t) (smoothed)'].plot(ax=ax, secondary_y=True, label=f'R(t) ({window} day average)')
    ax2 = (df.set_index('Date')['New Cases (smoothed)']).plot(ax=ax, label=f'Daily New Cases ({window} day average)')
    # ax2 = df.set_index('Date')['Total Cases'].pct_change(freq='14d').plot(ax=ax, label=f'% Change in New Cases')
    # (df.set_index('Date')['I (smoothed)']*province.population).plot(ax=ax)
    for index, row in data.province.interventions.iterrows():
        date = row['Date']
        measure = row['Measure']
        ax.axvline(date, color=colors[index], label=measure)

    # Add line to denote where R=1 is
    ax1.axhline(1, ls='--', c='red')
    ax1.text(x=df['Date'].max(), y=1.1, s='R = 1')
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()

    ax.legend(h1+h2, l1+l2, bbox_to_anchor=(0, -0.75), loc='lower left')
    return fig


def plot_immunity(data):
    df = data.data[['Date', 'Immunity (Lower Bound)', 'Immunity (Upper Bound)']].copy()
    df = df.melt('Date', var_name='Confidence', value_name='Immunity Percentage')
    df['Immunity Percentage'] *= 100
    fig, ax = plt.subplots(figsize=(21,9))
    sns.lineplot(
        data=df,
        x='Date',
        y='Immunity Percentage',
        hue='Confidence',
        ax=ax
    )
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    return fig    


def app():
    prov_options = list(config.province_names.values())
    default_index = prov_options.index('Saskatchewan')
    province_selection = st.sidebar.selectbox(
        "Select Province", 
        options=prov_options,
        index=default_index
    )
    
    data = Data(province_selection)

    st.write(data.province.interventions)

    st.write(plot_R(data, 14))

    # st.write(data.data)

    st.write(plot_immunity(data))

if __name__ == "__main__":
    st.set_page_config(layout='wide')

    app()
