import inventory_devices
import re
import pandas
import os
import sys
from api import MistAPIHandler
from file_ops import EkahauWriter, ExcelReader, ConfigReader, ExcelWriter
from typing import List, Tuple, Dict

#suppress warnings from writing to ekahau file
if not sys.warnoptions:
    import warnings
    warnings.simplefilter('ignore')

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
        header_items = ['site_name', 'ap_name', 'ap_mac']
        for item in header_items:
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
                if self.is_valid_mac(ap_mac):
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

    def is_valid_mac(self, mac:str, delimiter:str = '') -> bool:
        mac_regex = '^[a-fA-F0-9]{2}' + f'({delimiter}[a-fA-F0-9]' + '{2}){5}$'
        mac_pattern = re.compile(r''+mac_regex)
        if mac_pattern.match(mac):
            return True
        else:
            return False 

    def __str__(self):
        return 'site_mac_name'

class SiteMac:

    site_to_mac:Dict[str, List[str]]
    config_sites:Dict[str, Dict[str,str]]

    def __init__(self, config:Dict):
        self.config_sites = config['sites']
        self.reader = ExcelReader(self.config_sites['ap_excel_file'])

    def get_data_structure(self) -> Dict:
        headers = []
        header_items = ['site_name', 'ap_name', 'ap_mac']
        for item in header_items:
            headers.append(self.config_sites['header_column_names'][item].replace('\\n', '\n'))
        values = self.reader.extract_table_from_file(headers, dropset=[self.config_sites['dropna_header'].replace('\\n', '\n')], groupby=self.config_sites['groupby'].replace('\\n', '\n'), worksheet=self.config_sites['sheet_name'])
        self.site_to_mac= {} 
        for name, group in values:
            try:
                name_wo_floor = self._remove_floor_from_site_name(name)
            except ValueError:
                name_wo_floor = name
            if name_wo_floor not in self.site_to_mac:
                self.site_to_mac[name_wo_floor] = [] 
            for item in group.values:
                _, _, ap_mac = item
                if self.is_valid_mac(ap_mac):
                    self.site_to_mac[name_wo_floor].append(ap_mac)
                else:
                    print('Found invalid mac for ap : {}'.format(ap_mac))
        return self.site_to_mac

    def _remove_floor_from_site_name(self, site:str) -> str:
        site_formats = ['Flr-\d+$', '\d(st|nd|rd|th) Flr']
        for site_format in site_formats:
            floor = re.compile(r''+site_format)
            floor_match = floor.search(site)
            if floor_match:
                start = floor_match.start()
                return site[:start-1]
        raise ValueError('Site does not conform to SITE Flr-xx format.')

    def is_valid_mac(self, mac:str, delimiter:str = '') -> bool:
        mac_regex = '^[a-fA-F0-9]{2}' + f'({delimiter}[a-fA-F0-9]' + '{2}){5}$'
        mac_pattern = re.compile(r''+mac_regex)
        if mac_pattern.match(mac):
            return True
        else:
            return False 

    def __str__(self):
        return 'site_to_mac'

class AssignDeviceProfileTask:

    def __init__(self, site_mac:Dict, deviceprofile_id:str, handler:MistAPIHandler):
        self.smn = site_mac
        self.deviceprofile_id = deviceprofile_id
        self.handler = handler
        self.order = 1

    def perform_task(self):

        assign_jsons = []
        sites = {'task':'assign aps to device profile'}
        for site in self.smn:
            try:
                site_macs = self.smn[site]
                assign_json = {
                    'op' : 'assign to device profile',
                    'macs' : site_macs
                }
                assign_jsons.append(assign_json)
            except KeyError:
                pass
        
        for assign_json in assign_jsons:
            sites[site] = {'success':[], 'error':[]}
            if len(assign_json['macs']) > 0:
                print('Assigning APs to Device Profile')
                try:
                    mac_payload = {'macs':assign_json['macs']}
                    self.handler.assign_devices_to_device_profile(self.handler.org_id, self.deviceprofile_id, mac_payload)
                except Exception as e:
                    print(e)
            else:
                print('No MACs to assign to device profile')
                sites[site]['success'] = []
                sites[site]['error'] = []
        
        return sites


class AssignTask:

    def __init__(self, site_mac:Dict, site_name_to_id:Dict[str, str], name_association:Dict[str,str], handler:MistAPIHandler):
        self.smn = site_mac
        self.sn_id = site_name_to_id
        self.name_assoc = name_association
        self.handler = handler
        self.order = 0

    def perform_task(self) -> Dict[str, Dict[str, str]]:
        
        assign_jsons = []
        sites = {'task':'assign ap'}
        for site in self.smn:
            try:    
                site_id = self.sn_id[self.name_assoc[site]]
                site_macs = self.smn[site]
                assign_json = {
                    'op' : 'assign',
                    'site_id' : site_id,
                    'macs' : site_macs,
                    'no_reassign' : False
                }
                assign_jsons.append(assign_json)
            except KeyError:
                pass
         
        for assign_json,site in zip(assign_jsons, self.smn.keys()):
            sites[site] = {'success':[], 'error':[]}
            if len(assign_json['macs']) > 0:
                print(f'assigning APs to site: {self.name_assoc[site]}')
                try:
                    response = self.handler.assign_inventory_to_site(assign_json)
                    sites[site]['success'] = response['success']
                    sites[site]['error'] = response['error']
                except Exception as e:
                    print(e)
            else:
                print(f'No new MACs to assign to site: {self.name_assoc[site]}')
                sites[site]['success'] = []
                sites[site]['error'] = []
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
            print(f'naming APs for site: {self.name_assoc[site]}')
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
                    print(f'pushing ap name {id_to_name[device_id]}...')
                    response = self.handler.config_site_device(site_id, device_id, {'name':id_to_name[device_id]})
                    print('name pushed to site')
                    success.append([response['name'], response['mac']])
                except Exception as e:
                    print(e)
                    error.append(id_to_name[device_id])
            results[site]['success'] = success
            results[site]['error'] = error
        return results

class RenameAPEsxTask:

    def __init__(self, esx_writer:EkahauWriter):
        self.esx_writer = esx_writer
        self.order = 2

    def perform_task(self):
        esx_filepath = self.esx_writer.config['sites']['esx_file']
        if self.esx_writer.ap_names_are_unique_throughout_excel_file():
            result = self.esx_writer.replace_ap_names_in_esx_file(esx_filepath)
        else:
            result = self.esx_writer.rename_aps_floor_dependent(esx_filepath)
        return result

class CreatePerFloorEsxFilesTask:

    def __init__(self, esx_writer:EkahauWriter):
        self.esx_writer = esx_writer
        self.order = 2

    def perform_task(self):
        esx_filepath = self.esx_writer.config['sites']['esx_file']
        esx_basename = esx_filepath[:len(esx_filepath)-4]
        esx_copy_name = esx_basename + ' - Copy.esx'
        if os.path.exists(esx_copy_name):
            esx_filepath = esx_copy_name
        result = {'task' : 'create per floor esx files'}
        esx_data = self.esx_writer.extract_info_from_esx_file(esx_filepath)
        floorplan_ds = self.esx_writer.create_floorplan_specific_esx_data(esx_data)
        for floor in floorplan_ds:
            print(f'creating file {floor}...')
            self.esx_writer.create_floorplan_specific_esx_file(esx_filepath, floor, floorplan_ds[floor])
            result[floor] = {'success':[floor], 'error':[]}
            print('file created.')
        return result

class TaskManager:

    task_datastructure = {
        'assign ap' : [NameAssoc, SiteMac],
        'name ap' : [NameAssoc, SiteMacName],
        'rename esx ap' : [NameAssoc],
        'create per floor esx files' : [NameAssoc],
        'assign aps to device profile' : [NameAssoc, SiteMac],
    }

    def __init__(self, config:Dict = {}, handler:MistAPIHandler = None, writer:ExcelWriter = None, esx_writer:EkahauWriter = None):
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

        self.esx_writer = esx_writer

        self.handler.save_org_id_by_name(config['org'])
        self.handler.populate_site_id_dict()

        if 'assign aps to device profile' in config['sites']['tasks']:
            if 'device_profile' in config['sites']:
                device_profile_name = config['sites']['device_profile']
                deviceprofiles = self.handler.get_device_profiles(self.handler.org_id)
                for deviceprofile in deviceprofiles:
                    if device_profile_name == deviceprofile['name']:
                        self.deviceprofile_id = deviceprofile['id']
                        break
            else:
                print('The task assign aps to device profile requires a device_profile parameter to be set in the config.yml file. Set it and try again.')
                exit()

        self.site_name_to_id = self.handler.sites
        print('reading information from excel file...')
        self._create_data_structures()

        if self.config['sites']['lowercase_ap_names'] == True and 'site_mac_name' in self.data_structures:
            print('lowercasing ap names...')
            self.lowercase_names_in_site_mac_name_ds()

        print('validating data...')
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
        site_dependent_ds = ['site_mac_name', 'site_to_mac']
        for data_structure in self.data_structures:
            if data_structure in site_dependent_ds:
                ds_without_unknown_sites = self._remove_unknown_sites(self.data_structures[data_structure])
                self.data_structures[data_structure] = ds_without_unknown_sites
                if data_structure == 'site_mac_name':
                    validated_ds = self._validate_site_mac_name_ds(self.data_structures[data_structure])
                    self.data_structures[data_structure] = validated_ds
                elif data_structure == 'site_to_mac':
                    validated_ds = self._validate_site_to_mac_ds(self.data_structures[data_structure])
                    self.data_structures[data_structure] = validated_ds
            else:
                pass

    def lowercase_names_in_site_mac_name_ds(self):
        site_mac_name = self.data_structures['site_mac_name']
        for site in site_mac_name:
            for ap in site_mac_name[site]:
                current_name = site_mac_name[site][ap]
                site_mac_name[site][ap] = current_name.lower()
    
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
                try:
                    named_aps = pandas.read_excel(saved_filename, sheet_name='name ap').values.tolist()
                except:
                    named_aps = []
                site_mac_name = ds[site]
                site_mac_name_copy = site_mac_name.copy()
                for mac in site_mac_name:
                    mac_to_name_pair = [site_mac_name[mac], mac]
                    if mac_to_name_pair in named_aps:
                        site_mac_name_copy.pop(mac)
                ds[site] = site_mac_name_copy
            return ds

    def _validate_site_to_mac_ds(self, ds:Dict) -> Dict:
        """ Remove devices that were already assigned to sites previously. """
        excel_base_name = '{}.xlsx'
        for site in ds:
            mist_site_name = self.data_structures['name_association'][site]
            site_id = self.site_name_to_id[mist_site_name]
            saved_filename = os.path.join(os.getcwd(), 'data', excel_base_name.format(site_id))
            if os.path.exists(saved_filename):
                try:
                    assigned_mac = pandas.read_excel(saved_filename, sheet_name='assign ap')['MAC'].values.tolist()
                except:
                    assigned_mac = []
                site_macs = ds[site]
                site_macs_copy = site_macs.copy()
                for mac in site_macs:
                    if mac.lower() in assigned_mac :
                        site_macs_copy.remove(mac)
                ds[site] = site_macs_copy
            return ds

    def create_tasks(self):
        self.execute_queue = []
        for task in self.tasks:
            if task == 'assign ap':
                task_instance = AssignTask(self.data_structures['site_to_mac'], self.site_name_to_id, self.data_structures['name_association'], self.handler)
            elif task == 'name ap':
                task_instance = NameAPTask(self.data_structures['site_mac_name'], self.data_structures['name_association'], self.handler)
            elif task == 'rename esx ap':
                task_instance = RenameAPEsxTask(self.esx_writer)
            elif task == 'create per floor esx files':
                task_instance = CreatePerFloorEsxFilesTask(self.esx_writer)
            elif task == 'assign aps to device profile':
                task_instance = AssignDeviceProfileTask(self.data_structures['site_to_mac'], self.deviceprofile_id, self.handler)
            else:
                raise ValueError(f'Unknown task: {task}. Available tasks are:\nassign ap\nname ap\nrename esx ap\ncreate per floor esx files\n')
            self.execute_queue.append(task_instance)
    
    def execute_tasks(self):
        self.results = []
        self.execute_queue.sort(key=lambda o: o.order)
        for task in self.execute_queue:
            result = task.perform_task()
            self.results.append(result)

    def save_success_configs_to_file(self):
        self.writer = self.writer(self.results, self.site_name_to_id, self.data_structures['name_association'])
        self.writer.write_success_configs_to_file()