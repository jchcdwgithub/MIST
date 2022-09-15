from api import MistAPIHandler
import inventory_devices
import re
import pandas
from file_ops import ExcelReader, ConfigReader
from typing import List, Tuple, Dict
from dataclasses import dataclass

config_reader = ConfigReader('config.yml')
config = config_reader.extract_information_from_file()

class NameAssoc:

    config_sites:Dict
    name_association:Dict[str,str]

    def __init__(self, config:Dict):
        self.config_sites = config['sites']
    
    def get_data_structure(self) -> Tuple[str, Dict[str, str]]:
        site_key_regex = re.compile(r'site\d+')
        name_association = {}
        for key in self.config_sites:
            if site_key_regex.match(key):
                site = self.config_sites[key]
                if 'excel_name' in site:
                    excel_name = site['excel_name']
                    name = site['name']
                    name_association[excel_name] = name
                else:
                    name = site['name']
                    name_association[name] = name
        self.name_association = name_association
        return ('name_association', self.name_association)

class SiteMacName:

    values:pandas.DataFrame
    site_mac_name:Dict
    config_sites:Dict
    excel_reader:ExcelReader

    def __init__(self, config:Dict):
        self.config_sites = config['sites']
        self.excel_reader = ExcelReader(config['ap_excel_file'])

    def get_data_structure(self) -> Tuple[str, Dict]:
        headers = []
        for item in self.config_sites['header_column_names']:
            headers.append(self.config_sites['header_column_names'][item].replace('\\n', '\n'))
        values = self.excel_reader.extract_table_from_file(headers, dropset=[self.config_sites['dropna_header'].replace('\\n', '\n')], groupby=self.config_sites['groupby'].replace('\\n', '\n'), worksheet=self.config_sites['sheet_name'])
        self.site_mac_name = {} 
        for name, group in values:
            try:
                name_wo_floor = self._remove_floor_from_site_name(name)
            except ValueError:
                name_wo_floor = name
            if name_wo_floor not in self.site_mac_name:
                self.site_mac_name[name_wo_floor] = {}
            for item in group.values:
                _, ap_name, ap_mac = item
                if inventory_devices.is_valid_mac(ap_mac):
                    self.site_mac_name[name_wo_floor][ap_mac.lower()] = ap_name
                else:
                    print('Found invalid mac for ap {}'.format(ap_name))
        return ('site_mac_name', self.site_mac_name)
    
    def _remove_floor_from_site_name(self, site:str) -> str:
        floor = re.compile(r'Flr-\d+$')
        floor_match = floor.search(site)
        if not floor_match:
            raise ValueError('Site does not conform to SITE Flr-xx format.')
        else:
            start = floor_match.start()
            return site[:start-1]

class TaskManager:

    task_datastructure = {
        'assign ap' : [NameAssoc, SiteMacName],
        'name ap' : [NameAssoc, SiteMacName],
    }

    def __init__(self, config:Dict):
        username = config['login']['username']
        password = config['login']['password']
        login_params = {
            'username':username,
            'password':password
            }
        self.config = config
        self.handler = MistAPIHandler('usr_pw', login_params)
        self.handler.save_org_id_by_name(config['org'])
        self.handler.populate_site_id_dict()
        self.site_name_to_id = self.handler.sites

    def create_data_structures(self):
        pass

class AssignTask:
    def __init__(self, site_mac_name:Dict, site_name_to_id:Dict[str, str], name_association:Dict[str,str], handler:MistAPIHandler):
        self.smn = self._convert_site_mac_dict_to_tuples(site_mac_name)
        self.sn_id = site_name_to_id
        self.name_assoc = name_association
        self.handler = handler

    def perform_task(self) -> Tuple[List, List]:
        
        assign_jsons = []
        for site in self.smn:
            try:    
                assign_json = inventory_devices.create_assign_json(site, self.sn_id, name_association=self.name_assoc) 
                assign_jsons.append(assign_json)
            except KeyError:
                pass

        for assign_json in assign_jsons:
            success_filename = f'assigned_aps_{assign_json["site_id"]}.txt'
            error_filename = f'unassigned_aps_{assign_json["site_id"]}.txt'
            success = []
            error = []
            try:
                response = self.handler.assign_inventory_to_site(assign_json)
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
        
        return success, error

    def _convert_site_mac_dict_to_tuples(self, site_mac_name:Dict) -> Tuple:
        sites_to_aps_tuples = []
        for site in site_mac_name:
            current_tuple = (site, site_mac_name[site])
            sites_to_aps_tuples.append(current_tuple)
        return sites_to_aps_tuples

class NameAPTask:

    def __init__(self, site_mac_name:Dict[str, Dict[str,str]], name_association:Dict[str,str], handler:MistAPIHandler):
        self.smn = site_mac_name
        self.name_assoc = name_association
        self.handler = handler
    
    def perform_task(self) -> Tuple[List, List]:
        try:
            id_to_name = {}
            for site in self.smn:
                site_id = self.handler.sites[self.name_assoc[site]]
                site_devices = self.handler.get_site_devices(site_id)
                mac_to_id = {}
                for device in site_devices:
                    mac_to_id[device['mac']] = device['id']
                id_to_name = {}
                site_aps = self.smn[site]
                for ap in site_aps:
                    if ap in mac_to_id:
                     id_to_name[mac_to_id[ap]] = site_aps[ap]
                failed = []
                for device_id in id_to_name:
                    json_response = self.handler.config_site_device(site_id, device_id, {'name':id_to_name[device_id]})
        except Exception as e:
            print(e)