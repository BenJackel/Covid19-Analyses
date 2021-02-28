from pandas import DataFrame, to_datetime, read_csv
from pathlib import Path

province_names = {
                  'ON':'Ontario',
         'BC':'British Columbia',
                   'CA':'Canada',
                   'QC':'Quebec',
                  'AB':'Alberta',
             'SK':'Saskatchewan',
                 'MB':'Manitoba',
            'NB':'New Brunswick',
'NL':'Newfoundland and Labrador',
              'NS':'Nova Scotia',
     'PE':'Prince Edward Island',
    'NWT':'Northwest Territories',
                  'NU':'Nunavut',
                    'YT':'Yukon',
   'RP':'Repatriated travellers'
}

province_abbrs = {v: k for k, v in province_names.items()}

population_data = {
    'NL': 520998,
    'PE': 159713,
    'NS': 979115,
    'NB': 781315,
    'QC': 8575779,
    'ON': 14733119,
    'MB': 1379584,
    'SK': 1177884,
    'AB': 4428112,
    'BC': 5145851,
    'YT': 42176,
    'NWT': 45074,
    'NU': 39285
}

interventions = {
            'SK': [
                {'Date': to_datetime('03-13-2020'), 'Measure': 'First restrictions, gathering size > 250'},
                {'Date': to_datetime('03-18-2020'), 'Measure': 'State of Emergency'},
                {'Date': to_datetime('03-26-2020'), 'Measure': 'Gatherings limited to 10'},
                {'Date': to_datetime('09-02-2020'), 'Measure': 'School Starts'},
                {'Date': to_datetime('05-04-2020'), 'Measure': 'Medical clinics reopen / Campsites'},
                {'Date': to_datetime('05-19-2020'), 'Measure': 'Personal Care'},
                {'Date': to_datetime('06-08-2020'), 'Measure': 'Gathering size increase, beaches, playgrounds, fitness, child care open'},
                {'Date': to_datetime('06-22-2020'), 'Measure': 'Outdoor Rec, Gathings up to 30, outdoor sports allowed'},
                {'Date': to_datetime('07-06-2020'), 'Measure': 'Bars, Restaraunts, Casinos, Bingo, Indoor Rec Open'},
                {'Date': to_datetime('10-12-2020'), 'Measure': 'Thanksgiving'},
                {'Date': to_datetime('11-03-2020'), 'Measure': 'Local Mask Policy (Regina, PA, Saskatoon)'},
                {'Date': to_datetime('11-19-2020'), 'Measure': 'Province-wide Mask Policy'},
                {'Date': to_datetime('11-27-2020'), 'Measure': 'Indoor gatherings capacity restrictions, group and teams sports cancelled'},
                {'Date': to_datetime('12-14-2020'), 'Measure': 'Social gather restrictions, capacity restrictions for retailers'}
            ],
            'QC': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'PE': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'NS': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'NB': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'ON': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'MB': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'AB': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'BC': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'YT': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'NWT': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ],
            'NU': [
                {'Date': to_datetime('03-01-2020'), 'Measure': ''}
            ]

        }

class Province():

    def __init__(self, province):
        self.name = province_names.get(province, province)
        self.abbr = province_abbrs.get(self.name)
        self.vaccine_file = Path(f'data').joinpath(f'{self.abbr}_vaccines.csv')
        self.population = population_data.get(self.abbr)
        self.interventions = self.__get_interventions()

    def __get_interventions(self):
        if self.abbr in interventions:
            return DataFrame(interventions.get(self.abbr)).sort_values(['Date'])