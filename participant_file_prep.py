from pathlib import Path
import pandas as pd
from dotenv import dotenv_values
from ibridges import Session
from ibridges.path import IrodsPath
from ibridges import upload

# these two file paths need to be changed before each new measurement week
ldot_file_path = r"O:\DGK\IRAS\EEPI\Privacy\Exposome-Panel Study\Meetweken\Meetweken november 2026\MEMIC_Overview_Apparaatnummers meetweek november 2026_20261116_12_09.xlsx"
garmin_file_path = r"O:\DGK\IRAS\EEPI\Privacy\Exposome-Panel Study\Meetweken\Meetweken november 2026\garmin_rand_nrs_meetweek_november_linked_2026.xlsx"
# the overview apparaatnummers needs to be cleaned up because not all people
# in there actually paricipate if some we have too many applicants
actual_participants_path = r"O:\DGK\IRAS\EEPI\Privacy\Exposome-Panel Study\Meetweken\Meetweken november 2026\adressen_deelnemers_november_2026_opgeschoond.xlsx"

actual_participants = pd.read_excel(actual_participants_path, dtype='str')

package_sending_date = '2026-11-13'

# load the variables defined in the env file
# config_path = r'O:\DGK\IRAS\EEPI\Projects\Exposome-Panel Study\Datamanagement\study_admin_code\panel-study-monitoring\.env'
config_path = Path(Path(__file__).parent, '.env')
config = dotenv_values(config_path)
yoda_password = dotenv_values(config['YODA'])['YODA']

env_file = Path.expanduser(Path('~')).joinpath(".irods", "irods_environment.json")
session = Session(irods_env=env_file, password=yoda_password)

# prepare the Ldot data
ldot_data = pd.read_excel(ldot_file_path, dtype=str)

ldot_data = ldot_data[ldot_data['studienummer'].isin(actual_participants['studienummer'])]

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
    .filter(['AID', 'User ID'])
    )

batch_sensor_aid_keylist = pd.merge(
    ldot_data,
    garmin_aid,
    how='left',
    left_on='studienummer',
    right_on='AID'
)

batch_sensor_aid_keylist = batch_sensor_aid_keylist.fillna('').drop_duplicates()

# add GPS IMEI from key table
keylist_track_sensors = pd.read_excel('sodaq_sensors/TRACK_KoppelingBarcodeIMEI.xlsx', dtype=str)
batch_sensor_aid_keylist = batch_sensor_aid_keylist.merge(
    keylist_track_sensors, how='left', left_on='gps', right_on='QR CODE'
    )

batch_sensor_aid_keylist = (
    batch_sensor_aid_keylist
    .rename(columns={'gps': 'GPS IMEI',
                    'short code dynamisch': 'short_code_dynamisch',
                    'short code statisch': 'short_code_statisch'})
    )

batch_sensor_aid_keylist = batch_sensor_aid_keylist[
    ['studienummer', 'naam', 'email', 'pakket verstuurd',
       'pakket retour', 'imei dynamisch', 'short_code_dynamisch', 
       'imei statisch', 'short_code_statisch', 'QR CODE', 'GPS IMEI',
       'User ID']
       ]

# store the file in Yoda
yoda_monitoring_dir = config['YODA_MONITORING_DIR']

keylist_path = Path(Path().resolve(), config['FILE_NAME_LDOT'])
batch_sensor_aid_keylist.to_csv(keylist_path, index=False, sep=';')

irods_path = IrodsPath(session, config['YODA_MMWEEK_DIR'], config['FILE_NAME_LDOT'])
print("writing output to yoda ")
upload(keylist_path, irods_path, overwrite=True)
