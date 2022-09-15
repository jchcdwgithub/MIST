from typing import Dict, List
import pandas

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