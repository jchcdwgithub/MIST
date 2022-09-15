from api import MistAPIHandler
import inventory_devices
import re
import yaml
from file_ops import ExcelReader

with open('config.yml') as f:
    current_index = 0
    config_index = 0
    config_lines = f.read()
    yaml_str = ''
    site_match = re.compile(r'site:')
    num_matches = len(site_match.findall(config_lines))
    while current_index < num_matches:
        config_lines = config_lines.replace('site:', f'site{current_index}:',1)
        current_index += 1
    config = yaml.load(config_lines, Loader=yaml.Loader)

headers = []
config_sites = config['sites']
for item in config_sites['header_column_names']:
    headers.append(config_sites['header_column_names'][item].replace('\\n', '\n'))
excel_reader = ExcelReader(config_sites['ap_excel_file'])
values = excel_reader.extract_table_from_file(headers, dropset=[config_sites['dropna_header'].replace('\\n', '\n')], groupby=config_sites['groupby'].replace('\\n', '\n'), worksheet=config_sites['sheet_name'])
site_mac_name = inventory_devices.create_site_to_mac_dict(values)
smn_tuples = inventory_devices.convert_site_mac_dict_to_tuples(site_mac_name)

username = config['login']['username']
password = config['login']['password']
login_params = {'username':username, 'password':password}
handler = MistAPIHandler('usr_pw', login_params)
handler.save_org_id_by_name(config['org'])
handler.populate_site_id_dict()
site_name_to_id = handler.sites
name_association = inventory_devices.create_name_association_dict(config_sites)


assign_jsons = []
for site in smn_tuples:
    try:    
        assign_json = inventory_devices.create_assign_json(site, site_name_to_id, name_association=name_association) 
        assign_jsons.append(assign_json)
    except KeyError:
        pass

for assign_json in assign_jsons:
    success_filename = f'assigned_aps_{assign_json["site_id"]}.txt'
    error_filename = f'unassigned_aps_{assign_json["site_id"]}.txt'
    success = []
    error = []
    try:
        response = handler.assign_inventory_to_site(assign_json)
        success = response['success']
        error = response['error']
    except Exception as e:
        print(e)

    with open(success_filename, 'a+') as assigned_aps_f, open(error_filename, 'a+') as unassigned_aps_f:
        lines = []
        for ap_mac in success:
            lines.append(f'{ap_mac}\n')
        assigned_aps_f.writelines(lines)
        if len(error) > 0:
            for ap_mac in error:
                lines.append(f'{ap_mac}\n')
        unassigned_aps_f.writelines(lines)