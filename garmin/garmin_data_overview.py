# -*- coding: utf-8 -*-
from pathlib import Path
import re
from datetime import datetime
from io import StringIO
import os
import pandas as pd
from dotenv import dotenv_values
from ibridges import search_data
from ibridges.interactive import Session
from ibridges import IrodsPath


# load the variables defined in the env file
config = dotenv_values("./.env")
print(config)
yoda_password = dotenv_values(config['YODA'])['YODA']

# set up ibridges session
env_file = Path.expanduser(Path('~')).joinpath(".irods", "irods_environment.json")
session = Session(env_file, password=yoda_password)

# create inventory of available files
garmin_path = config['YODA_GARMIN_SOURCE_DIR']
garmin_files = search_data(session, path=garmin_path, path_pattern="%")

garmin_files_df = pd.DataFrame({'yoda_path': [str(p) for p in garmin_files]})

# load all files of a particicular export
def merge_garmin_exports(garmin_files_df, export_type):
    """merges all files of a particular type and stores them in the processed folder
    export type is the part of the filename that indicates what data is in the file, e.g. 'Daily'"""

    # ignore files in the processed folder
    garmin_files_df = garmin_files_df[~garmin_files_df['yoda_path'].str.contains('processed')]

    # use of capitals in the filenames are inconsistant so make lower
    files_to_process = garmin_files_df[garmin_files_df['yoda_path'].str.lower().str.contains(export_type)]['yoda_path']

    loaded_data = pd.DataFrame()

    for file in files_to_process:

        print(file)

        file_name = os.path.split(file)[1]
        file_date = re.search('[0-9]{4}-[0-9]{2}-[0-9]{2}', file).group()

        obj = IrodsPath(session, file).dataobject

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
        data['file_date'] = file_date

        loaded_data = pd.concat([loaded_data, data])

        # in order to deduplicate the dataframe with data, turn all columns to string
        # to avoid TypeError: unhashable type: 'dict'
        loaded_data = loaded_data.astype(str)

        loaded_data = loaded_data.drop_duplicates()

        # write the data to yoda processed folder
        date = datetime.today().strftime('%Y-%m-%d')

        processed_dir = config['YODA_GARMIN_PROCESSED_DIR']

        irods_save_path = IrodsPath(session, processed_dir + '/' + export_type + '_{}.csv'.format(date))

        with irods_save_path.open('w') as new_obj:

            new_obj.write(loaded_data.to_csv(sep=';', index=False).encode())

    return loaded_data


merge_garmin_exports(garmin_files_df, 'daily')
merge_garmin_exports(garmin_files_df, 'stress')
merge_garmin_exports(garmin_files_df, 'pulseox')
merge_garmin_exports(garmin_files_df, 'sleep')
merge_garmin_exports(garmin_files_df, 'usermetric')
merge_garmin_exports(garmin_files_df, 'epoch')
merge_garmin_exports(garmin_files_df, 'bodycomposition')
merge_garmin_exports(garmin_files_df, 'respiration')
