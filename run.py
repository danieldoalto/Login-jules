# --- Início da Aplicação ---
# 1. Carregar variáveis de ambiente do .env
# Esta é a primeira coisa a ser feita para garantir que todas as configurações
# subsequentes tenham acesso às variáveis de ambiente corretas.
# `override=True` garante que os valores do .env substituam os do shell.
from dotenv import load_dotenv
load_dotenv(override=True)

# 2. Importar e criar a aplicação Flask
from app import create_app
import os

# Determina qual classe de configuração usar com base na variável de ambiente
config_name = os.getenv('FLASK_CONFIG', 'config.Config')
app = create_app(config_class_string=config_name)


if __name__ == '__main__':
    # As configurações de SSL e porta agora são lidas de app.config,
    # que por sua vez são carregadas de config.Py e variáveis de ambiente.
    # Para desenvolvimento, podemos usar certificados autoassinados.
    # Certifique-se de que 'cert.pem' e 'key.pem' existam na raiz do projeto ou ajuste o caminho.
    # Você pode gerá-los com openssl:
    # openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

    use_ssl = app.config.get('FLASK_USE_SSL', False)
    ssl_context = None

    if use_ssl:
        cert_path = app.config.get('SSL_CERT_PATH', 'cert.pem')
        key_path = app.config.get('SSL_KEY_PATH', 'key.pem')

        # Verifica se os caminhos são relativos e os torna absolutos em relação à raiz do projeto
        # A raiz do projeto é o diretório onde run.py está.
        project_root = os.path.dirname(__file__)
        if not os.path.isabs(cert_path):
            cert_path = os.path.join(project_root, cert_path)
        if not os.path.isabs(key_path):
            key_path = os.path.join(project_root, key_path)

        if os.path.exists(cert_path) and os.path.exists(key_path):
            ssl_context = (cert_path, key_path)
            print(f"SSL Habilitado. Certificado: {cert_path}, Chave: {key_path}")
        else:
            print(f"AVISO: FLASK_USE_SSL é True, mas os arquivos de certificado/chave não foram encontrados em {cert_path} ou {key_path}.")
            print("Execute o servidor com HTTP.")
            use_ssl = False # Volta para HTTP se os arquivos não existirem

    port = int(app.config.get('FLASK_RUN_PORT', os.getenv('PORT', 5000))) # PORT para compatibilidade com Heroku etc.
    debug = app.config.get('DEBUG', False)
    host = app.config.get('FLASK_RUN_HOST', '0.0.0.0')

    print(f"Iniciando servidor em {'https://' if use_ssl and ssl_context else 'http://'}{host}:{port} com debug={debug}")

    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)
