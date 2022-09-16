import sys
sys.path.append('C:/Users/jasohoa/Documents/Automation/MIST/src')
import inventory_devices
import tasks
import pytest
import random
from typing import Dict, List


class FakeAPIHandler:

    def __init__(self):
        self.data = []
        self.sites = {
            'site0' : 'id0',
            'site1' : 'id1'
        }
        self.site_devices = {
            'id0' : [ {'id': 'dev_id0', 'mac':'mac0'}],
            'id1' : [ {'id' : 'dev_id1', 'mac':'mac1'}]
        }
    
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
    assert True == generated

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