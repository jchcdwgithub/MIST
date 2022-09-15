from typing import Dict, List
import pandas
import yaml
import re

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