#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
import re
from datetime import datetime
from io import StringIO
import os
import pandas as pd
from dotenv import dotenv_values
from ibridges import search_data
from ibridges import Session
from ibridges import IrodsPath

# this script creates csv files from the Garmin json files stored in Yoda. A
# csv file is created for each day, files are stored in yoda

# code modified from garmin_data_overview.py to work with new exports per month

# file with the garmin codes of the measurement week
mweek_garmin_login = r"O:\DGK\IRAS\EEPI\Privacy\Exposome-Panel Study\Meetweken\Meetweken september 2026\garmin_rand_nrs_meetweek_september_linked_2026.xlsx"
check_month = '2026-10'
data_file = 'dailies'

config_path = Path(Path(__file__).parent.parent, '.env')
config = dotenv_values(config_path)
yoda_password = dotenv_values(config['YODA'])['YODA']

# set up ibridges session
env_file = Path.expanduser(Path('~')).joinpath(".irods", "irods_environment.json")
session = Session(env_file, password=yoda_password)

# load the participant overview created using the script "participant_file_prep.py"
keylist_path = IrodsPath(session, config['YODA_MMWEEK_DIR'], config['FILE_NAME_LDOT'])
with keylist_path.open('r') as stream:
    batch_sensor_aid_keylist = pd.read_csv(stream, sep=';', dtype=str)

# load the keytable with Garmin UserIDs and e-mail addresses
garmin_userid_keylist_path = r"O:\DGK\IRAS\EEPI\Privacy\Exposome-Panel Study\Datamanagement\keylists\garmin_user_id_e-mail_address_key_table.csv"
garmin_user_id_keylist = pd.read_csv(garmin_userid_keylist_path, sep=';', dtype=str)

# garmin login credentials current measurement week
garmin_credentials_mmweek = pd.read_excel(mweek_garmin_login, dtype=str)

print("processing Garmin data")

# load the variables defined in the env file
# config_path = "O:\DGK\IRAS\EEPI\Projects\Exposome-Panel Study\Datamanagement\study_admin_code\panel-study-monitoring\.env"
config_path = Path(Path(__file__).resolve().parent.parent, '.env')
config = dotenv_values(config_path)

yoda_password = dotenv_values(config['YODA'])['YODA']


# create inventory of available files on Yoda
garmin_path = config['YODA_GARMIN_SOURCE_DIR']
garmin_files = search_data(session, path=garmin_path, path_pattern="%")

garmin_files_df = pd.DataFrame({'yoda_path': [str(p) for p in garmin_files]})

# only process data from start date of measurement week
if check_month != 'all':

    garmin_files_df['month'] = garmin_files_df['yoda_path'].str.extract('(\\d{4}-\\d{2})')

garmin_files_df = garmin_files_df[garmin_files_df['month'] == check_month]

# only consider monthly files
garmin_files_df = garmin_files_df[garmin_files_df['yoda_path'].str.contains('(\\d{4}-\\d{2}\\.json)')]
garmin_files_df = garmin_files_df[garmin_files_df['yoda_path'].str.contains(data_file)]
garmin_files_df = garmin_files_df[~garmin_files_df['yoda_path'].str.contains('old')]


# use of capitals in the filenames are inconsistant so make lower
files_to_process = garmin_files_df['yoda_path']
print(files_to_process)

loaded_data = pd.DataFrame()

for json_file in files_to_process:

    print(json_file)

    file_name = os.path.split(json_file)[1]

    obj = IrodsPath(session, json_file).dataobject

    stream = obj.open('r')
    json_text = stream.read().decode()

    stream.close()

    # some files have an issue where the dicts are not properly enclosed in a list (an empty list is present at the end)
    try:
        data = pd.read_json(StringIO(json_text))
    
    except:
        print('exception')
        json_text = re.sub(r'\[\]$', r']', json_text)
        json_text = re.sub(r'^', r'[', json_text)

        data = pd.read_json(StringIO(json_text))

    data['file_name'] = file_name
    data['file_date'] = check_month

    loaded_data = pd.concat([loaded_data, data])

    # in order to deduplicate the dataframe with data, turn all columns to string
    # to avoid TypeError: unhashable type: 'dict'
    loaded_data = loaded_data.astype(str)

    loaded_data = loaded_data.drop_duplicates()

    # write the data to yoda processed folder
    date = datetime.today().strftime('%Y-%m-%d')

    # processed_dir = config['YODA_GARMIN_PROCESSED_DIR']

    # irods_save_path = IrodsPath(session, processed_dir + '/' + export_type + '_{}.csv'.format(date))

    # with irods_save_path.open('w') as new_obj:

    #     new_obj.write(loaded_data.to_csv(sep=';', index=False).encode())


counts = loaded_data[['userId', 'calendarDate']].drop_duplicates().groupby('userId').count().reset_index()

print(counts)

meetweek_participants_counts = (
    batch_sensor_aid_keylist
    .merge(counts, how='left', left_on='user_id', right_on='userId')
    .merge(garmin_credentials_mmweek.dropna(subset='user_id'), how='left', on='user_id')
)

meetweek_participants_counts = meetweek_participants_counts[
    ['Studienummer', 'random_nr', 'Naam', 'user_id', 'calendarDate', 'email', 'password']
    ]

outfile = f'garmin_counts_{check_month}.xlsx'
outdir = r"O:/DGK/IRAS/EEPI/Projects/Exposome-Panel Study/Datamanagement/study_admin_code/panel-study-monitoring/downloads"

print(f'output stored in "{outdir}"')

meetweek_participants_counts.to_excel(os.path.join(outdir, outfile), index=False)

# merge_garmin_exports(garmin_files_df, 'dailies')
# merge_garmin_exports(garmin_files_df, 'stress')
# merge_garmin_exports(garmin_files_df, 'pulseox')
# merge_garmin_exports(garmin_files_df, 'sleep')
# merge_garmin_exports(garmin_files_df, 'usermetric')
# merge_garmin_exports(garmin_files_df, 'epoch')
# merge_garmin_exports(garmin_files_df, 'bodycomposition')
# merge_garmin_exports(garmin_files_df, 'respiration')
