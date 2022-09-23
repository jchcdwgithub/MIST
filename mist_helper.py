import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from api import MistAPIHandler
import tasks
from file_ops import ConfigReader, ExcelWriter

def main():
    
    config_reader = ConfigReader('config.yml')
    config = config_reader.extract_information_from_file()

    task_manager = tasks.TaskManager(config=config, handler=MistAPIHandler, writer=ExcelWriter)
    print('creating tasks...')
    task_manager.create_tasks()
    print('executing tasks...')
    task_manager.execute_tasks()
    print('saving executed tasks to file...')
    task_manager.save_success_configs_to_file()
    print('finished.')

if __name__ == '__main__':
    main()