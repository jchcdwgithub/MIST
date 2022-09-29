import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from api import MistAPIHandler
import tasks
from file_ops import ConfigReader, ExcelWriter, EkahauWriter

def main():
    
    config_reader = ConfigReader('config.yml')
    config = config_reader.extract_information_from_file()

    esx_writer = EkahauWriter(config)

    task_manager = tasks.TaskManager(config=config, handler=MistAPIHandler, writer=ExcelWriter, esx_writer=esx_writer)
    print('creating tasks...')
    task_manager.create_tasks()
    print('executing tasks...')
    task_manager.execute_tasks()

    if 'assign ap' in task_manager.tasks or 'name ap' in task_manager.tasks:
        print('saving executed tasks to file...')
        task_manager.save_success_configs_to_file()
    print('finished.')

if __name__ == '__main__':
    main()