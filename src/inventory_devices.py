from api import MistAPIHandler
import excel
import pandas
from typing import List, Dict

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