import os
import json
from datetime import datetime, timedelta

dt_format = '%Y-%m-%d_%H-%M-%S'
directory = './cache'

if not os.path.exists(directory):
    os.makedirs(directory)

def get_cache():
    directory_files = os.listdir(directory)

    try:
        last = sorted(directory_files)[-1]
        last_time = datetime.strptime(last.strip('.json'), dt_format)
    except IndexError:
        last = None
        last_time = datetime.min

    current_time = datetime.now()
    time_difference = abs(current_time - last_time)

    if time_difference <= timedelta(hours=1):
        with open(os.path.join(directory, last)) as file:
            return json.load(file)
    else:
        return None

def set_cache(data):
    current_time = datetime.now()

    file_name = f'{current_time.strftime(dt_format)}.json'
    file_path = os.path.join(directory, file_name)
    
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)