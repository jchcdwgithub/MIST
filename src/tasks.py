import inventory_devices
import re
import pandas
import os
from api import MistAPIHandler
from file_ops import ExcelReader, ConfigReader, ExcelWriter
from typing import List, Tuple, Dict

config_reader = ConfigReader('config.yml')
config = config_reader.extract_information_from_file()

class NameAssoc:

    config_sites:Dict
    name_association:Dict[str,str]

    def __init__(self, config:Dict):
        self.config_sites = config['sites']
    
    def get_data_structure(self) ->  Dict[str, str]:
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
        return self.name_association
    
    def __str__(self):
        return 'name_association'

class SiteMacName:

    values:pandas.DataFrame
    site_mac_name:Dict
    config_sites:Dict
    excel_reader:ExcelReader

    def __init__(self, config:Dict):
        self.config_sites = config['sites']
        self.excel_reader = ExcelReader(self.config_sites['ap_excel_file'])

    def get_data_structure(self) -> Dict:
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
                    print('Found invalid mac for ap {}: {}'.format(ap_name, ap_mac))
        return self.site_mac_name
    
    def _remove_floor_from_site_name(self, site:str) -> str:
        site_formats = ['Flr-\d+$', '\d(st|nd|rd|th) Flr']
        for site_format in site_formats:
            floor = re.compile(r''+site_format)
            floor_match = floor.search(site)
            if floor_match:
                start = floor_match.start()
                return site[:start-1]
        raise ValueError('Site does not conform to SITE Flr-xx format.')

    def __str__(self):
        return 'site_mac_name'

class AssignTask:

    def __init__(self, site_mac_name:Dict, site_name_to_id:Dict[str, str], name_association:Dict[str,str], handler:MistAPIHandler):
        self.smn = self._convert_site_mac_dict_to_tuples(site_mac_name)
        self.sn_id = site_name_to_id
        self.name_assoc = name_association
        self.handler = handler
        self.order = 0

    def perform_task(self) -> Dict[str, Dict[str, str]]:
        
        assign_jsons = []
        sites = {'task':'assign ap'}
        for site in self.smn:
            try:    
                assign_json = inventory_devices.create_assign_json(site, self.sn_id, name_association=self.name_assoc) 
                assign_jsons.append(assign_json)
            except KeyError:
                pass
        
        for assign_json,site in zip(assign_jsons, self.smn):
            sites[site[0]] = {'success':[], 'error':[]}
            print(f'assigning APs to site: {self.name_assoc[site[0]]}')
            try:
                response = self.handler.assign_inventory_to_site(assign_json)
                sites[site[0]]['success'] = response['success']
                sites[site[0]]['error'] = response['error']
            except Exception as e:
                print(e)
        return sites

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
        self.order = 1
    
    def perform_task(self) -> Dict[str, Dict[str, List[str]]]:
        id_to_name = {}
        results = {'task':'name ap'}
        for site in self.smn:
            print('naming APs')
            site_id = self.handler.sites[self.name_assoc[site]]
            results[site] = {'success':[], 'error':[]}
            try:
                site_devices = self.handler.get_site_devices(site_id)
            except Exception as e:
                print(e)
                exit()
            mac_to_id = {}
            for device in site_devices:
                mac_to_id[device['mac']] = device['id']
            id_to_name = {}
            site_aps = self.smn[site]
            for ap in site_aps:
                if ap in mac_to_id:
                 id_to_name[mac_to_id[ap]] = site_aps[ap]
            error = []
            success = []
            for device_id in id_to_name:
                try:
                    response = self.handler.config_site_device(site_id, device_id, {'name':id_to_name[device_id]})
                    success.append([response['name'], response['mac']])
                except Exception as e:
                    print(e)
                    error.append(id_to_name[device_id])
            results[site]['success'] = success
            results[site]['error'] = error
        return results

class TaskManager:

    task_datastructure = {
        'assign ap' : [NameAssoc, SiteMacName],
        'name ap' : [NameAssoc, SiteMacName],
    }

    def __init__(self, config:Dict = {}, handler:MistAPIHandler = None, writer:ExcelWriter = None):
        username = config['login']['username']
        password = config['login']['password']
        login_params = {
            'username':username,
            'password':password
            }
        self.config = config
        self.tasks = config['sites']['tasks']

        print('logging in...')
        self.handler = handler('usr_pw', login_params)
        self.writer = writer

        self.handler.save_org_id_by_name(config['org'])
        self.handler.populate_site_id_dict()

        self.site_name_to_id = self.handler.sites
        print('reading information from excel file...')
        self._create_data_structures()
        print('validating information...')
        self._validate_data_structures()

    def _create_data_structures(self):
        data_objects = [] 
        data_structures = {}
        for task in self.tasks:
            for object in self.task_datastructure[task]:
                if str(object) not in data_objects:
                    concrete_obj = object(self.config)
                    try:
                        data_structures[str(concrete_obj)] = concrete_obj.get_data_structure()
                    except Exception as e:
                        print(f'Failed in creating {str(object)} data structure: {e}. Aborting...')
                        exit()
        self.data_structures = data_structures
    
    def _validate_data_structures(self):
        for data_structure in self.data_structures:
            if data_structure == 'site_mac_name':
                validated_ds = self._validate_site_mac_name_ds(self.data_structures[data_structure])
                self.data_structures[data_structure] = validated_ds
                ds_without_unknown_sites = self._remove_unknown_sites(self.data_structures[data_structure])
                self.data_structures[data_structure] = ds_without_unknown_sites
            else:
                pass
    
    def _remove_unknown_sites(self, ds:Dict) -> Dict:
        ds_copy = ds.copy()
        for site in ds:
            if not site in self.data_structures['name_association']:
                ds_copy.pop(site)
        return ds_copy

    def _validate_site_mac_name_ds(self, ds:Dict) -> Dict:
        """ Remove devices that were already assigned to sites previously. """
        excel_base_name = '{}.xlsx'
        for site in ds:
            mist_site_name = self.data_structures['name_association'][site]
            site_id = self.site_name_to_id[mist_site_name]
            saved_filename = os.path.join(os.getcwd(), 'data', excel_base_name.format(site_id))
            if os.path.exists(saved_filename):
                    df = pandas.read_excel(saved_filename)
                    assigned_macs = df['mac'].values.tolist()
                    mac_to_name = ds[site]
                    mac_to_name_copy = mac_to_name.copy()
                    for mac in mac_to_name:
                        if mac in assigned_macs:
                            mac_to_name_copy.pop(mac)
                    ds[site] = mac_to_name_copy
            return ds

    def create_tasks(self):
        self.execute_queue = []
        for task in self.tasks:
            if task == 'assign ap':
                assign_task = AssignTask(self.data_structures['site_mac_name'], self.site_name_to_id, self.data_structures['name_association'], self.handler)
                self.execute_queue.append(assign_task)
            elif task == 'name ap':
                name_task = NameAPTask(self.data_structures['site_mac_name'], self.data_structures['name_association'], self.handler)
                self.execute_queue.append(name_task)
    
    def execute_tasks(self):
        self.results = []
        self.execute_queue.sort(key=lambda o: o.order)
        for task in self.execute_queue:
            result = task.perform_task()
            self.results.append(result)

    def save_success_configs_to_file(self):
        self.writer = self.writer(self.results, self.site_name_to_id, self.data_structures['name_association'])
        self.writer.write_success_configs_to_file()