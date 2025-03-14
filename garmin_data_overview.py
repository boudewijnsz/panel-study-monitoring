# -*- coding: utf-8 -*-
import re
from shutil import copy2
from io import StringIO
import os
import pandas as pd
import chardet
from dotenv import dotenv_values

config = dotenv_values(".env")

# thi
# s function does a few things:
# - combine the data for each type of Garmin export
# - place a copy of files that couldn't be parsed to a separate folder to be inspected

parsing_errors_dir = 

def merge_data(type):

    df_out = pd.DataFrame()
    
    for file in os.listdir(json_dir):
    
        if file.endswith('json') and type in file.lower():

            file_path = os.path.join(json_dir, file)
    
            with open(file_path, 'rb') as f:
                # encoding differes per file and is not utf-8 so determine first
                enc = chardet.detect(f.read())
            try:
                data = pd.read_json(file_path, encoding=enc['encoding'])
                
                data['filename'] = file

                df_out = pd.concat([df_out, data])
                
            except Exception as e: 
                # some files have an issue where the dicts are not properly enclosed in a list (an empty list is present at the end)

                try: 
                    with open(file_path, 'r') as f:
                        raw_json = f.read()

                    raw_json = re.sub(r'\[\]$', r']', raw_json)
                    raw_json = re.sub(r'^', r'[', raw_json)

                    data = pd.read_json(StringIO(raw_json))

                    data['filename'] = file    
                    df_out = pd.concat([df_out, data])

                except:
                    print(file, e)
                    copy2(file_path, parsing_errors_dir)


    df_out.drop_duplicates().to_csv(os.path.join(csv_dir, type + '.csv'), sep=';')

    return df_out

# bodycomposition = merge_data('bodycomposition')
daily = merge_data('daily')
# epoch = merge_data('epoch')
# pulseox = merge_data('pulseox')
# respiration = merge_data('respiration')
# sleep = merge_data('sleep')
# stress = merge_data('stress')
# usermetric = merge_data('usermetric')
