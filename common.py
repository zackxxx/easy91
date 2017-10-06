import os
import configparser


def dd(content):
    print(type(content))
    print(content)
    exit(1)


def get_config(*config_key):
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_path)
    return config.get(*config_key)
