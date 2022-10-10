# Mist Config Automator

This is a script that automates Mist configuration.

## Installation

Download the project to your local environment and navigate into the MIST folder.

You can then download the dependencies that the script needs with:

pip install -r requirements.txt

## Supported Configuration Tasks:

Currently there are four tasks that are supported. They are:

1. assign ap
2. name ap
3. rename esx ap
4. create per floor esx files

The exact names listed above should be included in the config yaml file under sites. (See usage for more information.)

## Usage

The script is currently written to read the AP installation excel file that was created for Mist AP installers. All information that the script uses lives in the config yaml file, currently found under the main folder. An example file can be found in the examples folder included with this project.

### The config file

The config.yml file contains a few key pieces of information:

#### org
The name of the organization that you're pushing configuration to. This must match the Mist dashboard name exactly.
#### sites
sites: This contains the list of sites that you want to configure and also other information for those sites, like the tasks you'd like to perform on those sites. Here's a breakdown of the attributes in the sites section:
##### ap_excel_file
This is the path, relative to the MIST folder or an absolute path to where the AP Installation excel sheet is.
##### sheet_name
There are multiple sheets in the AP Installation file. The name of the sheet where the configuration information sheet must be specified.
##### header_column_names
The names of the columns that contain the configuration information. There are three that are required for the current tasks:
###### ap_name
The column name that contains the AP name information.
###### ap_mac
The column name that contains the AP MAC information.
###### site_name
The column name that contains the Site name information.
###### note
If you are just planning on using the AP installation excel sheet as is then none of this information needs to be changed from the example config file.
##### dropna_header
Currently set to the AP MAC column. Any row with a MAC that isn't filled in will not be included in the configuration push.
##### groupby
Currently set to the Site name. Configuration is grouped by site currently.
##### site
This contains the name of the site that you want to configure. There is a potential difference between the site name configured in the Mist dashboard and the name found in the AP Installation excel file. The script needs to know how to associate those two names:
###### name 
The site name as configured in the Mist dashboard.
###### excel_name
The site name found in the AP Installation excel file. This is the name without the floor suffix.
##### tasks
This is the list of configuration tasks that you'd like to perform against the sites defined.
##### login
This section contains the information that you need to authenticate against the Mist dashboard:
###### username
Your username
###### password
Your password

After defining the config.yml file, you can run the script. On the CLI type:

python mist_helper.py