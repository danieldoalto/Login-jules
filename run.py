from app import create_app
import os
from dotenv import load_dotenv

# Carrega .env antes de qualquer outra coisa para garantir que as variáveis estejam disponíveis
# para config.py e create_app() se elas dependerem disso no momento da importação.
# Idealmente, config.py lida com o carregamento do .env.
# Se create_app() ou config.py não carregarem, podemos fazer aqui.
# Assumindo que config.py já chama load_dotenv(), esta linha pode ser redundante ou
# garantir que seja carregado se config.py não o fizer no contexto de execução de run.py.
# Vamos garantir que seja carregado.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("Arquivo .env não encontrado na raiz do projeto. Usando configurações padrão ou variáveis de ambiente existentes.")


# Determina qual classe de configuração usar com base na variável de ambiente
# FLASK_CONFIG pode ser 'config.DevelopmentConfig', 'config.ProductionConfig', etc.
# O padrão é 'config.Config' (que por sua vez lê de variáveis de ambiente)
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
