import sys
import os
src_path = os.getenv('MistAPIHandler')
sys.path.append(src_path)
import inventory_devices
import tasks
import pytest
import random
import pandas
import file_ops
from typing import Dict, List


class FakeAPIHandler:

    def __init__(self, username:str='', password:str=''):
        self.data = []
        self.sites = {
            'site0' : 'id0',
            'site1' : 'id1'
        }
        self.site_devices = {
            'id0' : [ {'id': 'dev_id0', 'mac':'mac0'}],
            'id1' : [ {'id' : 'dev_id1', 'mac':'mac1'}]
        }
        self.username = username
        self.password = password
    
    def assign_inventory_to_site(self, request_body:Dict) -> Dict:
        self.data.append(request_body)
        assign_macs = request_body['macs']
        return {
            'op' : 'assign',
            'success' : assign_macs,
            'error' : []
        }
    
    def config_site_device(self, site_id:str, device_id:str, request_body:Dict) -> Dict:
        self.data.append(request_body)
        name = request_body['name']
        return {
            'name' : name,
            'id' : device_id,
            'mac' : self.site_devices[site_id][0]['mac']
        }

    def get_site_devices(self, site_id:str) -> Dict:
        return self.site_devices[site_id] 
    
    def save_org_id_by_name(self, org_name:str):
        self.org_id = '001'
    
    def populate_site_id_dict(self):
        pass

    def get_inventory(self):
        self.org_inventory = [
            {'mac':f'mac{num}'} for num in range(5)
        ]
        return self.org_inventory

def generate_random_mac():
    mac = ''
    length = 12
    while length > 0:
        mac += random.choice('abcdef0123456789')
        length -= 1
    return mac

def generate_site_mac_name(num_records_to_generate:int) -> Dict[str, Dict[str,str]]:
    site_number = 0
    site_mac_name_dict = {}
    while site_number < num_records_to_generate:
        site_mac_name_dict[f'site{site_number}'] = { generate_random_mac() : f'ap{site_number}' }
    return site_mac_name_dict        

def get_test_config_data() -> Dict:
    return {
        'org' : 'org',
        'sites' : {
            'ap_excel_file' : '',
            'sheet_name' : 'test',
            'header_column_names': {
                'site' : 'Site\nBld\nFloor',
                'ap_name' : 'New WAP Name',
                'ap_mac' : 'New WAP \nMAC Address'
            },
            'dropna_header' : 'New WAP \nMAC Address',
            'groupby' : 'Site\nBld\nFloor',
            'site1' : {
                'name' : 'site1'
            },
            'tasks' : [
                'assign ap'
            ]
        },
        'login' : {
            'username' : 'username',
            'password' : 'password'
        }
     }

@pytest.fixture
def site_mac_name() -> Dict[str, Dict[str,str]]:
    return {
        'site0' : { generate_random_mac() : 'site0-ap-01' },
        'site1' : { generate_random_mac() : 'site1-ap-01'}
    }

@pytest.fixture
def static_site_mac_name() -> Dict[str, Dict[str,str]]:
    return {
        'site0' : {'mac0':'site0-ap-01'},
        'site1' : {'mac1':'site1-ap-01'}
    }

@pytest.fixture
def site_name_to_id() -> Dict[str, str]:
    return {
        'site0' : 'id0',
        'site1' : 'id1'
    }

@pytest.fixture
def name_association() -> Dict[str, str]:
    return {
        'site0' : 'site0',
        'site1' : 'site1'
    }

@pytest.fixture
def create_temp_site_excel() -> str:
    test_macs = ['aabbccddeef1', 'aabbccddeef2']
    df = pandas.DataFrame(data=test_macs, columns=['mac'])
    full_file_path = os.path.join(os.getcwd(), 'data', 'id1.xlsx')
    df.to_excel(full_file_path, index=False, sheet_name='assign ap')
    yield full_file_path
    os.remove(full_file_path)

@pytest.fixture
def create_temp_excel_data() -> str:
    test_data = [[f'site1 Flr-0{num}', f'aabbccddeef{num}', f'ap-{num}'] for num in range(5)] 
    df = pandas.DataFrame(data=test_data, columns=['Site\nBld\nFloor', 'New WAP \nMAC Address','New WAP Name'])
    full_path = os.path.join(os.getcwd(), 'data', 'test_data.xlsx')
    df.to_excel(full_path, index=False, sheet_name='test')
    yield full_path
    os.remove(full_path)

def test_remove_floor_from_site_name_removes_floor():
    test_data = 'SCP MAB Flr-1'
    expected = 'SCP MAB'
    generated = inventory_devices.remove_floor_from_site_name(test_data)
    assert expected == generated

def test_remove_floor_from_site_name_raises_error_if_no_match():
    test_data = 'xail'
    with pytest.raises(ValueError) as e:
        inventory_devices.remove_floor_from_site_name(test_data)

def test_create_assign_json_adds_correct_site_id_based_on_name():
    test_data = ('SCP MAB',
        {'aabbccddeeff' : 'SCP-MAB-FL01-AP001',
        'aabbccddeefe' : 'SCP-MAB-FL01-AP002',
        'aabbccddeefd' : 'SCP-MAB-FL01-AP003'}
    )
    expected = {
        'op' : 'assign',
        'site_id' : '07e88738-d52d-4968-8fd4-b6d272dcd69e',
        'macs' : ['aabbccddeeff', 'aabbccddeefe', 'aabbccddeefd'],
        'no_reassign': False
    }
    generated = inventory_devices.create_assign_json(test_data, {'SCP-Sentara SCP MAB':'07e88738-d52d-4968-8fd4-b6d272dcd69e'}, {'SCP MAB':'SCP-Sentara SCP MAB'})
    assert generated == expected

def test_remove_invalid_macs_removes_only_invalid_macs_from_list():
    test_data = ['aabbccddeeff', '.ckif', 'lif,m', 'aabbccddeefe']
    expected = ['aabbccddeeff', 'aabbccddeefe']
    generated = inventory_devices.remove_invalid_macs(test_data)
    assert expected == generated

def test_remove_invalid_macs_checks_colon_delimited_macs():
    test_data = ['aa:bb:cc:dd:ee:ff', ',ckif', 'fkdmc,', 'aa:bb:cc:dd:ee:fe']
    expected = ['aa:bb:cc:dd:ee:ff', 'aa:bb:cc:dd:ee:fe']
    generated = inventory_devices.remove_invalid_macs(test_data, delimiter=':')
    assert expected == generated

def test_remove_invalid_macs_checks_dash_delimited_macs():
    test_data = ['aa-bb-cc-dd-ee-ff', ',ckif', 'fkdmc,', 'aa-bb-cc-dd-ee-fe']
    expected = ['aa-bb-cc-dd-ee-ff', 'aa-bb-cc-dd-ee-fe']
    generated = inventory_devices.remove_invalid_macs(test_data, delimiter='-')
    assert expected == generated

def test_is_valid_mac_returns_true_for_valid_mac_with_no_delims():
    test_data = 'aabbccddeeff'
    generated = inventory_devices.is_valid_mac(test_data)
    assert True == generated

def test_is_valid_mac_returns_false_for_valid_mac_with_no_delims():
    test_data = 'aabbccddeef'
    generated = inventory_devices.is_valid_mac(test_data)
    assert False == generated

def test_is_valid_mac_returns_true_for_valid_mac_with_colon_delims():
    test_data = 'aa:bb:cc:dd:ee:ff'
    generated = inventory_devices.is_valid_mac(test_data, ':')
    assert True == generated

def test_is_valid_mac_returns_false_for_valid_mac_with_colon_delims():
    test_data = 'aa:bb:cc:dd:ee:f'
    generated = inventory_devices.is_valid_mac(test_data, ':')
    assert False == generated

def test_get_site_names_from_config_creates_full_list_of_sites():
    test_data = {
        'ap_excel_file' : 'somefile',
        'other_config_info' : 'other_info',
        'site1': {
            'excel_name' : 'SCP MAP',
            'name' : 'SCP-Sentara SCP MAP'
        },
        'site2': {
            'excel_name' : 'SCP MOB',
            'name' : 'SCP-Sentara SCP MOB'
        },
        'site3': {
            'excel_name' : 'SCP',
            'name' : 'SCP-Sentara Caremore Plex'
        }
    }
    expected = ['SCP-Sentara SCP MAP', 'SCP-Sentara SCP MOB', 'SCP-Sentara Caremore Plex']
    generated = inventory_devices.get_site_names_from_config_sites(test_data)
    assert expected == generated

def test_create_name_association_dict_creates_excel_name_to_name_associations_when_both_are_present_in_a_site():
    test_data = {
        'site1' : {
            'name' : 'SCP-Sentara SCP MOB',
            'excel_name' : 'SCP MOB'
        },
        'site2' : {
            'name' : 'SCP-Sentara SCP MAB',
            'excel_name' : 'SCP MAB'
        },
        'other_info' : 'other_info'
    }
    expected = {'SCP MOB': 'SCP-Sentara SCP MOB', 'SCP MAB': 'SCP-Sentara SCP MAB'}
    generated = inventory_devices.create_name_association_dict(test_data)
    assert expected == generated

def test_create_name_association_dict_creates_name_to_name_associations_when_only_one_is_present():
    test_data = {
        'site1' : {
            'name' : 'SCP-Sentara SCP MOB'
        },
        'site2' : {
            'name' : 'SCP-Sentara SCP MAB'
        }
    }
    expected = {'SCP-Sentara SCP MOB':'SCP-Sentara SCP MOB', 'SCP-Sentara SCP MAB': 'SCP-Sentara SCP MAB'}
    generated = inventory_devices.create_name_association_dict(test_data)
    assert expected == generated

def test_AssignTask_creates_assign_jsons_and_pushes_to_handler(site_mac_name, site_name_to_id, name_association):
    handler = FakeAPIHandler()
    assign_task = tasks.AssignTask(site_mac_name, site_name_to_id, name_association, handler)
    sites = assign_task.perform_task()
    assert sites == {'site0':{'success':[list(site_mac_name['site0'].keys())[0]], 'error':[]}, 'site1':{'success':[list(site_mac_name['site1'].keys())[0]], 'error':[]}, 'task' :'assign ap'}

def test_NameAPTask_creates_device_jsons_and_pushes_to_handler(static_site_mac_name, name_association):
    handler = FakeAPIHandler()
    name_ap_task = tasks.NameAPTask(static_site_mac_name, name_association, handler)
    response = name_ap_task.perform_task()
    assert response == {'site0':{'success':[['site0-ap-01','mac0']], 'error':[]}, 'site1':{'success':[['site1-ap-01','mac1']], 'error':[]}, 'task':'name ap'}

def test_validate_data_structure_removes_macs_already_assigned_macs_from_site_mac_name_dict(create_temp_site_excel, create_temp_excel_data):
    expected = {
        'site1' : {
            'aabbccddeef3' : 'ap-3',
            'aabbccddeef4' : 'ap-4',
            'aabbccddeef0' : 'ap-0'
        }
    }
    config = {
        'org' : 'org',
        'sites' : {
            'ap_excel_file' : create_temp_excel_data,
            'sheet_name' : 'test',
            'header_column_names': {
                'site' : 'Site\nBld\nFloor',
                'ap_name' : 'New WAP Name',
                'ap_mac' : 'New WAP \nMAC Address'
            },
            'dropna_header' : 'New WAP \nMAC Address',
            'groupby' : 'Site\nBld\nFloor',
            'site1' : {
                'name' : 'site1'
            },
            'tasks' : [
                'assign ap'
            ]
        },
        'login' : {
            'username' : 'username',
            'password' : 'password'
        }
     }
    task_manager = tasks.TaskManager(config=config, handler=FakeAPIHandler)
    task_manager._validate_data_structures()
    assert expected == task_manager.data_structures['site_mac_name']

def test_create_tasks_adds_assign_task_object_to_execute_queue(create_temp_excel_data):
    config = get_test_config_data()
    config['sites']['ap_excel_file'] = create_temp_excel_data
    task_manager = tasks.TaskManager(config=config, handler=FakeAPIHandler)
    task_manager.create_tasks()
    assign_task = task_manager.execute_queue[0]
    assert isinstance(assign_task, tasks.AssignTask)
    assert assign_task.order == 0
    assert assign_task.name_assoc == {'site1' : 'site1'}
    assert assign_task.smn == [('site1', {f'aabbccddeef{num}': f'ap-{num}' for num in range(5)})]

def test_ExcelWriter_creates_file_with_site_id_and_macs_for_successful_assign_task():
    test_data = [{
        'task' : 'assign ap',
        'site1' : {
        'success' : [
            f'aabbccddeef{num}' for num in range(5)
        ],
        'error' : []
        }
    }]
    excel_writer = file_ops.ExcelWriter(test_data, {'site1': 'id1'},{'site1':'site1'})
    excel_writer.write_success_configs_to_file()
    file_path = os.path.join(os.getcwd(), 'data', 'id1.xlsx')
    assert os.path.exists(file_path)
    
    file_contents = pandas.read_excel(file_path, sheet_name='assign ap')['MAC'].values.tolist()
    assert [f'aabbccddeef{num}' for num in range(5)] == file_contents

    os.remove(file_path)

def test_ExcelWriter_creates_file_with_site_id_and_ap_name_to_mac_for_successful_ap_name_task():
    test_data = [{
        'task' : 'name ap',
        'site1' : {
            'success' : [
                [f'aabbccddeef{num}', f'ap-{num}'] for num in range(5)
            ],
            'error' : []
        }
    }]

    excel_writer = file_ops.ExcelWriter(test_data, {'site1': 'id1'}, {'site1':'site1'})
    excel_writer.write_success_configs_to_file()
    file_path = os.path.join(os.getcwd(), 'data', 'id1.xlsx')
    assert os.path.exists(file_path)

    file_contents = pandas.read_excel(file_path, sheet_name='name ap').values.tolist()
    assert [[f'aabbccddeef{num}', f'ap-{num}'] for num in range(5)] == file_contents

    os.remove(file_path)

def test_TaskManager_executes_tasks_in_correct_order(create_temp_excel_data):
    config = get_test_config_data()
    config['sites']['ap_excel_file'] = create_temp_excel_data
    config['sites']['tasks'].append('name ap')
    task_manager = tasks.TaskManager(config=config, handler=FakeAPIHandler, writer=file_ops.ExcelWriter)
    task_manager.create_tasks()
    task_manager.execute_tasks()
    expected = ['assign ap', 'name ap']
    generated = [result['task'] for result in task_manager.results]
    assert expected == generated 

def test_remove_floor_from_site_name_matches_on_nam_num_cardinal_Flr_format():
    test_strs = ['Test Site 1st Flr', 'Test Site 2nd Flr', 'Test Site 3rd Flr', 'Test Site 5th Flr']
    expected = ['Test Site' for _ in range(len(test_strs))]
    generated = [inventory_devices.remove_floor_from_site_name(test_str) for test_str in test_strs]
    assert expected == generated

def test_ExcelWriter_writes_only_unique_values_to_worksheet(create_temp_site_excel):
    test_data = [
        {
        'task' : 'assign ap',
        'site1': { 
        'success' :[f'aabbccddeef{num}' for num in range(1,5)],
        'error': []
               }
        }
    ]

    expected = [f'aabbccddeef{num}' for num in range(1, 5)]
    writer = file_ops.ExcelWriter(test_data, {'site1':'id1'}, {'site1':'site1'})
    writer.write_success_configs_to_file()
    generated = pandas.read_excel(create_temp_site_excel)['mac'].values.tolist()
    assert expected == generated