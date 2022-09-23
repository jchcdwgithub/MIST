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
    site_formats = ['Flr-\d+$', '\d(st|nd|rd|th) Flr']
    for site_format in site_formats:
        floor = re.compile(r''+site_format)
        floor_match = floor.search(site)
        if floor_match:
            start = floor_match.start()
            return site[:start-1]
    raise ValueError('Site does not conform to SITE Flr-xx format.')

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
    mac_regex = '^[a-fA-F0-9]{2}' + f'({delimiter}[a-fA-F0-9]' + '{2}){5}$'
    mac_pattern = re.compile(r''+mac_regex)
    if mac_pattern.match(mac):
        return True
    else:
        return False 

def create_assigned_aps_txt(assign_jsons:List[Dict]):
    for assign_json in assign_jsons:
        csv_filename = f'assigned_aps_{assign_json["site_id"]}.txt'
        with open(csv_filename, 'a+') as assigned_aps_f:
            lines = []
            for ap_mac in assign_json['macs']:
                lines.append(f'{ap_mac}\n')
            assigned_aps_f.writelines(lines)

def create_site_to_mac_dict(values:pandas.DataFrame) -> Dict:
    site_mac_name = {} 
    for name, group in values:
        try:
            name_wo_floor = remove_floor_from_site_name(name)
        except ValueError:
            name_wo_floor = name
        if name_wo_floor not in site_mac_name:
            site_mac_name[name_wo_floor] = {}
        for item in group.values:
            _, ap_name, ap_mac = item
            if is_valid_mac(ap_mac):
                site_mac_name[name_wo_floor][ap_mac.lower()] = ap_name
            else:
                print('Found invalid mac for ap {}'.format(ap_name))
    return site_mac_name

def convert_site_mac_dict_to_tuples(site_mac_name:Dict) -> Tuple:
    sites_to_aps_tuples = []
    for site in site_mac_name:
        current_tuple = (site, site_mac_name[site])
        sites_to_aps_tuples.append(current_tuple)
    return sites_to_aps_tuples

def get_site_names_from_config_sites(config_sites:Dict) -> List[str]:
    site_key_regex = re.compile(r'site\d+')
    site_names = []
    for key in config_sites:
        if site_key_regex.match(key):
            site_names.append(config_sites[key]['name'])
    return site_names

def create_name_association_dict(config_sites:Dict) -> Dict[str,str]:
    site_key_regex = re.compile(r'site\d+')
    name_association = {}
    for key in config_sites:
        if site_key_regex.match(key):
            if 'excel_name' in config_sites[key]:
                excel_name = config_sites[key]['excel_name']
                name = config_sites[key]['name']
                name_association[excel_name] = name
            else:
                name = config_sites[key]['name']
                name_association[name] = name
    return name_association