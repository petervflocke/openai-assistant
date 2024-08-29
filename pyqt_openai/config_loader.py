import configparser
import os

import yaml

from pyqt_openai import CONFIG_DATA, INI_FILE_NAME

_config_cache = None


def parse_value(value):
    # Boolean conversion
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    # Numeric conversion
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            pass
    # Default: return the value as is (string)
    return value


def convert_list(value):
    # Convert comma-separated string to list
    return [item.strip() for item in value.split(',')]


def ini_to_yaml():
    ini_old_filename = 'pyqt_openai.ini'
    if os.path.exists(ini_old_filename):
        ini_new_filename = 'config.ini'
        if os.path.exists(ini_old_filename):
            os.rename(ini_old_filename, ini_new_filename)

        # Open INI file
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(ini_new_filename)

        # Convert to yaml data
        yaml_data = {}
        for section in config.sections():
            yaml_data[section] = {}
            for key, value in config.items(section):
                if key in ['chat_column_to_show', 'image_column_to_show']:
                    yaml_data[section][key] = convert_list(value)
                else:
                    yaml_data[section][key] = parse_value(value)

        os.remove(ini_new_filename)
    else:
        yaml_data = CONFIG_DATA

    yaml_filename = INI_FILE_NAME
    if not os.path.exists(yaml_filename):
        # Save as YAML file
        with open(yaml_filename, 'w') as yaml_file:
            yaml.dump(yaml_data, yaml_file, default_flow_style=False)
    else:
        with open(yaml_filename, 'r') as yaml_file:
            prev_yaml_data = yaml.safe_load(yaml_file)
        # Add new keys
        for section, values in yaml_data.items():
            if section not in prev_yaml_data:
                prev_yaml_data[section] = values
            else:
                for key, value in values.items():
                    if key not in prev_yaml_data[section]:
                        prev_yaml_data[section][key] = value
        # Save as YAML file
        with open(yaml_filename, 'w') as yaml_file:
            yaml.dump(prev_yaml_data, yaml_file, default_flow_style=False)


class ConfigManager:
    def __init__(self, yaml_file=INI_FILE_NAME):
        self.yaml_file = yaml_file
        self.config = self._load_yaml()

    def _load_yaml(self):
        with open(self.yaml_file, 'r') as file:
            return yaml.safe_load(file)

    def _save_yaml(self):
        with open(self.yaml_file, 'w') as file:
            yaml.safe_dump(self.config, file)

    # Getter methods
    def get_dalle(self):
        return self.config.get('DALLE', {})

    def get_general(self):
        return self.config.get('General', {})

    def get_replicate(self):
        return self.config.get('REPLICATE', {})

    def get_dalle_property(self, key):
        return self.config.get('DALLE', {}).get(key)

    def get_general_property(self, key):
        return self.config.get('General', {}).get(key)

    def get_replicate_property(self, key):
        return self.config.get('REPLICATE', {}).get(key)

    # Setter methods
    def set_dalle_property(self, key, value):
        if 'DALLE' not in self.config:
            self.config['DALLE'] = {}
        self.config['DALLE'][key] = value
        self._save_yaml()

    def set_general_property(self, key, value):
        if 'General' not in self.config:
            self.config['General'] = {}
        self.config['General'][key] = value
        self._save_yaml()

    def set_replicate_property(self, key, value):
        if 'REPLICATE' not in self.config:
            self.config['REPLICATE'] = {}
        self.config['REPLICATE'][key] = value
        self._save_yaml()


ini_to_yaml()
CONFIG_MANAGER = ConfigManager()
# print(CONFIG_MANAGER.get_general_property('API_KEY'))