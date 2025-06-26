import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env no diretório raiz do projeto
# (um nível acima de onde config.py está, se config.py estiver em um subdiretório como 'app')
# Se config.py está na raiz, então .env na raiz é carregado.
# Ajuste o path se necessário. Se run.py está na raiz e importa 'app', e 'app' importa 'config',
# o diretório de trabalho é a raiz.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Se config.py está em 'app/'
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env') # Se config.py está na raiz

load_dotenv(dotenv_path=dotenv_path, override=True)

class Config:
    """Configurações base do aplicativo."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-dificil-de-adivinhar'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # Configurações do SQLAlchemy (movidas para create_app para usar instance_path)
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #     f"sqlite:///{os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'site.db')}"
    # SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configurações do Flask-Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.example.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'seu-email@example.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'sua-senha'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or MAIL_USERNAME

    # Configurações de Segurança
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true' # True em produção
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax') # 'Lax' ou 'Strict'
    REMEMBER_COOKIE_SECURE = True # True em produção
    REMEMBER_COOKIE_HTTPONLY = True

    # Configurações específicas da aplicação
    CONFIRMATION_TOKEN_MAX_AGE = 3600  # 1 hora para expiração do token de confirmação
    LOGIN_SESSION_MAX_AGE_HOURS = 24 # 24 horas para expiração da sessão de login/liberação de IP

    # Firewall (apenas informativo, a lógica real estará em outro lugar)
    FIREWALL_TYPE = os.environ.get('FIREWALL_TYPE', 'ufw') # 'ufw' ou 'iptables'

    # Para run.py (SSL)
    FLASK_USE_SSL = os.environ.get('FLASK_USE_SSL', 'false').lower() == 'true'
    SSL_CERT_PATH = os.environ.get('SSL_CERT_PATH', 'cert.pem')
    SSL_KEY_PATH = os.environ.get('SSL_KEY_PATH', 'key.pem')

    # Credenciais do Administrador (lidas do .env)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    ADMIN_NOTIFICATIONS_EMAIL = os.environ.get('ADMIN_NOTIFICATIONS_EMAIL', ADMIN_EMAIL) # Default para o email do admin


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False # Permitir HTTP para desenvolvimento
    REMEMBER_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    # Em produção, SECRET_KEY, senhas de e-mail/DB devem vir de variáveis de ambiente ou secrets manager.

# Adicionar mais configurações para diferentes ambientes (Testing, etc.) se necessário.

# Para selecionar a configuração:
# config_name = os.getenv('FLASK_CONFIG') or 'default'
# if config_name == 'development':
#     app.config.from_object(DevelopmentConfig)
# else:
#     app.config.from_object(ProductionConfig)
# No __init__.py, `app.config.from_object('config.Config')` carrega a classe base.
# Poderia ser `app.config.from_object(os.environ.get('APP_CONFIG_FILE', 'config.DevelopmentConfig'))`
# Mas por simplicidade, vamos usar a classe Config e controlar o DEBUG via FLASK_DEBUG.
# A classe Config já lê muitas de suas configurações de variáveis de ambiente.
