from api import MistAPIHandler
import excel
import pandas
import re
from typing import List, Dict, Tuple

def inventory_devices(handler:MistAPIHandler, org_id:str):
    try:
        print('Gathering inventory...')
        response_json = handler.get_inventory(org_id)
        print('Inventory gathered.')
        sites = {}
        devices = [['NAME', 'MODEL', 'MAC', 'SITE', 'CONNECTED']]
        print('Populating tables...')
        for device in response_json:
            device_siteid = device['site_id']
            if device_siteid is not None:
                if device_siteid not in sites:
                    site_response = handler.get_sites(org_id)
                    for site in site_response:
                        if site['id'] == device_siteid:
                            sites[device_siteid] = site['name']
                device['site'] = sites[device_siteid]
            else:
                device['site'] = ''
            devices.append([device['name'],device['model'],device['mac'],device['site'],'UP' if device['connected'] else 'DOWN'])
        print('Tables populated.')
        tables = {'APs' : [devices]}
        print('Writing to excel file...')
        excel.write_tables_to_excel_workbook(tables)
        print('Done.')
    except Exception as e:
        print(e)

def create_assign_json_with_ap_macs(site_id:str, ap_macs:List) -> Dict:
    
    assign_json = {
        'op' : 'assign',
        'site_id' : site_id,
        'macs' : [],
        'no_reassign' : False
    }
    assign_json['macs'] = ap_macs
    return assign_json

def create_site_to_ap_name_mac_from_dataframe(dataframe:pandas.DataFrame, header_names:List[str]) -> Dict:
    """ 
        header_names is dependent on the data that the dataframe pulled from and should be something like ['site', 'ap name', 'ap mac']
        It's expected that the dataframe has dropped the all rows with ap mac == na
    """
    #first header should be site name
    values = dataframe.loc[:,header_names].groupby(header_names[0])
    site_mac_name = {}
    for name, group in values:
        site_mac_name[name] = {}
        for item in group.values:
            _, ap_name, ap_mac = item
            site_mac_name[name][ap_mac.lower()] = ap_name
    return site_mac_name

def remove_floor_from_site_name(site:str) -> str:
    floor = re.compile(r'Flr-\d+$')
    floor_match = floor.search(site)
    if not floor_match:
        raise ValueError('Site does not conform to SITE Flr-xx format.')
    else:
        start = floor_match.start()
        return site[:start-1]

def create_assign_json(site:Tuple[str, Dict[str, str]], site_name_to_id:Dict[str, str], name_association:Dict[str, str] = None) -> Dict:
    """
        param: site is a dictionary of name to a list of dictionaries with ap macs as keys and ap names as values.
        param: site_name_to_id is a dictionary of site names to site ids
        param: name_association is a dictionary of name to site name. If there is a difference between the naming on the input file and 
               the site name in the dashboard, this must be included.

        returns: the assign json file with the site_id and macs fields populated.
    """

    assign_json = { 
        'op' : 'assign',
        'site_id' : '',
        'macs' : [],
        'no_reassign' : False
    }

    site_name, site_aps = site

    if name_association:
        if name_association[site_name] in site_name_to_id:
            assign_json['site_id'] = site_name_to_id[name_association[site_name]]
        else:
            raise KeyError('The site name is either mistyped or the site doesn\'t exist in this organization')
    else:
        assign_json['site_id'] = site_name
        
    for ap_mac in site_aps:
        assign_json['macs'].append(ap_mac)

    return assign_json

def remove_invalid_macs(macs:List[str], delimiter:str = '') -> List[str]:
    base_match_string = '^[a-fA-F0-9]{2}' + f'({delimiter}[a-fA-F0-9]'
    match_string = base_match_string + '{2}){5}$'
    mac_pattern = re.compile(r''+match_string)
    valid_macs = []
    for mac in macs:
        if mac_pattern.match(mac):
            valid_macs.append(mac)
    return valid_macs

def is_valid_mac(mac:str, delimiter:str = '') -> bool:
    base_match_string = '^[a-fA-F0-9]{2}' + f'({delimiter}[a-fA-F0-9]'
    match_string = base_match_string + '{2}){5}$'
    mac_pattern = re.compile(r''+match_string)
    if mac_pattern.match(mac):
        return True
    else:
        return False 