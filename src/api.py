from subprocess import call
import requests
import json
from typing import Dict, List 

class MistAPIHandler:

    BASE_URL :str = 'https://api.mist.com/api/v1/'
    headers :Dict[str,str] = {
        'Content-Type':'application/json',
        'X-CSRFTOKEN':''
    }
    cookies:Dict[str,str] = {'sessionid':'', 'csrftoken':''}
    login_methods :list[str]= [
       'usr_pw',
       'oauth2'
    ]
    api_endpoints:Dict[str,str] = {
        "login":"login",
        "check_login": "self",
        "mxedges_stats": "orgs/{}/stats/mxedges",
        "mxedge_stats" : "orgs/{}/stats/mxedges/{}",
        "mxedge_events": "const/mxedge_events",
        "sites" : "orgs/{}/sites",
        "site" : "sites/{}",
        "site_group" : "orgs/{}/sitegroups",
        "site_devices" : "sites/{}/devices",
        "device_config" : "sites/{}/devices/{}",
        "inventory" : "orgs/{}/inventory",
        "bounce_tunterm_data_ports" : "orgs/{}/mxedges/{}/services/tunterm/bounce_port",
        "mistedge_restart" : "orgs/{}/mxedges/{}/restart",
        "claim_mistedge" : "orgs/{}/mxedges/claim",
        "assign_mistedge_to_site" : "orgs/{}/mxedges/assign",
        "create_mistedge" : "orgs/{}/mxedges",
        "get_mxedge_models" : "const/mxedge_models",
        "get_mxedge_clusters" : "orgs/{}/mxclusters",
        "wlan" : "orgs/{}/wlans",
        "import_map" : "sites/{}/maps/import",
        "org_import_map" : "orgs/{}/maps/import"
    }
    sites  = {}
    org_id = ''
    
    def __init__(self, login_method:str, login_params:Dict[str,str]) -> None:
        if login_method not in self.login_methods:
            raise ValueError('Unsupported login method.')
        else:
            try:
                if login_method == 'usr_pw':
                    self._login_usr_pw(login_params)
                elif login_method == 'oauth2':
                    self._login_oauth2(login_params)
                print('Login Successful. Tokens set.')
            except Exception as e:
                print('Login Failed...')
                print(e)
                
    def _login_usr_pw(self, login_params:Dict[str,str]) -> bool:
        api_path:str = 'login'
        if 'two_factor' not in login_params:
            body = json.dumps({'email':login_params['username'], 'password':login_params['password']})
            full_api_path = f"{self.BASE_URL}{api_path}"
            response = requests.post(full_api_path,data=body,headers={'Content-Type':'application/json'})
            if response.status_code == 200:
                self.headers['X-CSRFTOKEN'] = response.cookies.get('csrftoken')
                self.cookies['sessionid'] = response.cookies.get('sessionid')
                self.cookies['csrftoken'] = response.cookies.get('csrftoken')
                return True
            else:
                raise ValueError
        else:
            if login_params['two_factor'] is None:
                body = json.dumps({'email':login_params['username'], 'password':login_params['password']})
                full_api_path = f"{self.BASE_URL}{api_path}"
                response = requests.post(full_api_path,data=body,headers={'Content-Type':'application/json'})
                if response.status_code == 200:
                    full_api_path += '/two_factor'
                    two_factor = input('Enter the two factor code:')
                    body = json.dumps({'two_factor':two_factor})
                    response = requests.post(full_api_path,data=body,headers={'Content-Type':'application/json'})
                    if response.status_code == 200:
                        self.headers['X-CSRFTOKEN'] = response.cookies.get('csrftoken')
                        self.cookies['sessionid'] = response.cookies.get('sessionid')
                        self.cookies['csrftoken'] = response.cookies.get('csrftoken')
                        return True
                    else:
                        raise ValueError
                else:
                    raise ValueError
            else:
                body = json.dumps({'email':login_params['username'], 'password':login_params['password'], 'two_factor':login_params['two_factor']})
                full_api_path = f"{self.BASE_URL}{api_path}"
                response = requests.post(full_api_path,data=body,headers={'Content-Type':'application/json'})
                if response.status_code == 200:
                    self.headers['X-CSRFTOKEN'] = response.cookies.get('csrftoken')
                    self.cookies['sessionid'] = response.cookies.get('sessionid')
                    self.cookies['csrftoken'] = response.cookies.get('csrftoken')
                    return True
                else:
                    raise ValueError

    def populate_site_id_dict(self):
        sites = self.get_sites(self.org_id)
        for site in sites:
            self.sites[site['name']] = site['id']

    def save_org_id_by_name(self, org_name:str):
        login_response = self.check_login()
        for scope in login_response['privileges']:
            if scope['scope'] == 'org' and scope['name'] == org_name:
                self.org_id = scope['org_id']
                break
        if self.org_id == '':
            raise ValueError('org name not found in orgs that you manage.') 

    def _login_oauth2(self, login_params:Dict[str,str]) -> bool:
        pass

    def get_mist_edges_stats(self, org_id:str) -> str:

        return self._action_api_endpoint('mxedges_stats',[org_id])

    def get_mist_edge_stats(self,org_id:str,mist_edge_id:str) -> str:

        return self._action_api_endpoint("mxedge_stats",[org_id,mist_edge_id])

    def check_login(self) -> str:

        return self._action_api_endpoint('check_login',[])
            
    def get_mist_edge_events(self) -> str:

        return self._action_api_endpoint('mxedge_events',[])

    def get_org_ids(self) -> Dict[str,str]:
    
        privileges = self.check_login()
        return {privilege['name']:privilege['org_id'] for privilege in privileges}
                    
    def get_sites(self, org_id:str) -> Dict[str,str]:

        return self._action_api_endpoint('sites',[org_id])

    def create_site(self, org_id:str, site_info:Dict[str,str]) -> Dict[str,str]:

        return self._action_api_endpoint('sites',[org_id],call_body=site_info,action='post')        

    def delete_site(self, site_id:str) -> Dict[str, str]:

        return self._action_api_endpoint('site',[site_id],action='delete')

    def update_site(self, site_id:str, site_info:Dict[str,str]) -> Dict[str,str]:

        return self._action_api_endpoint('site',[site_id],call_body=site_info,action='put')

    def get_site_devices(self, site_id:str) -> Dict[str,str]:

        return self._action_api_endpoint('site_devices', [site_id])

    def config_site_device(self, site_id:str, device_id:str, device_info: Dict) -> Dict[str, str]:

        return self._action_api_endpoint('device_config', [site_id, device_id], call_body=device_info, action='put')

    def get_inventory(self, org_id:str = '') -> Dict[str,str]:

        return self._action_api_endpoint('inventory',[org_id if org_id != '' else self.org_id])

    def add_inventory_to_org(self, org_id:str, inventory_info:Dict[str,str]) -> Dict[str,str]:
        """
        [
            CLAIM-CODE01,
            CLAIM-CODE02,
            ...
        ]
        """
        return self._action_api_endpoint('inventory', [org_id], call_body=inventory_info, action='post')

    def assign_inventory_to_site(self, inventory_info:Dict[str,str], org_id:str='') -> Dict[str, str]:
        """
        {
            "op" : "assign",
            "site-id" : str,
            "macs": list[str], no delimiter for macs
            "no_reassign" : bool, if true, treat site assignment against an already assigned AP as error
            "disable_auto_config" : bool, for cloud-ready switch/gateway. Mist will not manage switch/gateway if true
            "managed" : bool, for adopted switch/gateway Mist will NOT manage by default, this enables Mist mgmt
        }
        """

        return self._action_api_endpoint('inventory', [org_id if org_id != '' else self.org_id], call_body=inventory_info, action='put')

    def unassign_inventory_from_site(self, org_id:str, inventory_info:Dict[str,str]) -> Dict[str,str]:
        """
        {
            "op" : "unassign",
            "macs" : list[str], no delimiter for macs
        }
        """

        return self._action_api_endpoint('inventory', [org_id], call_body=inventory_info, action='put')

    def update_device_config(self, site_id:str, device_id:str, device_config:Dict[str,str]) -> Dict[str,str]:

        return self._action_api_endpoint('device_config',[site_id,device_id],device_config,action='put')

    def bounce_tunterm_data_ports(self, org_id:str, mxedge_id:str) -> Dict[str, str]:

        return self._action_api_endpoint('bounce_tunterm_data_ports', [org_id, mxedge_id], action='post')

    def restart_mistedge(self, org_id:str, mxedge_id:str) -> Dict[str, str]:

        return self._action_api_endpoint('mistedge_restart', [org_id, mxedge_id], action='post')

    def claim_mistedge(self, org_id:str, claim_code:Dict[str,str]) -> Dict[str, str]:
        """ 
        {
            "code" : "135-145-678"
        }
        """
        return self._action_api_endpoint('claim_mistedge', [org_id], call_body=claim_code, action='post')

    def assign_mistedge_to_site(self, org_id:str, site_info:Dict[str, str]) -> Dict[str, str]:
        """
        {
            "site_id" : "4ac1dcf4-9d8b-7211-65c4-057819f0862b",
            "mxedge_ids" : ["387804a7-3474-85ce-15a2-f9a9684c9c90"]
        }
        """

        return self._action_api_endpoint("assign_mistedge_to_site", [org_id], call_body=site_info, action='post')

    def create_mistedge(self, org_id:str, mistedge_info:Dict[str,str]) -> Dict[str, str]:
        """
        {
            "name" : str,
            "model" : str,
            "services" : list[str] *** tunterm is only service currently supported,
            "versions" : object
                "mxagent" : str,
                "tunterm" : str
            "ntp_servers" : list[str],
            "mxedge_mgmt" : object,
            "oob_ip_config" : object,
                "type" : "static" || "dhcp",
                "ip" : str,
                "netmask": str,
                "gateway" : str,
                "dns" : list[str]
            "proxy" : object,
            "tunterm_ip_config" : object,
                "ip" : str,
                "netmask" : str,
                "gateway" : str
            "tunterm_other_ip_configs" : object,
                "ip" : str,
                "netmask" : str
            "tunterm_port_config": object
                "separate_upstream_downstream" : boolean, default = false,
                "downstream_ports" : list[str], 0, 1, 2, 3 allowed
                "upstream_ports" : list[str], 0, 1, 2, 3 allowed
                "upstream_port_vlan_id" : int
            "tunterm_switch_config" : object
                "enabled" : boolean, default = fase,
                "0" : object
                    "vlan_ids" : list[int],
                    "port_vlan_id" : int || None,
            "tunterm_dhcpd_config" : object,
                "type" : "relay",
                "enabled" boolean, default = false,
                "servers" : list[str],
            "tunterm_igmp_snooping_config" : object,
                "enabled" : boolean, defualt=false,
                "vlan_ids" : list[int],
                "querier.query_interval" : int,
                "querier.max_response_time" : int,
                "querier.robustness" : int [1-7],
                "querier.version" : int,
                "querier.mtu" : int
            "mxlcuster_id" : str
        }
        """

        return self._action_api_endpoint("create_mistedge", [org_id], call_body=mistedge_info, action="post")

    def get_mistedge_models(self) -> Dict[str, str]:

        return self._action_api_endpoint('get_mxedge_models', [])

    def get_mxedge_clusters(self, org_id:str) -> Dict[str, str]:

        return self._action_api_endpoint('get_mxedge_clusters', [org_id])

    def create_site_group(self, org_id:str, site_group_info:Dict[str,str]) -> Dict[str, str]:
        """
        {
            "name" : str
        }
        """
        return self._action_api_endpoint('site_group', [org_id], call_body=site_group_info, action='post')

    def get_org_wlans(self, org_id:str) -> Dict[str, str]:
        
        return self._action_api_endpoint('wlans', [org_id])

    def import_map(self, site_id:str, map, headers:Dict) -> Dict[str, str]:

        return self._action_api_endpoint('import_map', [site_id], call_body=map, action='post', multi=True, custom_headers=headers)


    def _action_api_endpoint(self, api_endpoint:str, api_params:list[str], call_body:Dict[str,str]={}, action:str='get', multi:bool=False, custom_headers:Dict={}) -> Dict[str,str]:
        
        full_api_path = self._make_full_api_uri(api_endpoint, api_params)
        if multi:
            return self._make_multi_api_call(full_api_path, call_body, custom_headers)
        else:
            return self._make_api_call(full_api_path, call_body, action)

    def _make_full_api_uri(self, api_endpoint:str, api_params:list[str]) -> str:

        if api_endpoint in self.api_endpoints:
            api_path = self.api_endpoints[api_endpoint].format(*api_params)
            full_api_path = f"{self.BASE_URL}{api_path}"
            return full_api_path
        else:
            raise ValueError(f"The API endpoint is not currently supported. Add it to the api_endpoints list and try again.")
    
    def _make_multi_api_call(self, full_api_path:str, call_body, headers:Dict) -> Dict[str,str]:
        headers['X-CSRFTOKEN'] = self.headers['X-CSRFTOKEN']
        response = requests.request('post', full_api_path, data=call_body, headers=headers, cookies=self.cookies)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Request failed: {response.status_code} {response.reason}")

    def _make_api_call(self, full_api_path:str, call_body:Dict[str,str], action:str) -> Dict[str,str]:

        if action != 'get' or action != 'delete':
            data = json.dumps(call_body)
            response = requests.request(action,full_api_path,data=data,headers=self.headers,cookies=self.cookies)
        else:
            response = requests.request(action,full_api_path,headers=self.headers,cookies=self.cookies)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Request failed: {response.status_code} {response.reason}")