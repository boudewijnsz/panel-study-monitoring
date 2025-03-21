# %%
# -*- coding: utf-8 -*-
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import dotenv_values
from ibridges import Session
from ibridges.search import search_data
from ibridges.path import IrodsPath
from ibridges import download
from ibridges import upload

# load the variables defined in the env file
config = dotenv_values("./.env")
yoda_password = dotenv_values(config['YODA'])['YODA']

# start an ibridges session to create the overview of all the files present in Yoda
env_file = Path.expanduser(Path('~')).joinpath(".irods", "irods_environment.json")
session = Session(irods_env=env_file, password=yoda_password)

# %%
# load the key table with AID and Access token
key_table_file = config['GARMIN_KEY_TABLE_FILE']

# the data are in different tabs with inconsistent names so parse with loop and dict
key_table_xlsx = pd.ExcelFile(key_table_file)

key_table_tabs = {'November': 'November',
                  'februari': 'February'}

key_table = pd.DataFrame()

for k, v in key_table_tabs.items():
    key_table_batch = pd.read_excel(key_table_xlsx, k)
    key_table_batch['month'] = v

    key_table = pd.concat([key_table, key_table_batch])


key_table.columns

# %%
# load the most recent overwiew of daily Garmin data
garmin_processed_dir_yoda = 'research-expanse-garmin/processed/'
daily_files = search_data(session, path=str(garmin_processed_dir_yoda), path_pattern="daily%")

daily_files_df = pd.DataFrame({'file': [str(f) for f in daily_files]})
daily_files_df['file_date'] = daily_files_df['file'].str.extract('([0-9]{4}-[0-9]{2}-[0-9]{2})')
daily_files_df['file_date'] = pd.to_datetime(daily_files_df['file_date'])

# load the data from the most recent file
most_recent_daily_file = daily_files_df[daily_files_df['file_date'] == daily_files_df['file_date'].max()]['file'].iloc[0]

print("loading data from {}".format(most_recent_daily_file))

# because the file is big, streaming takes long. Therfore download and load in to dataframe
local_path = Path("./downloads")
irods_path = IrodsPath(session, '~', most_recent_daily_file)
download(session, irods_path, local_path, overwrite=True)

daily_download_path = './downloads/' + Path(most_recent_daily_file).name

most_recent_daily = pd.read_csv(daily_download_path, sep=';')

# remove the downloaded file to keep things organized
Path.unlink(daily_download_path)


# %%
most_recent_daily_aid = key_table[['AID', 'month', 'Access token']].merge(most_recent_daily, how='left', left_on='Access token', right_on='userAccessToken')

daily_aid_counts = most_recent_daily_aid[['AID', 'month', 'calendarDate']].groupby(['AID', 'month']).nunique().reset_index()

daily_aid_min_date = most_recent_daily_aid[['AID', 'calendarDate']].groupby('AID').min().reset_index().rename(columns={'calendarDate': 'min_date'})
daily_aid_max_date = most_recent_daily_aid[['AID', 'calendarDate']].groupby('AID').max().reset_index().rename(columns={'calendarDate': 'max_date'})

daily_aid_overview = daily_aid_counts.merge(daily_aid_min_date, how='left', on='AID').merge(daily_aid_max_date, how='left', on='AID')

daily_aid_counts= daily_aid_counts.rename(columns={'calendarDate': 'file_available',
                                                   'AID': 'Studienummer'})

daily_aid_overview = daily_aid_overview.sort_values('month')

daily_aid_overview


# %%
# load the overview to the panel monitoring Yoda dir
date = datetime.today().strftime("%Y-%m-%d")
processed_dir = config['YODA_MONITORING_DIR']

irods_save_path = IrodsPath(session, processed_dir + '/garmin_overview_{}.csv'.format(date))

with irods_save_path.open('w') as new_obj:

    new_obj.write(daily_aid_overview.to_csv(sep=';', index=False).encode())


