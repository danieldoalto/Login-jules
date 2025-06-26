import yaml
import os
from flask import current_app

DEFAULT_CONFIG_PATH = 'config.yml'

def load_link_config(path=None):
    """
    Carrega a configuração de links dinâmicos de um arquivo YAML.
    O caminho do arquivo é relativo à raiz da aplicação.
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH

    if path is None:
        # Este caso não deveria acontecer se chamado de __init__.py com o path explícito.
        # Mas se chamado diretamente sem path, tentaria o default.
        if current_app:
            path = os.path.join(current_app.root_path, DEFAULT_CONFIG_PATH)
        else: # Fallback ainda mais genérico, pode não ser ideal.
            project_root_guess = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            path = os.path.join(project_root_guess, DEFAULT_CONFIG_PATH)
            print(f"Warning: load_link_config chamado sem path e sem current_app. Tentando: {path}")

    absolute_path = path # O path fornecido por __init__.py já será absoluto.

    config_data = {
        'admin_links': [],
        'user_links': []
    }

    if not os.path.exists(absolute_path):
        if current_app:
            current_app.logger.warning(f"Arquivo de configuração de links '{absolute_path}' não encontrado. Usando links vazios.")
        else:
            print(f"Warning: Arquivo de configuração de links '{absolute_path}' não encontrado. Usando links vazios.")
        return config_data

    try:
        with open(absolute_path, 'r', encoding='utf-8') as f:
            loaded_yaml = yaml.safe_load(f)
            if loaded_yaml: # Verifica se o arquivo não está vazio
                config_data['admin_links'] = loaded_yaml.get('admin_links', [])
                config_data['user_links'] = loaded_yaml.get('user_links', [])
            else: # Arquivo YAML vazio
                if current_app:
                    current_app.logger.warning(f"Arquivo de configuração de links '{absolute_path}' está vazio. Usando links vazios.")
                else:
                    print(f"Warning: Arquivo de configuração de links '{absolute_path}' está vazio. Usando links vazios.")

    except yaml.YAMLError as e:
        if current_app:
            current_app.logger.error(f"Erro ao parsear o arquivo YAML de links '{absolute_path}': {e}. Usando links vazios.")
        else:
            print(f"Error: Erro ao parsear o arquivo YAML de links '{absolute_path}': {e}. Usando links vazios.")
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Erro inesperado ao carregar o arquivo de links '{absolute_path}': {e}. Usando links vazios.")
        else:
            print(f"Error: Erro inesperado ao carregar o arquivo de links '{absolute_path}': {e}. Usando links vazios.")

    return config_data
