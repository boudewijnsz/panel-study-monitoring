#!/bin/sh
# garmin file processing
/home/zboudewijn/.pyenv/shims/python /home/zboudewijn/data/automation_server/panel-study-monitoring/garmin/garmin_data_overview.py > /home/zboudewijn/data/automation_server/garmin_overview_log.txt 2>&1

# garmin stats
/home/zboudewijn/.pyenv/shims/python /home/zboudewijn/data/automation_server/panel-study-monitoring/garmin/garmin_stats.py > /home/zboudewijn/data/automation_server/garmin_stats_log.txt 2>&1

# sodaq sensor overview
/home/zboudewijn/.pyenv/shims/python /home/zboudewijn/data/automation_server/panel-study-monitoring/sodaq_sensors/sodaq_file_overview.py > /home/zboudewijn/data/automation_server/sodaq_overview_log.txt 2>&1
