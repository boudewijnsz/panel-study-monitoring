## Panel sensor monitoring

This code checks for Sodaq sensor files in Yoda. It can be scheduled to run on 
a Surf Research Cloud VM every morning at 07:00. It needs a few import files,
all of which can be stored on Yoda to make it easier to develop on a local 
computer and run the scheduled script on the Surf Research Cloud VM.

The files should be stored in the Yoda folder research-panel-monitoring/source_files

### steps to follow
1. Make sure your Yoda password is stored in the file indicated in the .env file
on both your local computer and the SRC VM
2. modify the following paramaters in the .env file:

BATCH_NAME = the name of the batch, used for file naming
FILE_NAME_LDOT = this is the export csv file that is created by the script 
`participant_file_prep.py`. 

2. run the script `participant_file_prep.py`. This prepares the file with all
the variables required for the monitoring (IMEI codes, email address of participant etc.).
It only needs to be ran once. Run this on your local computer, it
uses files on the O: drive. The resulting overview is stored on Yoda so it can 
be read from the Surf Research Cloud VM. 
3. modify the following paramaters in the .env file:

BATCH_NAME = the name of the batch, used for file naming

FILE_NAME_LDOT = this is the export csv file that is created by the script 
`participant_file_prep.py`
