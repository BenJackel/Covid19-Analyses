import config
import datetime
import streamlit as st
import pandas as pd
import requests
from numpy import nan


def make_immunity_monotonic(data):
    while not data['Total Vaccinated'].is_monotonic:
        data.loc[data['Date']<pd.to_datetime('Jan 5, 2021'), 'Total Vaccinated'] = 0
        data['vacc_diff'] = data['Total Vaccinated'].diff()
        data.loc[data['vacc_diff'] <= 0, 'Total Vaccinated'] = nan
        data['Total Vaccinated'] = data['Total Vaccinated'].ffill().fillna(0).astype(int)
    data = data.drop('vacc_diff', axis=1, errors='ignore')
    return data


class Data():
    def __init__(self, province):
        self.as_of_date = datetime.datetime.today().date()
        self.province = config.Province(province)
        df, _ = get_case_data(self.as_of_date)
        self.data = df.query(f'Province=="{self.province.name}"')
        self.__add_vaccinated()
        self.__add_immunity()
        self.__calculate_R()

    def __add_vaccinated(self):
        df = self.data.copy()
        vaccine_data, date = get_vaccine_history(self.as_of_date)
        df = df.merge(vaccine_data, on=['Date', 'Province'], how='left')
        df['Total Vaccinated'] = df['Total Vaccinated'].fillna(0).astype(int)
        df['New Vaccinated'] = df['New Vaccinated'].fillna(0).astype(int)
        self.data = df
        return self

    def __add_immunity(self):
        df = self.data.copy()
        df = df.groupby(['Province']).apply(make_immunity_monotonic)
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
    df = pd.read_csv(data_url, parse_dates=['date'])
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
    return df, as_of_date


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
    prov_names = {abbr: name for abbr, name in config.province_data[['abbr', 'name']].values}
    df['Province'] = df['Province'].apply(lambda x: prov_names.get(x, x))
    return df, as_of_date
