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
import json
from zipfile import ZipFile
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
            ],
            'lowercase_ap_names':False
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
def site_to_mac() -> Dict[str, List[str]]:
    return {
        'site0' : [generate_random_mac()],
        'site1' : [generate_random_mac()]
    }

@pytest.fixture
def static_site_to_mac() -> Dict[str, List[str]]:
    return {
        'site0' : ['mac0'],
        'site1' : ['mac1']
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
    df = pandas.DataFrame(data=test_macs, columns=['MAC'])
    full_file_path = os.path.join(os.getcwd(), 'data', 'id1.xlsx')
    with pandas.ExcelWriter(full_file_path) as writer:
        df = pandas.DataFrame(data=test_macs, columns=['MAC'])
        df.to_excel(writer, index=False, sheet_name='assign ap')
        test_mac_names = [['aabbccddeef1', 'ap-1'], ['aabbccddeef2', 'ap-2']]
        df = pandas.DataFrame(data=test_mac_names, columns=['MAC', 'NAME'])
        df.to_excel(writer, sheet_name='name ap', index=False)
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

@pytest.fixture
def create_temp_excel_data_uppercase_names() -> str:
    test_data = [[f'site1 Flr-0{num}', f'aabbccddeef{num}', f'AP-{num}'] for num in range(5)] 
    df = pandas.DataFrame(data=test_data, columns=['Site\nBld\nFloor', 'New WAP \nMAC Address','New WAP Name'])
    full_path = os.path.join(os.getcwd(), 'data', 'test_data.xlsx')
    df.to_excel(full_path, index=False, sheet_name='test')
    yield full_path
    os.remove(full_path)

@pytest.fixture
def get_test_ap_data():
    test_data = {
  "accessPoints": [
    {
      "name": "Measured AP-33:ab",
      "mine": False,
      "userDefinedPosition": False,
      "noteIds": [],
      "tags": [],
      "id": "b185b285-22cf-4dc2-8033-185950809ce7",
      "status": "CREATED"
    },
    {
      "name": "vbg2600-n1e-12",
      "mine": False,
      "userDefinedPosition": False,
      "noteIds": [],
      "vendor": "Cisco",
      "model": "",
      "tags": [],
      "id": "6a99621e-db58-401f-ab4c-29e8ae3d835b",
      "status": "CREATED"
    },
    {
      "location": {
        "floorPlanId": "2d3b2d17-25d3-4ebb-bd8c-5fc7b9b75bf0",
        "coord": {
          "x": 765.3018727910558,
          "y": 288.53909480473203
        }
      },
      "name": "AP21",
      "mine": True,
      "userDefinedPosition": True,
      "noteIds": [
        "bc474aaf-9cd5-4651-9e6c-cff0603ac006"
      ],
      "vendor": "Mist",
      "model": "",
      "tags": [],
      "id": "8f3a97a6-28e9-4752-92ad-6f00352817a6",
      "status": "CREATED"
    },
    {
      "location": {
        "floorPlanId": "85222db6-8dcb-4e79-998f-e2416ab44153",
        "coord": {
          "x": 565.8025530447351,
          "y": 650.9133237774099
        }
      },
      "name": "AP072",
      "mine": True,
      "userDefinedPosition": False,
      "noteIds": [
        "665e40b4-0691-4555-acaf-77d270286ee3"
      ],
      "vendor": "Mist",
      "model": "",
      "tags": [],
      "id": "f1d7b2b5-9461-49a1-9558-9b0241380dc4",
      "status": "CREATED"
    },
    {
      "location": {
        "floorPlanId": "2d3b2d17-25d3-4ebb-bd8c-5fc7b9b75bf0",
        "coord": {
          "x": 685.7095447426987,
          "y": 456.6705156205836
        }
      },
      "name": "AP36",
      "mine": True,
      "userDefinedPosition": True,
      "noteIds": [
        "1f64acf0-c90f-4fd7-a465-829f85319e15"
      ],
      "vendor": "Mist",
      "model": "",
      "tags": [],
      "id": "fb08208f-9ebe-48ac-ae37-33fc52f37aa8",
      "status": "CREATED"
    },
    {
      "location": {
        "floorPlanId": "85222db6-8dcb-4e79-998f-e2416ab44153",
        "coord": {
          "x": 662.1880815804216,
          "y": 636.8000822415748
        }
      },
      "name": "AP058",
      "mine": True,
      "userDefinedPosition": False,
      "noteIds": [
        "4ad6864e-7732-4938-94a8-55e4dc41e7e2"
      ],
      "vendor": "Mist",
      "model": "",
      "tags": [],
      "id": "189990f4-c1fa-4fbf-8580-c56f3c6ebeac",
      "status": "CREATED"
    },
  ]
    }
    return test_data

@pytest.fixture
def get_test_floorplan_data():
    test_data = {
        "floorPlans": [
    {
      "name": "VBG - Floor 4",
      "width": 841.0,
      "height": 595.0,
      "metersPerUnit": 0.1543577072585195,
      "imageId": "a96ea6ca-88a9-48d1-a2a2-0762cff6a8f2",
      "bitmapImageId": "be3c74b7-c7f7-43f3-a452-dbcc7af37a49",
      "gpsReferencePoints": [],
      "floorPlanType": "FSPL",
      "cropMinX": 30.889724310776955,
      "cropMinY": 0.0,
      "cropMaxX": 841.0,
      "cropMaxY": 595.0,
      "rotateUpDirection": "LEFT",
      "tags": [],
      "id": "ea798325-1bae-4608-b5ec-a137ad3a7dec",
      "status": "CREATED"
    },
    {
      "name": "VBG - MOB Floor 4",
      "width": 841.0,
      "height": 595.0,
      "metersPerUnit": 0.14021459964438093,
      "imageId": "65f7bf97-e2b3-4a80-a948-298f84cc98a5",
      "bitmapImageId": "93ca43f3-8d44-4a28-82e6-8c873e36e947",
      "gpsReferencePoints": [],
      "floorPlanType": "FSPL",
      "cropMinX": 295.05012531328316,
      "cropMinY": 7.456140350877206,
      "cropMaxX": 533.1679197994987,
      "cropMaxY": 569.4360902255639,
      "rotateUpDirection": "LEFT",
      "tags": [],
      "id": "93c89f93-040b-4469-ab49-b3c254b197eb",
      "status": "CREATED"
    },
    {
      "name": "VBG - Floor 3",
      "width": 841.0,
      "height": 595.0,
      "metersPerUnit": 0.1682560911697549,
      "imageId": "faae511b-f49b-4865-a64e-06f6eb05b0a7",
      "bitmapImageId": "2a1adc17-83e1-45e1-bd7e-0b77318f246e",
      "gpsReferencePoints": [],
      "floorPlanType": "FSPL",
      "cropMinX": 0.0,
      "cropMinY": 0.0,
      "cropMaxX": 841.0,
      "cropMaxY": 595.0,
      "rotateUpDirection": "RIGHT",
      "tags": [],
      "id": "4538b490-edaf-46a0-bf5d-f40d21189307",
      "status": "CREATED"
    },
    {
      "name": "VBG - Floor 2",
      "width": 1132.0,
      "height": 945.0,
      "metersPerUnit": 0.25379893534497106,
      "imageId": "52f16650-a60a-431e-ae0f-448b1d2745cb",
      "gpsReferencePoints": [],
      "floorPlanType": "FSPL",
      "cropMinX": 140.41353383458642,
      "cropMinY": 42.29323308270676,
      "cropMaxX": 1110.0075187969924,
      "cropMaxY": 741.9924812030076,
      "rotateUpDirection": "UP",
      "tags": [],
      "id": "2d3b2d17-25d3-4ebb-bd8c-5fc7b9b75bf0",
      "status": "CREATED"
    },
    {
      "name": "VBG - MOB Floor 1",
      "width": 841.0,
      "height": 595.0,
      "metersPerUnit": 0.1426063537289941,
      "imageId": "5c943e97-6126-446d-a2eb-87ce65405737",
      "bitmapImageId": "3a20edaa-5268-46e9-9fb6-73fd3e15d196",
      "gpsReferencePoints": [],
      "floorPlanType": "FSPL",
      "cropMinX": 303.57142857142844,
      "cropMinY": 0.0,
      "cropMaxX": 574.7092731829574,
      "cropMaxY": 595.0,
      "rotateUpDirection": "LEFT",
      "tags": [],
      "id": "e82611ba-e0d4-4738-b7eb-c3b9357f2c87",
      "status": "CREATED"
    },
    {
      "name": "VBG - MOB Floor 2",
      "width": 841.0,
      "height": 595.0,
      "metersPerUnit": 0.11725714186046168,
      "imageId": "d6061ff6-277b-48f6-9334-b55d77958093",
      "bitmapImageId": "5448dc93-a8b9-4854-aa91-aec14d5c1b96",
      "gpsReferencePoints": [],
      "floorPlanType": "FSPL",
      "cropMinX": 291.85463659147865,
      "cropMinY": 0.0,
      "cropMaxX": 561.9273182957393,
      "cropMaxY": 595.0,
      "rotateUpDirection": "LEFT",
      "tags": [],
      "id": "81222b78-c982-4b71-84d4-239b4d6006ed",
      "status": "CREATED"
    },
    {
      "name": "VBG - MOB Floor 3",
      "width": 841.0,
      "height": 595.0,
      "metersPerUnit": 0.17205306977658935,
      "imageId": "872651dc-2593-4d31-a456-59633494d026",
      "bitmapImageId": "c5e6c60e-a869-497b-b366-64dcce2ebf03",
      "gpsReferencePoints": [],
      "floorPlanType": "FSPL",
      "cropMinX": 361.0902255639097,
      "cropMinY": 0.0,
      "cropMaxX": 534.233082706767,
      "cropMaxY": 595.0,
      "rotateUpDirection": "LEFT",
      "tags": [],
      "id": "9ec73444-e1e0-41b0-a249-8ff98570977e",
      "status": "CREATED"
    },
    {
      "name": "VBG - Floor 1",
      "width": 1086.0,
      "height": 951.0,
      "metersPerUnit": 0.22020780559313144,
      "imageId": "4f34c13d-143f-4024-804b-7c0e190e9b2e",
      "gpsReferencePoints": [],
      "floorPlanType": "FSPL",
      "cropMinX": 0.0,
      "cropMinY": 0.0,
      "cropMaxX": 1086.0,
      "cropMaxY": 951.0,
      "rotateUpDirection": "UP",
      "tags": [],
      "id": "85222db6-8dcb-4e79-998f-e2416ab44153",
      "status": "CREATED"
    }
        ]
    }
    return test_data

@pytest.fixture
def create_temp_esx_zip(get_test_ap_data, get_test_floorplan_data):
    temp_zip = os.path.join(os.getcwd(), 'dev', 'test.zip')
    with ZipFile(temp_zip, 'w') as zf:
            zf.writestr('accessPoints.json', json.dumps(get_test_ap_data))
            zf.writestr('floorPlans.json', json.dumps(get_test_floorplan_data))
    yield temp_zip
    os.remove(temp_zip)

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

def test_AssignTask_creates_assign_jsons_and_pushes_to_handler(site_to_mac, site_name_to_id, name_association):
    handler = FakeAPIHandler()
    assign_task = tasks.AssignTask(site_to_mac, site_name_to_id, name_association, handler)
    sites = assign_task.perform_task()
    assert sites == {'site0':{'success':site_to_mac['site0'], 'error':[]}, 'site1':{'success':site_to_mac['site1'], 'error':[]}, 'task' :'assign ap'}

def test_NameAPTask_creates_device_jsons_and_pushes_to_handler(static_site_mac_name, name_association):
    handler = FakeAPIHandler()
    name_ap_task = tasks.NameAPTask(static_site_mac_name, name_association, handler)
    response = name_ap_task.perform_task()
    assert response == {'site0':{'success':[['site0-ap-01','mac0']], 'error':[]}, 'site1':{'success':[['site1-ap-01','mac1']], 'error':[]}, 'task':'name ap'}

def test_validate_data_structure_removes_macs_already_assigned_macs_from_site_mac_name_dict(create_temp_site_excel, create_temp_excel_data):
    expected = {
        'site1' : [
            'aabbccddeef0',
            'aabbccddeef3',
            'aabbccddeef4',
        ]
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
            ],
            'lowercase_ap_names' : False
        },
        'login' : {
            'username' : 'username',
            'password' : 'password'
        }
     }
    task_manager = tasks.TaskManager(config=config, handler=FakeAPIHandler)
    task_manager._validate_data_structures()
    assert expected == task_manager.data_structures['site_to_mac']

def test_create_tasks_adds_assign_task_object_to_execute_queue(create_temp_excel_data):
    config = get_test_config_data()
    config['sites']['ap_excel_file'] = create_temp_excel_data
    task_manager = tasks.TaskManager(config=config, handler=FakeAPIHandler)
    task_manager.create_tasks()
    assign_task = task_manager.execute_queue[0]
    assert isinstance(assign_task, tasks.AssignTask)
    assert assign_task.order == 0
    assert assign_task.name_assoc == {'site1' : 'site1'}
    assert assign_task.smn == {'site1': [f'aabbccddeef{num}' for num in range(5)]}

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
    generated = pandas.read_excel(create_temp_site_excel)['MAC'].values.tolist()
    assert expected == generated

def test_lowercase_names_in_site_mac_name_changes_ds_names_to_lowercase(create_temp_excel_data_uppercase_names):
    config = get_test_config_data()
    config['sites']['ap_excel_file'] = create_temp_excel_data_uppercase_names
    config['sites']['lowercase_ap_names'] = True
    config['sites']['tasks'].append('name ap')
    task_manager = tasks.TaskManager(config=config, handler=FakeAPIHandler, writer=file_ops.ExcelWriter)
    expected = {
        'site1' : {f'aabbccddeef{num}':f'ap-{num}' for num in range(5)}
    }
    generated = task_manager.data_structures['site_mac_name']
    assert expected == generated

def test_validate_site_mac_name_ds_removes_aps_that_were_already_assigned(create_temp_excel_data, create_temp_site_excel):
    config = get_test_config_data()
    config['sites']['ap_excel_file'] = create_temp_excel_data
    task_manager = tasks.TaskManager(config=config, handler=FakeAPIHandler, writer=file_ops.ExcelWriter)
    expected = {
        'site1' : [f'aabbccddeef{num}' for num in range(3,5)]
        }
    expected['site1'].insert(0, 'aabbccddeef0')
    generated = task_manager.data_structures['site_to_mac']
    assert expected == generated

def test_validate_site_to_mac_ds_removes_aps_that_were_already_named(create_temp_excel_data, create_temp_site_excel):
    config = get_test_config_data()
    config['sites']['ap_excel_file'] = create_temp_excel_data
    config['sites']['tasks'] = ['name ap']
    task_manager = tasks.TaskManager(config=config, handler=FakeAPIHandler, writer=file_ops.ExcelWriter)
    expected = {
        'site1' : {f'aabbccddeef{num}' : f'ap-{num}' for num in range(3,5)}
        }
    expected['site1']['aabbccddeef0'] = 'ap-0'
    generated = task_manager.data_structures['site_mac_name']
    assert expected == generated

def test_remove_locations_from_aps_removes_only_designated_floorplan_id(create_temp_esx_zip):
    esx_writer = file_ops.EkahauWriter(get_test_config_data) 
    floorplan_id = "2d3b2d17-25d3-4ebb-bd8c-5fc7b9b75bf0"
    expected = { 
        "accessPoints": [
    {
      "name": "Measured AP-33:ab",
      "mine": False,
      "userDefinedPosition": False,
      "noteIds": [],
      "tags": [],
      "id": "b185b285-22cf-4dc2-8033-185950809ce7",
      "status": "CREATED"
    },
    {
      "name": "vbg2600-n1e-12",
      "mine": False,
      "userDefinedPosition": False,
      "noteIds": [],
      "vendor": "Cisco",
      "model": "",
      "tags": [],
      "id": "6a99621e-db58-401f-ab4c-29e8ae3d835b",
      "status": "CREATED"
    },
    {
      "location": {
        "floorPlanId": "2d3b2d17-25d3-4ebb-bd8c-5fc7b9b75bf0",
        "coord": {
          "x": 765.3018727910558,
          "y": 288.53909480473203
        }
      },
      "name": "AP21",
      "mine": True,
      "userDefinedPosition": True,
      "noteIds": [
        "bc474aaf-9cd5-4651-9e6c-cff0603ac006"
      ],
      "vendor": "Mist",
      "model": "",
      "tags": [],
      "id": "8f3a97a6-28e9-4752-92ad-6f00352817a6",
      "status": "CREATED"
    },
    {
      "name": "AP072",
      "mine": True,
      "userDefinedPosition": False,
      "noteIds": [
        "665e40b4-0691-4555-acaf-77d270286ee3"
      ],
      "vendor": "Mist",
      "model": "",
      "tags": [],
      "id": "f1d7b2b5-9461-49a1-9558-9b0241380dc4",
      "status": "CREATED"
    },
    {
      "location": {
        "floorPlanId": "2d3b2d17-25d3-4ebb-bd8c-5fc7b9b75bf0",
        "coord": {
          "x": 685.7095447426987,
          "y": 456.6705156205836
        }
      },
      "name": "AP36",
      "mine": True,
      "userDefinedPosition": True,
      "noteIds": [
        "1f64acf0-c90f-4fd7-a465-829f85319e15"
      ],
      "vendor": "Mist",
      "model": "",
      "tags": [],
      "id": "fb08208f-9ebe-48ac-ae37-33fc52f37aa8",
      "status": "CREATED"
    },
    {
      "name": "AP058",
      "mine": True,
      "userDefinedPosition": False,
      "noteIds": [
        "4ad6864e-7732-4938-94a8-55e4dc41e7e2"
      ],
      "vendor": "Mist",
      "model": "",
      "tags": [],
      "id": "189990f4-c1fa-4fbf-8580-c56f3c6ebeac",
      "status": "CREATED"
    },
  ]
    }
    with ZipFile(create_temp_esx_zip) as zf:
        generated = esx_writer.remove_location_info_from_aps_not_on_floorplan(zf,floorplan_id)
    assert expected == generated

def test_remove_all_floorplans_except_current_floorplan_keeps_only_current_floorplan(create_temp_esx_zip):
    esx_writer = file_ops.EkahauWriter(get_test_config_data)
    floorplan_id = "2d3b2d17-25d3-4ebb-bd8c-5fc7b9b75bf0"
    expected = {
        "floorPlans": [
    {
      "name": "VBG - Floor 2",
      "width": 1132.0,
      "height": 945.0,
      "metersPerUnit": 0.25379893534497106,
      "imageId": "52f16650-a60a-431e-ae0f-448b1d2745cb",
      "gpsReferencePoints": [],
      "floorPlanType": "FSPL",
      "cropMinX": 140.41353383458642,
      "cropMinY": 42.29323308270676,
      "cropMaxX": 1110.0075187969924,
      "cropMaxY": 741.9924812030076,
      "rotateUpDirection": "UP",
      "tags": [],
      "id": "2d3b2d17-25d3-4ebb-bd8c-5fc7b9b75bf0",
      "status": "CREATED"
    },
        ]
    }
    with ZipFile(create_temp_esx_zip) as zf:
        generated = esx_writer.remove_all_floorplans_except_current_floorplan(zf, floorplan_id)
    assert expected == generated