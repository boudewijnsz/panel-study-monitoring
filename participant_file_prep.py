from pathlib import Path
import pandas as pd
from dotenv import dotenv_values
from ibridges import Session
from ibridges.path import IrodsPath
from ibridges import upload

# these two file paths need to be changed before each new measurement week
ldot_file_path = r"O:\DGK\IRAS\EEPI\Privacy\Exposome-Panel Study\Meetweken\Meetweken oktober 2025\MEMIC_Overview_Apparaatnummers deelnemers meetweek oktober 2025_20251013_21_08.csv"
garmin_file_path = r"O:\DGK\IRAS\EEPI\Privacy\Exposome-Panel Study\Meetweken\Meetweken oktober 2025\garmin_participants_okt_2025_linked.xlsx"

package_sending_date = '2025-10-10'

# load the variables defined in the env file
# config_path = r'O:\DGK\IRAS\EEPI\Projects\Exposome-Panel Study\Datamanagement\study_admin_code\panel-study-monitoring\.env'
config_path = Path(Path(__file__).parent, '.env')
config = dotenv_values(config_path)
yoda_password = dotenv_values(config['YODA'])['YODA']

env_file = Path.expanduser(Path('~')).joinpath(".irods", "irods_environment.json")
session = Session(irods_env=env_file, password=yoda_password)

# prepare the Ldot data
ldot_data = pd.read_csv(ldot_file_path, sep=';', dtype=str)

# this file contains everyone who was invited, filter only actual participants
ldot_data = ldot_data.loc[ldot_data['Deelname'] == 'Ja']

# remove the time indicator for the variable pakket verstuurd
# set manually at top of the script as this sometimes doesn't match Ldot
ldot_data['pakket verstuurd'] = package_sending_date

# merge the Garmin Access Token
garmin_data = pd.read_excel(garmin_file_path, dtype=str)
garmin_keylist_file = r"O:/DGK/IRAS/EEPI/Privacy/Exposome-Panel Study/Meetweken/ALGEMEEN/Gegevens voor Garmin met AID.xlsx"
garmin_keylist = pd.read_excel(garmin_keylist_file, dtype=str)

garmin_aid = (
    garmin_data
    .merge(garmin_keylist, how='left', on='random_nr')
    .filter(['AID', 'access token'])
    )

batch_sensor_aid_keylist = pd.merge(
    ldot_data,
    garmin_aid,
    how='left',
    left_on='Studienummer',
    right_on='AID'
)

batch_sensor_aid_keylist = batch_sensor_aid_keylist.fillna('').drop_duplicates()

# add GPS IMEI from key table
keylist_track_sensors = pd.read_excel('sodaq_sensors/TRACK_KoppelingBarcodeIMEI.xlsx', dtype=str)
batch_sensor_aid_keylist = batch_sensor_aid_keylist.merge(
    keylist_track_sensors, how='left', left_on='GPS', right_on='QR CODE'
    )

batch_sensor_aid_keylist = (
    batch_sensor_aid_keylist
    .rename(columns={'IMEI': 'GPS IMEI',
                    'Short code dynamisch': 'short_code_dynamisch',
                    'Short code statisch': 'short_code_statisch',
                    'access token': 'garmin_access_token'})
    )

batch_sensor_aid_keylist = batch_sensor_aid_keylist[
    ['Studienummer', 'Naam', 'Email', 'pakket verstuurd',
       'pakket retour', 'IMEI dynamisch', 'short_code_dynamisch', 
       'IMEI statisch', 'short_code_statisch', 'QR CODE', 'GPS IMEI',
       'garmin_access_token']
       ]

# store the file in Yoda
yoda_monitoring_dir = config['YODA_MONITORING_DIR']

keylist_path = Path(Path().resolve(), config['FILE_NAME_LDOT'])
batch_sensor_aid_keylist.to_csv(keylist_path, index=False, sep=';')

irods_path = IrodsPath(session, config['YODA_MMWEEK_DIR'], config['FILE_NAME_LDOT'])
print("writing output to yoda ")
upload(session, keylist_path, irods_path, overwrite=True)
