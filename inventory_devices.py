from api import MistAPIHandler
import excel

username = ''
password = ''
org_id = ''
handler = MistAPIHandler('usr_pw', {'username':username,'password':password})        
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