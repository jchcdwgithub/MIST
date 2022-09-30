from math import floor
from typing import Dict, List, Tuple
from zipfile import ZipFile
import json
import shutil
import pandas
import yaml
import re
import os
import copy

class IOReader:
    def __init__(self, file:str):
        try:
            with open(file) as f:
                pass
        except:
            raise IOError('Could not open file. Check the path/name.')

class ExcelReader(IOReader):
    def __init__(self, file:str):
        super().__init__(file)
        self.file = file

    def extract_table_from_file(self, headers:List[str], dropset:List[str] = [], groupby:str = '', worksheet:str='') -> List[List[str]]:
        if worksheet != '':
            ex_excel = pandas.read_excel(rf'{self.file}', sheet_name=worksheet)
        else:
            ex_excel = pandas.read_excel(rf'{self.file}')
        to_process = ex_excel.dropna(subset=['New WAP \nMAC Address']) if dropset != '' else ex_excel
        values = to_process.loc[:,headers].groupby(groupby) if groupby != '' else to_process[:,headers]
        return values

class ConfigReader(IOReader):
    def __init__(self, file:str):
        super().__init__(file)
        self.file = file
        self.process_tasks = [self._rename_site_keys_with_unique_names]

    def extract_information_from_file(self):
        
        with open('config.yml') as f:
            config_lines = f.read()
            for task in self.process_tasks:
                config_lines = task(config_lines)
            config = yaml.load(config_lines, Loader=yaml.Loader)
            return config

    def _rename_site_keys_with_unique_names(self, config_lines:str) -> str:

        current_index = 0
        site_match = re.compile(r'site:')
        num_matches = len(site_match.findall(config_lines))
        while current_index < num_matches:
            config_lines = config_lines.replace('site:', f'site{current_index}:',1)
            current_index += 1
        return config_lines

class Writer:

    def __init__(self):
        pass

    def write_results_to_files(site:Dict[str, Dict[str, List[str]]], site_id:str):
        success_filename = f'assigned_aps_{site_id}.txt'
        error_filename = f'unassigned_aps_{site_id}.txt'
        with open(success_filename, 'a+') as assigned_aps_f, open(error_filename, 'a+') as unassigned_aps_f:
            lines = []
            unassigned_lines = []
            success = site['success']                
            error = site['error']

            lines.append(f'{site[0].upper()}\n')
            for ap_mac in success:
                lines.append(f'{ap_mac}\n')
            assigned_aps_f.writelines(lines)

            if len(error) > 0:
                unassigned_lines.append(f'{site[0].upper()}\n')
                for ap_mac in error:
                    lines.append(f'{ap_mac}\n')
                unassigned_aps_f.writelines(unassigned_lines)

class ExcelWriter:

    task_headers = {
        'assign ap' : ['MAC'],
        'name ap' : ['AP Name', 'MAC'],
        'rename esx ap': ['Ekahau File'],
        'create per floor esx files' : ['Files'],
    }

    def __init__(self, results:Dict, site_name_to_id:Dict, name_association:Dict[str, str]):
        self.results = results
        self.sn_to_id = site_name_to_id
        self.name_assoc = name_association

    def write_success_configs_to_file(self):
        for result in self.results:
            sheet_name = result['task']
            for key in result:
                if key != 'task':
                    site_name = key
                    out_filename = f'{self.sn_to_id[self.name_assoc[site_name]]}.xlsx'
                    full_outfile_path = os.path.join(os.getcwd(), 'data', out_filename)
                    success_data = result[site_name]['success']
                    self.write_success_data_to_worksheet(sheet_name, success_data, full_outfile_path)

    def write_success_data_to_worksheet(self, sheet_name:str, success_data:List, out_filename:str):
        dataframe = pandas.DataFrame(data=success_data, columns=self.task_headers[sheet_name])
        if os.path.exists(out_filename):
            with pandas.ExcelWriter(out_filename, mode='a', if_sheet_exists='overlay') as writer:
                if sheet_name in writer.sheets:
                    current_df = pandas.read_excel(out_filename, sheet_name=sheet_name)
                    current_values = current_df.values.tolist()
                    column_names = current_df.columns.values.tolist() 
                    to_write_values = dataframe.values.tolist()
                    new_values = to_write_values.copy()
                    for value in to_write_values:
                        if value in current_values:
                            new_values.remove(value)
                    dataframe = pandas.DataFrame(data=new_values, columns=column_names)
                    dataframe.to_excel(writer, sheet_name=sheet_name, startrow=writer.sheets[sheet_name].max_row, header=None, index=False)
                else:
                    dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            dataframe.to_excel(out_filename, sheet_name=sheet_name, index=False)

class EkahauWriter:

    def __init__(self, config:Dict):
        self.config = config

    def replace_ap_names_in_esx_file(self, esx_filepath:str):

        esx_to_final_naming = self.create_ap_naming_dict()
        site_name = esx_filepath[:len(esx_filepath)-4].split('\\')[-1]
        if site_name in esx_to_final_naming:
            esx_to_final_naming_ds = esx_to_final_naming[site_name]

        with ZipFile(esx_filepath, 'a') as zf:
            with zf.open('accessPoints.json') as ap_f:
                esx_aps = json.loads(ap_f.read()) 
                for ap in esx_aps['accessPoints']:
                    if ap['name'] in esx_to_final_naming_ds:
                        ap['name'] = esx_to_final_naming_ds[ap['name']]
            zf.writestr('accessPoints.json', json.dumps(esx_aps)) 

    def copy_esx_file(self, esx_filepath:str, new_filename:str='- Copy') -> str:
        
        old_filename = esx_filepath
        new_filename = old_filename[:len(old_filename)-4] + f' {new_filename}.esx'
        shutil.copyfile(old_filename, new_filename)
        return new_filename

    def rename_esx_file(self, esx_filepath:str) -> Tuple[str, str]:

        base_filename = esx_filepath[:len(esx_filepath)-3]
        esx_old_filepath = base_filename + 'esx'
        esx_new_filepath = base_filename + 'zip'
        os.rename(esx_old_filepath, esx_new_filepath)
        return (esx_old_filepath, esx_new_filepath)

    def create_ap_naming_dict(self, floor_dependent_naming:bool=False) -> Dict[str, str]:
        excel_filepath = self.config['sites']['ap_excel_file']
        sheet_name = self.config['sites']['sheet_name']
        lowercase_name = self.config['sites']['lowercase_ap_names']
        excel_columns_to_read = [
            self.config['sites']['header_column_names']['esx_ap_name'],
            self.config['sites']['header_column_names']['ap_name']
            ]
        site_column = self.config['sites']['header_column_names']['site']
        df = pandas.read_excel(excel_filepath, sheet_name=sheet_name)
        df_without_empty_names = df.dropna(subset=['New WAP Name'])
        if floor_dependent_naming:
            excel_columns_to_read.append(site_column)
            values = df_without_empty_names.loc[:,excel_columns_to_read].groupby(site_column)
        else:
            values = df_without_empty_names.loc[:,excel_columns_to_read]
        ap_naming_dict = {}
        for name, group in values:
            ap_naming_dict[name] = {}
            for item in group.values:
                if floor_dependent_naming:
                    esx_name, final_name, _ = item
                else:
                    esx_name, final_name = item
                ap_naming_dict[name][esx_name] = final_name.lower() if lowercase_name else final_name
        return ap_naming_dict

    def rename_aps_floor_dependent(self, esx_filepath:str):
        ap_naming_dict = self.create_ap_naming_dict(floor_dependent_naming=True)
        new_esx_filepath = self.copy_esx_file(esx_filepath)
        with ZipFile(new_esx_filepath, 'a') as zf:
            with zf.open('floorPlans.json', 'r') as fp_f:
                fp_json = json.loads(fp_f.read())
                floorplan_name = {fp['id']:fp['name'] for fp in fp_json['floorPlans']}
            with zf.open('accessPoints.json', 'r') as ap_f:
                ap_json = json.loads(ap_f.read())
                for ap in ap_json['accessPoints']:
                    if 'location' in ap:
                        floor_name = floorplan_name[ap['location']['floorPlanId']]
                        try:
                            ap['name'] = ap_naming_dict[floor_name][ap['name']]
                        except KeyError:
                            print(f'found AP in esx file that is not in the excel sheet: {ap["name"]}')
                zf.writestr('accessPoints.json', json.dumps(ap_json))
        return ap_json

    def get_floorplan_json_from_file(self, esx_filepath:str) -> Dict[str, str]:
        with ZipFile(esx_filepath) as esx_f:
            with esx_f.open('floorPlans.json') as floorplan_f:
                floorplan_json = json.loads(floorplan_f.read())
                self.floorplan_name_id = floorplan_json
                return floorplan_json

    def create_floorplan_specific_esx_file(self, esx_filepath:str, floorplan_name:str, floorplan_id:str):
        esx_with_floorplan_only_filename = f' {floorplan_name}'
        new_filename = self.copy_esx_file(esx_filepath, esx_with_floorplan_only_filename)
        with ZipFile(new_filename, 'a') as esx_f:
            new_ap_json = self.remove_location_info_from_aps_not_on_floorplan(esx_f, floorplan_id)
            esx_f.writestr('accessPoints.json', json.dumps(new_ap_json)) 
            new_floorplan_json = self.remove_all_floorplans_except_current_floorplan(esx_f, floorplan_id)
            esx_f.writestr('floorPlans.json', json.dumps(new_floorplan_json))
            new_areas_json = self.remove_floorplan_from_areas(esx_f, floorplan_id)
            esx_f.writestr('areas.json', json.dumps(new_areas_json))
            new_exc_json = self.remove_floorplan_from_excluded_areas(esx_f, floorplan_id)
            esx_f.writestr('exclusionAreas.json', json.dumps(new_exc_json))
            esx_f.writestr('interferers.json', json.dumps({'interferers':[]}))
            self.remove_surveys_that_reference_current_floorplan(esx_f, new_filename, floorplan_id)
        os.remove(new_filename)

    def create_floorplan_specific_esx_data(self, data_structures:Tuple) -> List[Dict]:
        shared_files, floorplan_spec_files, survey_files = data_structures
        floorplans = {}
        aps = {}
        areas = {}
        exclusionAreas = {}
        
        for item in floorplan_spec_files:
            item_name = item['name']
            if item_name == 'floorPlans.json':
                floorplans = item
            elif item_name == 'accessPoints.json':
                aps = item
            elif item_name == 'areas.json':
                areas = item
            elif item_name == 'exclusionAreas.json':
                exclusionAreas = item

        floorplan_name_id = {floorplan['name']:floorplan['id'] for floorplan in floorplans['data']['floorPlans']}

        floorplans_spec_files = {}
        for floorplan in floorplan_name_id:
            floorplan_id = floorplan_name_id[floorplan]
            floorplans_copy = copy.deepcopy(floorplans) 
            new_floorplan_json = self.remove_all_floorplans_except_current_floorplan_(floorplans_copy, floorplan_id)        

            aps_copy = copy.deepcopy(aps) 
            new_ap_json = self.remove_location_info_from_aps_not_on_floorplan_(aps_copy, floorplan_id)

            areas_copy = copy.deepcopy(areas) 
            new_areas_json = self.remove_floorplan_from_areas_(areas_copy, floorplan_id)

            exc_areas_copy = copy.deepcopy(exclusionAreas) 
            new_exc_areas_json = self.remove_floorplan_from_excluded_areas_(exc_areas_copy, floorplan_id)

            survey_files_copy = copy.deepcopy(survey_files) 
            floorplan_only_surveys = self.remove_surveys_that_ref_current_floorplan(survey_files_copy, floorplan_id)
            floorplans_spec_files[floorplan] = shared_files + [new_floorplan_json, new_ap_json, new_areas_json, new_exc_areas_json] + floorplan_only_surveys
        
        return floorplans_spec_files

    def create_floorplan_specific_esx_file(self, esx_filepath:str, floorplan_name:str, esx_files:List[Dict]):
        esx_filepath_wo_ext = esx_filepath[:len(esx_filepath)-4]
        esx_with_floorplan_only_filename = f'{esx_filepath_wo_ext} {floorplan_name}.esx'
        with ZipFile(esx_with_floorplan_only_filename, 'w') as esx_f:
            for esx_file in esx_files:
                esx_f.writestr(esx_file['name'], esx_file['data'])

    def remove_surveys_that_reference_current_floorplan(self, esx_file_handler:ZipFile, new_filename:str, floorplan_id:str):
        survey_regex = re.compile(r'survey-.*\.json')
        with ZipFile(new_filename[:len(new_filename)-4]+'_.esx', 'w') as new_file:
            for item in esx_file_handler.infolist():
                if (survey_regex.match(item.filename)):
                    with esx_file_handler.open(item.filename) as survey_f:
                        survey_json = json.loads(survey_f.read())
                        for survey in survey_json['surveys']:
                            if survey['floorPlanId'] == floorplan_id:
                                new_file.writestr(item, json.dumps(survey_json))
                else:
                    buffer = esx_file_handler.read(item.filename)
                    new_file.writestr(item, buffer)

    def remove_surveys_that_ref_current_floorplan(self, survey_files:List[Dict], floorplan_id:str) -> List[Dict]:
        survey_files_copy = []
        for survey in survey_files:
            survey_data = survey['data']['surveys']
            for surv in survey_data:
                if surv['floorPlanId'] == floorplan_id:
                    survey_files_copy.append({'name':survey['name'], 'data':json.dumps(survey['data']).encode('utf-8')})
        return survey_files_copy

    def remove_location_info_from_aps_not_on_floorplan(self, esx_file_handler:ZipFile, floorplan_id:str):
        with esx_file_handler.open('accessPoints.json') as ap_f:
            ap_json = json.loads(ap_f.read())
            ap_json_copy = ap_json.copy()
            for ap in ap_json_copy['accessPoints']:
                if 'location' in ap and ap['location']['floorPlanId'] != floorplan_id:
                    ap.pop('location')
        return ap_json_copy

    def remove_location_info_from_aps_not_on_floorplan_(self, ap_json:Dict, floorplan_id:str) -> Dict:
        ap_json_copy = ap_json.copy()
        for ap in ap_json_copy['data']['accessPoints']:
            if 'location' in ap and ap['location']['floorPlanId'] != floorplan_id:
                ap.pop('location')
        ap_json_copy['data'] = json.dumps(ap_json_copy['data']).encode('utf-8')
        return ap_json_copy

    def remove_floorplan_from_areas(self, esx_file_handler:ZipFile, floorplan_id:str) -> Dict:
        with esx_file_handler.open('areas.json') as areas_f:
            areas_json = json.loads(areas_f.read())
            new_areas_json = {'areas':[]}
            for area in areas_json['areas']:
                if area['floorPlanId'] == floorplan_id:
                    new_areas_json['areas'].append(area)
        return new_areas_json

    def remove_floorplan_from_areas_(self, areas_json:Dict, floorplan_id:str) -> Dict:
        new_areas_json = {'areas':[]}
        for area in areas_json['data']['areas']:
            if area['floorPlanId'] == floorplan_id:
                new_areas_json['areas'].append(area)
        return {'name':areas_json['name'], 'data':json.dumps(new_areas_json).encode('utf-8')}


    def remove_floorplan_from_excluded_areas(self, esx_file_handler:ZipFile, floorplan_id:str) -> Dict:
        with esx_file_handler.open('exclusionAreas.json') as exc_areas_f:
            exc_areas_json = json.loads(exc_areas_f.read())
            new_exc_areas_json = {'exclusionAreas':[]}
            for exc_area in exc_areas_json['exclusionAreas']:
                if exc_area['floorPlanId'] == floorplan_id:
                    new_exc_areas_json['exclusionAreas'].append(exc_area)
        return new_exc_areas_json

    def remove_floorplan_from_excluded_areas_(self, exc_areas_json, floorplan_id:str) -> Dict:
        new_exc_areas_json = {'exclusionAreas':[]}
        for exc_area in exc_areas_json['data']['exclusionAreas']:
            if exc_area['floorPlanId'] == floorplan_id:
                new_exc_areas_json['exclusionAreas'].append(exc_area)
        return {'name':exc_areas_json['name'], 'data': json.dumps(new_exc_areas_json).encode('utf-8') }

    def remove_all_floorplans_except_current_floorplan(self, esx_file_handler:ZipFile, floorplan_id:str) -> Dict:
        with esx_file_handler.open('floorPlans.json') as floorplan_f:
            floorplan_json = json.loads(floorplan_f.read())
            filtered_floorplan = {'floorPlans':[]} 
            for floorplan in floorplan_json['floorPlans']:
                if floorplan['id'] == floorplan_id:
                    filtered_floorplan['floorPlans'].append(floorplan)
        return filtered_floorplan 

    def remove_all_floorplans_except_current_floorplan_(self, floorplan_json:Dict, floorplan_id:str) -> Dict:
        filtered_floorplan = {'floorPlans':[]} 
        for floorplan in floorplan_json['data']['floorPlans']:
            if floorplan['id'] == floorplan_id:
                filtered_floorplan['floorPlans'].append(floorplan)
        return {'name':floorplan_json['name'], 'data':json.dumps(filtered_floorplan).encode('utf-8') }

    def extract_info_from_esx_file(self, esx_filepath:str='') -> Tuple[List, List, List]:
        """
        Reads from an esx file and returns a 3-tuple of shared_files, floorplan_specific_files, survey_files.
        """
        shared_files = []
        floorplan_specific_files = []
        survey_files = []
        floorplan_specific_filenames = {'accessPoints.json', 'areas.json', 'exclusionAreas.json', 'floorPlans.json','interferers.json'}
        survey_regex = re.compile(r'survey-.*\.json')
        if esx_filepath == '':
            esx_filepath = self.config['sites']['esx_file']
        with ZipFile(esx_filepath, 'r') as zf:
            for item in zf.infolist():
                if item.filename in floorplan_specific_filenames:
                    with zf.open(item.filename) as item_f:
                        item_data = json.loads(item_f.read())
                        item_dict = {'name':item.filename, 'data': item_data}
                        floorplan_specific_files.append(item_dict)
                elif survey_regex.match(item.filename):
                    with zf.open(item.filename) as item_f:
                        item_data = json.loads(item_f.read())
                        item_dict = {'name':item.filename, 'data':item_data}
                        survey_files.append(item_dict)
                else:
                    buffer = zf.read(item.filename)
                    shared_files.append({'name':item.filename, 'data':buffer})
        return (shared_files, floorplan_specific_files, survey_files)