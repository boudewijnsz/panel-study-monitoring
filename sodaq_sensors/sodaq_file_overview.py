#!/usr/bin/env python
# %%
# -*- coding: utf-8 -*-
import sys
import os
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import dotenv_values
import numpy as np
from ibridges import Session
from ibridges.search import search_data
from ibridges.path import IrodsPath
from ibridges import upload

# load the variables defined in the env file
config_path = Path(Path(__file__).parent.parent, '.env')
config = dotenv_values(config_path)
yoda_password = dotenv_values(config['YODA'])['YODA']

# start an ibridges session to create the overview of all the files present in Yoda
env_file = Path.expanduser(Path('~')).joinpath(".irods", "irods_environment.json")
session = Session(irods_env=env_file, password=yoda_password)

# %%
# name of the file exported from Ldot
file_name_ldot = config['FILE_NAME_LDOT']

# name of the batch (e.g. for March 2025 'march_2025')
batch_name = 'may_2025'

# %%
# to discuss:
# - take earliers data when there are multiple or actual date per participant?
# - same for batch end date

# %%
# first run download the overview from Ldot that contains the AID and sending dates for the sensors

batch_sensor_aid_keylist = pd.read_excel(file_name_ldot, dtype=str)

# add the GPS sensor IMEI
track_key_table = config['TRACK_KEY_TABLE']
keylist_track_sensors = pd.read_excel(track_key_table, dtype=str)
batch_sensor_aid_keylist = pd.merge(batch_sensor_aid_keylist, keylist_track_sensors, how='left', on='QR CODE')
batch_sensor_aid_keylist = batch_sensor_aid_keylist.rename(columns={'IMEI': 'GPS IMEI'})
batch_sensor_aid_keylist = batch_sensor_aid_keylist[
    ['Studienummer', 'Naam', 'Email', 'pakket verstuurd',
       'pakket retour', 'IMEI dynamisch', 'short_code_dynamisch', 
       'IMEI statisch', 'short_code_statisch', 'QR CODE', 'GPS IMEI']
       ]


# modify data types to ease adding missing values
batch_sensor_aid_keylist['GPS IMEI'] = batch_sensor_aid_keylist['GPS IMEI'].astype(str)

batch_sensor_aid_keylist['pakket verstuurd'] = pd.to_datetime(batch_sensor_aid_keylist['pakket verstuurd'], dayfirst=True)
batch_sensor_aid_keylist['pakket retour'] = pd.to_datetime(batch_sensor_aid_keylist['pakket retour'], dayfirst=True)

batch_sensor_aid_keylist = batch_sensor_aid_keylist.drop_duplicates()

# %%
# set the sending date for the current batch. Only the files in Yoda sent
# after this date and before today's date are taken into account.
# sending dates are available in the Ldot export but sometimes there are multiple dates, take the earliest
# batch_start_date = batch_sensor_aid_keylist['pakket verstuurd'].str.extract('([0-9]{2}-[0-9]{1,2}-[0-9]{4})').drop_duplicates().dropna().min()
today = datetime.today()

# if sensor has not been returned yet/return date is empty, use today's date
batch_sensor_aid_keylist['pakket retour'] = batch_sensor_aid_keylist['pakket retour'].fillna(today)


batch_sensor_aid_keylist

# %%
# generate an overview of all available data on Yoda
def get_yoda_files(yoda_path): 

    print("searching {}".format(yoda_path))
    
    irods_path = IrodsPath(session, session.home)

    yoda_dir = irods_path.joinpath(yoda_path)

    all_yoda_files = search_data(session, path=str(yoda_dir), path_pattern="%")

    all_yoda_files_df = pd.DataFrame({'file_path': all_yoda_files})
    all_yoda_files_df['file_path'] = all_yoda_files_df['file_path'].astype(str)

    all_yoda_files_df['file_date'] = all_yoda_files_df['file_path'].str.extract(r'([0-9]{4}\/[0-9]{2}\/[0-9]{2}(?=\/))')
    all_yoda_files_df['file_date'] = pd.to_datetime(all_yoda_files_df['file_date'], format='%Y/%m/%d')
    all_yoda_files_df['IMEI'] = all_yoda_files_df['file_path'].str.extract(r'([0-9]{15})(?=\.txt)')

    all_yoda_files_df.dropna(subset='IMEI', inplace=True)
    
    return all_yoda_files_df


# create an overview of all available files in Yoda
air_files = get_yoda_files('research-expanse-sodaq-nl/SODAQ AIR')
track_files = get_yoda_files('research-expanse-sodaq-nl/SODAQ TRACK')


# %%
# declare the functions to map the data

def merge_sensor_data(sensor_type):
    
    if sensor_type not in ['static', 'dynamic', 'gps']:
        print('Sensor type should be "static" or "dynamic", "gps"')
        return
    if sensor_type == 'gps':
        sensor_files = track_files
    else:
        sensor_files = air_files
    
    sensor_columns = {'static': ['IMEI statisch', 'short_code_statisch'],
                      'dynamic': ['IMEI dynamisch', 'short_code_dynamisch'],
                      'gps': ['GPS IMEI', 'QR CODE']}
    
    sensor_column = sensor_columns[sensor_type]
    
    sensor_data = (
        batch_sensor_aid_keylist[['Studienummer', 'Naam', 'Email', 'pakket verstuurd', 'pakket retour'] + sensor_column]
        .merge(sensor_files, how='left', left_on=sensor_column[0], right_on='IMEI')
        )
    
    return sensor_data
    

def count_sensor_files(sensor_files, sensor_type):
    
    if sensor_type == 'static':
        
        imei_column = ['IMEI statisch', 'short_code_statisch']
        
    elif sensor_type == 'dynamic':
    
        imei_column = ['IMEI dynamisch', 'short_code_dynamisch']
        
    elif sensor_type == 'gps':
        
        imei_column = ['GPS IMEI', 'QR CODE']
        
    else:
        print('Sensor type should be "static", "dynamic" or "gps"')
        return
            

    count_sensor_files = (
        sensor_files
        .loc[((sensor_files['file_date'] >= pd.to_datetime(sensor_files['pakket verstuurd'])) &
              (sensor_files['file_date'] < pd.to_datetime(sensor_files['pakket retour'])))]
        .filter(['Studienummer', 'Email', 'file_path'] + imei_column)
        .groupby(['Studienummer', 'Email'] + imei_column)
        .count()
        .reset_index()
        .assign(sensor_type = sensor_type)
        .rename(columns={'file_path': 'total_files_present',
                         imei_column[0]: 'IMEI',
                         imei_column[1]: 'short_code'})
        )
    
    # sometimes files are missing completely so merge back to original list of
    # IMEIS
    batch_IMEIs =  batch_sensor_aid_keylist[
        ['Studienummer', 'Email'] + imei_column
    ]

                      
    counted_IMEIs = count_sensor_files['IMEI']
    
    missing_IMEIs = (
        batch_IMEIs
        .merge(counted_IMEIs, how='outer', left_on=imei_column[0], right_on='IMEI')
        )
    
   
    missing_IMEIs = missing_IMEIs[missing_IMEIs['IMEI'].isna()].drop('IMEI', axis=1).rename(columns={imei_column[0]: 'IMEI',
                                                                                                     imei_column[1]: 'short_code'})

    missing_IMEIs['sensor_type'] = sensor_type
    missing_IMEIs['total_files_present'] = 0

    count_sensor_files = pd.concat([count_sensor_files, missing_IMEIs])
    
    return count_sensor_files


def get_sensor_dates(sensor_files, sensor_type):
    
    if sensor_type not in ['static', 'dynamic', 'gps']:
        
        print('Sensor type should be "static" or "dynamic"')
        return
    
    all_dates = pd.DataFrame({
        'date':
        pd.date_range(sensor_files['pakket verstuurd'].dt.date.min(), sensor_files['pakket retour'].dt.date.max()).to_list()
        })
    
    sensor_dates = (
        sensor_files
        .merge(all_dates, how='right', left_on='file_date', right_on='date')
        )
    
    sensor_dates = (
        sensor_dates
        .loc[((sensor_dates['date'] >= sensor_dates['pakket verstuurd']) &
                (sensor_dates['date'] < sensor_dates['pakket retour']))]
        .filter(['Studienummer', 'date'])
        .assign(file_date = sensor_dates['date'].astype('string'))
        .assign(file_available = 'yes')
        .assign(sensor_type = sensor_type)
        .drop_duplicates()
        .pivot(columns='file_date', index=['Studienummer', 'sensor_type'], values='file_available')
        .reset_index()
        )
    
    return sensor_dates

# %%
print('processing gps')
gps_sensors = merge_sensor_data('gps')
gps_sensors_count = count_sensor_files(gps_sensors, 'gps')
gps_sensors_count_dates = get_sensor_dates(gps_sensors, 'gps')

print('processing static sensors')
static_air_sensors = merge_sensor_data('static')
static_air_sensors_count = count_sensor_files(static_air_sensors, 'static')
static_air_sensors_count_dates = get_sensor_dates(static_air_sensors, 'static')

print('processing dynamic sensors')
dynamic_air_sensors = merge_sensor_data('dynamic')
dynamic_air_sensors_count = count_sensor_files(dynamic_air_sensors, 'dynamic')
dynamic_air_sensors_count_dates = get_sensor_dates(dynamic_air_sensors, 'dynamic')

print('creating overview')
gps_overview = gps_sensors_count.merge(gps_sensors_count_dates, how='left', on=['Studienummer', 'sensor_type'])
static_overview = static_air_sensors_count.merge(static_air_sensors_count_dates, how='left', on=['Studienummer', 'sensor_type'])
dynamic_overview = dynamic_air_sensors_count.merge(dynamic_air_sensors_count_dates, how='left', on=['Studienummer', 'sensor_type'])


# create the file with the full overview
overview_static_dynamic_gps = pd.concat(
    [static_overview, 
     dynamic_overview,
     gps_overview]).sort_values(['Studienummer', 'sensor_type'])

# add garmin data, these have been produced by script garmin_stats.py
garmin_data_path = Path(
    Path(__file__).resolve().parent.parent, 'downloads', 'data_daily_hr_hist.csv'
    )

garmin_data = pd.read_csv(garmin_data_path, 
                          dtype={'Studienummer': str,
                                 'date': str,
                                 'measurements': 'Int32'})

# count the number of days with garmin data. The original data shows recordings
# per hour so need to do some grouping
garmin_data_daily = (
    garmin_data
    .groupby(['Studienummer', 'date'], dropna=False)['measurements']
    .sum()
    .reset_index()
    )


garmin_data_daily['measurements'] = np.where(
    garmin_data_daily['measurements'] >= 1,
    1,
    0
)

# split the data so that when concatenating data, also the participants
# without Garmin data get a Garmin row in the overview
no_garmin_data = (
    garmin_data_daily[garmin_data_daily['date'].isna()]
    .assign(sensor_type = 'garmin')
    .assign(total_files_present = 0)
    .drop(['date', 'measurements'], axis=1)
    )

garmin_data_present = garmin_data_daily.dropna(subset=['date', 'Studienummer'])

garmin_data_daily_pivot = (
    garmin_data_present
    .assign(file_date = garmin_data_daily['date'].astype('string'))
    .rename(columns={'measurements': 'total_files_present'})
    .assign(files_present = np.where(garmin_data_present['measurements'] >= 1,
                                     'yes',
                                     ''))
    .pivot(columns='date', index=['Studienummer', 'total_files_present'], 
           values='files_present')
    .reset_index()
    .assign(sensor_type = 'garmin')
    )

garmin_data_daily_pivot = pd.concat([no_garmin_data, garmin_data_daily_pivot])

overview_static_dynamic_gps = pd.concat(
    [overview_static_dynamic_gps, garmin_data_daily_pivot]
    ).sort_values(['Studienummer', 'sensor_type'])

# Garmin measurements can start before sensor measurements which means the order
# of columns is not correct (garmin columns are added at the end). Reorder date
# columns
overview_columns = overview_static_dynamic_gps.columns
overview_date_columns = [c for c in overview_columns if re.match('\\d{4}', c)]
overview_date_columns.sort()
overview_non_date_columns = [c for c in overview_columns if not re.match('\\d{4}', c)]

overview_static_dynamic_gps = overview_static_dynamic_gps[
    overview_non_date_columns + overview_date_columns
]

overview_static_dynamic_gps.dropna(subset=['Studienummer'], inplace=True)

overview_static_dynamic_gps.drop_duplicates(inplace=True)
print('overview completed')

date_today = datetime.today().strftime('%Y-%m-%d')

# %%
# write the output file
overview_path = Path(Path().resolve(), "overview_sensor_files_batch_{}.xlsx".format(batch_name))

writer = pd.ExcelWriter(overview_path, engine='xlsxwriter')

overview_static_dynamic_gps.to_excel(writer, sheet_name='Sheet1', index=False)

workbook = writer.book

red = workbook.add_format({'bg_color': '#ffc7ce'})
green = workbook.add_format({'bg_color': '#c6efce'})

worksheet = writer.sheets['Sheet1']

# because the number of columns varies whether name is in there, dynamically
# check which column to color first
date_cols = [ c for c in overview_static_dynamic_gps.columns if re.match('[0-9]{4}-[0-9]{2}-[0-9]{2}', c)]
first_date_col = date_cols[0]

# still finish later

first_row = 1
first_col = 4
last_row = overview_static_dynamic_gps.shape[0]
last_col = overview_static_dynamic_gps.dropna(axis=1, how='all').shape[1]

worksheet.conditional_format(first_row, first_col, last_row, last_col,
                             {'type': 'cell',
                              'criteria': 'equal to',
                              'value': '"yes"',
                             'format': green})

worksheet.conditional_format(first_row, first_col, last_row, last_col,
                              {'type': 'blanks',
                              'format': red})



worksheet.autofit()

writer.close()


# write the file to the Yoda monitoring folder

yoda_monitoring_dir = config['YODA_MONITORING_DIR']

irods_path = IrodsPath(session, '~', yoda_monitoring_dir)
print("writing output to yoda ")
upload(session, overview_path, irods_path, overwrite=True)

session.close()

# %%
