REM this file can be used to upload all necessary files to SRC

REM Garmin key table
scp "O:\DGK\IRAS\EEPI\Privacy\Exposome-Panel Study\Meetweken\Accounts_Garmins_deelnemers_meetweken.xlsx" zboudewijn@145.38.193.9:data/automation_server/panel-study-monitoring/source_data/Accounts_Garmins_deelnemers_meetweken.xlsx  

REM Yoda pw
scp "C:\Users\boude004\.irods\.yoda" zboudewijn@145.38.193.9:/home/zboudewijn/.irods/.yoda

REM deelnemer overview
scp "O:\DGK\IRAS\EEPI\Privacy\Exposome-Panel Study\Meetweken\Meetweken mei 2025\panel_monitoring_overview_may_2025.xlsx" zboudewijn@145.38.193.9:/data/automation_server/panel-study-monitoring/source_data/panel_monitoring_overview_may_2025.xlsx