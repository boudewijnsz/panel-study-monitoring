#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ast
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import dotenv_values
from ibridges import Session
from ibridges.search import search_data
from ibridges.path import IrodsPath
from ibridges import download
from ibridges import upload

print("processing Garmin stats")

# load the variables defined in the env file
# config_path = r"O:\DGK\IRAS\EEPI\Projects\Exposome-Panel Study\Datamanagement\study_admin_code\panel-study-monitoring\.env"
config_path = Path(Path(__file__).resolve().parent.parent, '.env')
config = dotenv_values(config_path)

yoda_password = dotenv_values(config['YODA'])['YODA']

# start an ibridges session to create the overview of all the files present in Yoda
env_file = Path.expanduser(Path('~')).joinpath(".irods", "irods_environment.json")
session = Session(irods_env=env_file, password=yoda_password)

keylist_path = IrodsPath(session, config['YODA_MMWEEK_DIR'], config['FILE_NAME_LDOT'])
with keylist_path.open('r') as stream:
    key_table = pd.read_csv(stream, dtype=str, sep=';')

# load the most recent overwiew of daily Garmin data, this file contains
# the most relevant data like HR and number of steps. The daily file
# is created by the script garmin_data_overview.py
garmin_processed_dir_yoda = 'research-expanse-garmin/processed/'
daily_files = search_data(session, path=str(garmin_processed_dir_yoda), path_pattern="daily%")

daily_files_df = pd.DataFrame({'file': [str(f) for f in daily_files]})
daily_files_df['file_date'] = daily_files_df['file'].str.extract('([0-9]{4}-[0-9]{2}-[0-9]{2})')
daily_files_df['file_date'] = pd.to_datetime(daily_files_df['file_date'])

# load the data from the most recent file
most_recent_daily_file = daily_files_df[daily_files_df['file_date'] == daily_files_df['file_date'].max()]['file'].iloc[0]

print("loading data from {}".format(most_recent_daily_file))

# because the file is big, streaming takes long. Therefore download and load in to dataframe
# downloads_path = r"O:\DGK\IRAS\EEPI\Projects\Exposome-Panel Study\Datamanagement\study_admin_code\panel-study-monitoring\downloads"
downloads_path = Path(Path(__file__).resolve().parent.parent, 'downloads')
irods_path = IrodsPath(session, '~', most_recent_daily_file)
download(session, irods_path, downloads_path, overwrite=True)

daily_download_path = Path(downloads_path, Path(most_recent_daily_file).name)

most_recent_daily = pd.read_csv(daily_download_path, sep=';')

# in the first few days, it's possible there is no data in the jsons yet because
# participants haven't signed up yet
# in that case, create an empty df to still be able to create the general overview
if most_recent_daily.shape[0] > 0:

    # add AID to the daily data
    most_recent_daily_aid = key_table[['Studienummer', 'garmin_access_token']].merge(most_recent_daily, how='left', left_on='garmin_access_token', right_on='userAccessToken')

    daily_aid_counts = most_recent_daily_aid[['Studienummer', 'garmin_access_token', 'calendarDate']].groupby(['Studienummer', 'garmin_access_token']).nunique().reset_index()

    daily_aid_min_date = most_recent_daily_aid[['Studienummer', 'calendarDate']].groupby('Studienummer').min().reset_index().rename(columns={'calendarDate': 'min_date'})
    daily_aid_max_date = most_recent_daily_aid[['Studienummer', 'calendarDate']].groupby('Studienummer').max().reset_index().rename(columns={'calendarDate': 'max_date'})

    daily_aid_overview = daily_aid_counts.merge(daily_aid_min_date, how='left', on='Studienummer').merge(daily_aid_max_date, how='left', on='Studienummer')

    daily_aid_counts= daily_aid_counts.rename(columns={'calendarDate': 'file_available'})

    # process heart rate data for participants
    data_daily_hr_cols = most_recent_daily_aid[['Studienummer', 'userAccessToken', 'startTimeInSeconds', 'timeOffsetHeartRateSamples']]

    data_daily_hr_cols['date'] = pd.to_datetime(data_daily_hr_cols['startTimeInSeconds'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Europe/Amsterdam')

    data_daily_hr = pd.DataFrame()
    data_daily_hr_hist = pd.DataFrame()

    # there are empty dicts and float nan values in the data. Convert timeOffsetHeartRateSamples to string for easier
    # capture of nan values. math.isnan didnt work cause most rows are strings

    data_daily_hr_cols = data_daily_hr_cols.fillna('')

    for index, row in data_daily_hr_cols.iterrows():

        start_date = row['date']
        id = row['Studienummer']
        access_token = row['userAccessToken']


        if row['timeOffsetHeartRateSamples'] == '{}' or row['timeOffsetHeartRateSamples'] == '':

            data_hr_user = pd.DataFrame({'Studienummer': [id]})

            # for the empty data add empty dicts to the hist dataframe
            data_hr_user_hist_out = pd.DataFrame({'Studienummer': [id]})

        else:
            try: 
                data_hr_user = pd.DataFrame(ast.literal_eval(row['timeOffsetHeartRateSamples']).items()).rename(columns={0: 'time', 1: 'hr'})

                data_hr_user['time'] = data_hr_user['time'].astype(int)

                data_hr_user['hr_measure_time'] = start_date + pd.to_timedelta(data_hr_user['time'], unit='s')

                data_hr_user = data_hr_user.sort_values('hr_measure_time')

                data_hr_user['Studienummer'] = id

                data_hr_user['userAccessToken'] = access_token

                data_hr_user['date'] = data_hr_user['hr_measure_time'].dt.date

                data_hr_user['hour'] = data_hr_user['hr_measure_time'].dt.hour

                data_hr_user_hist = data_hr_user.groupby(['Studienummer', 'userAccessToken', 'date', 'hour'])['hr'].count().reset_index().rename(columns={'hr': 'measurements'})
                data_hr_user_hist['measurements'] = data_hr_user_hist['measurements'].astype(int) 


                # merge to all hours in the day to also show hours with no data. There can be multiple dates
                # in each dataframe so create the table with hours in a day for all dates
                all_hours_date = pd.DataFrame()
                for date in data_hr_user['date'].drop_duplicates():
                    hours = pd.DataFrame({'hour': range(0, 24)})
                    hours['date'] = date
                    all_hours_date = pd.concat([all_hours_date, hours])

                data_hr_user_hist_out = all_hours_date.merge(data_hr_user_hist, how='left', on=['date', 'hour'])
                data_hr_user_hist_out = data_hr_user_hist_out[['Studienummer', 'userAccessToken', 'date', 'hour', 'measurements']]
                data_hr_user_hist_out['measurements'] = data_hr_user_hist_out['measurements'].fillna(0)


            except Exception as e:
                print(e)
                print(index, row['timeOffsetHeartRateSamples'])
                print(row['timeOffsetHeartRateSamples'] == None)
                print(type(row['timeOffsetHeartRateSamples']))
        
        data_daily_hr_hist = pd.concat([data_daily_hr_hist, data_hr_user_hist_out])

        data_daily_hr_hist = data_daily_hr_hist.drop_duplicates()
        
        # remove the downloaded file to keep things organized
    Path.unlink(daily_download_path)

     # load the overview to the panel monitoring Yoda dir
    date = datetime.today().strftime("%Y-%m-%d")
    processed_dir = config['YODA_MONITORING_DIR']

    # store the overview with file counts
    irods_save_path_overview = IrodsPath(session, processed_dir + '/garmin_overview_{}.csv'.format(date))
    with irods_save_path_overview.open('w') as new_obj:

        new_obj.write(daily_aid_overview.to_csv(sep=';', index=False).encode())

    # store the overview with hist
    irods_save_path_hist = IrodsPath(session, processed_dir + '/garmin_overview_hr_counts_{}.csv'.format(date))
    with irods_save_path_hist.open('w') as new_obj:

        new_obj.write(data_daily_hr_hist.to_csv(sep=';', index=False).encode())

    # sometimes there are jsons but they don't contain data from the current batch
    # that also give issues. In that case some columns need to be added

    if len(data_daily_hr_hist.columns) == 1:
        data_daily_hr_hist = data_daily_hr_hist.assign(userAccessToken = '',
                                                        date = '',
                                                        hour = '',
                                                        measurements = '') 
        

else:
    # in case no data yet for Garmins
    data_daily_hr_hist = pd.DataFrame(
        columns=['Studienummer', 'userAccessToken', 'date', 'hour', 'measurements']
        )


# store a version of the hist data in the downloads folder to add the data to 
# the sodaq sensor overview
data_daily_hr_hist.to_csv(
    Path(downloads_path, 'data_daily_hr_hist.csv'), index=False
)
