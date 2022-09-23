from typing import Dict, List
import pandas
import yaml
import re
import os

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
        'name ap' : ['AP Name', 'MAC']
    }

    def __init__(self, results:Dict, site_name_to_id:Dict):
        self.results = results
        self.sn_to_id = site_name_to_id

    def write_success_configs_to_file(self):
        for result in self.results:
            sheet_name = result['task']
            for key in result:
                if key != 'task':
                    site_name = key
                    out_filename = f'{self.sn_to_id[site_name]}.xlsx'
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