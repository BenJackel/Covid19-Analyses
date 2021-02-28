from pandas import DataFrame, to_datetime, read_csv, read_json
from pathlib import Path
import requests
import datetime
# import streamlit as st


def get_province_data(as_of_date):
    data_url = 'https://api.opencovid.ca/other?loc=prov&stat=prov'
    resp = requests.get(data_url)
    df = DataFrame(resp.json()['prov'])
    df.rename(columns={
        'province_full': 'name',
        'province_short': 'abbr',
        'pop': 'population'
    }, inplace=True)
    return df


province_data = get_province_data(datetime.datetime.today().date())

interventions = {
            'SK': [
                {'Date': to_datetime('03-13-2020'), 'Measure': 'First restrictions, gathering size > 250', 'Type': 'Tighten'},
                {'Date': to_datetime('03-18-2020'), 'Measure': 'State of Emergency', 'Type': 'Notice'},
                {'Date': to_datetime('03-26-2020'), 'Measure': 'Gatherings limited to 10', 'Type': 'Tighten'},
                {'Date': to_datetime('09-02-2020'), 'Measure': 'School Starts', 'Type': 'Event'},
                {'Date': to_datetime('05-04-2020'), 'Measure': 'Medical clinics reopen / Campsites', 'Type': 'Ease'},
                {'Date': to_datetime('05-19-2020'), 'Measure': 'Personal Care', 'Type': 'Ease'},
                {'Date': to_datetime('06-08-2020'), 'Measure': 'Gathering size increase, beaches, playgrounds, fitness, child care open', 'Type': 'Ease'},
                {'Date': to_datetime('06-22-2020'), 'Measure': 'Outdoor Rec, Gathings up to 30, outdoor sports allowed', 'Type': 'Ease'},
                {'Date': to_datetime('07-06-2020'), 'Measure': 'Bars, Restaraunts, Casinos, Bingo, Indoor Rec Open', 'Type': 'Ease'},
                {'Date': to_datetime('10-12-2020'), 'Measure': 'Thanksgiving', 'Type': 'Event'},
                {'Date': to_datetime('11-03-2020'), 'Measure': 'Local Mask Policy (Regina, PA, Saskatoon)', 'Type': 'Tighten'},
                {'Date': to_datetime('11-19-2020'), 'Measure': 'Province-wide Mask Policy', 'Type': 'Tighten'},
                {'Date': to_datetime('11-27-2020'), 'Measure': 'Indoor gatherings capacity restrictions, group and teams sports cancelled', 'Type': 'Tighten'},
                {'Date': to_datetime('12-14-2020'), 'Measure': 'Social gather restrictions, capacity restrictions for retailers', 'Type': 'Tighten'}
            ],
            'QC': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'PE': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'NS': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'NB': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'ON': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'MB': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'AB': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'BC': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'YT': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'NWT': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'NU': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ],
            'NL': [
                {'Date': to_datetime('03-01-2020'), 'Measure': '', 'Type': ''}
            ]

        }

class Province():

    def __init__(self, province):
        self.data = self.__get_province_data(province)
        self.name = self.data['name'].values[0]
        self.abbr = self.data['abbr'].values[0]
        self.population = self.data['population'].values[0]
        self.interventions = self.__get_interventions()

    def __get_interventions(self):
        if self.abbr in interventions:
            return DataFrame(interventions.get(self.abbr)).sort_values(['Date'])

    def __get_province_data(self, province):
        df = province_data.query(f"(name=='{province}') or (abbr=='{province}')")
        return df
