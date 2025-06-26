from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_login import LoginManager # Adicionado LoginManager
import os

db = SQLAlchemy()
mail = Mail()
bcrypt = Bcrypt()
login_manager = LoginManager() # Instância do LoginManager
# Configurações do LoginManager (podem ser feitas aqui ou dentro de create_app)
login_manager.login_view = 'main.login' # Rota para a qual usuários não logados são redirecionados
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'


def create_app(config_class_string='config.Config'):
    app = Flask(__name__, instance_relative_config=True)

    # Configurações do App
    # app.config.from_object('config.Config') # Alterado para ser mais flexível
    app.config.from_object(config_class_string)

    # Cria a pasta instance se não existir (Flask faz isso automaticamente para instance_path)
    # No entanto, é bom garantir se formos colocar o DB lá explicitamente antes do init_app
    try:
        if not os.path.exists(app.instance_path):
            os.makedirs(app.instance_path)
    except OSError:
        pass

    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'site.db')}"
    # SQLALCHEMY_TRACK_MODIFICATIONS é geralmente definido em config.py ou False por padrão em versões recentes
    if 'SQLALCHEMY_TRACK_MODIFICATIONS' not in app.config:
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Carregar links dinâmicos do config.yml
    from .config_loader import load_link_config
    # Passar app.root_path explicitamente para garantir o caminho correto
    # durante a inicialização, antes que o contexto da aplicação esteja totalmente ativo para current_app.
    # No entanto, load_link_config foi escrito para tentar usar current_app.root_path,
    # que deve estar disponível neste ponto de create_app.
    # Se current_app.root_path não for confiável aqui, teríamos que fazer:
    # app.config['DYNAMIC_LINKS'] = load_link_config(path=os.path.join(app.root_path, 'config.yml'))
    # Mas vamos confiar que current_app.root_path é acessível ou que o fallback em load_link_config funciona.
    # Para ser mais explícito e seguro:
    config_file_path = os.path.join(app.root_path, 'config.yml')
    app.config['DYNAMIC_LINKS'] = load_link_config(path=config_file_path)
    if not app.config['DYNAMIC_LINKS']['admin_links'] and not app.config['DYNAMIC_LINKS']['user_links']:
        app.logger.info("Nenhum link dinâmico foi carregado. Verifique config.yml ou logs anteriores.")
    else:
        app.logger.info(f"Links dinâmicos carregados: {len(app.config['DYNAMIC_LINKS']['admin_links'])} grupos de admin, {len(app.config['DYNAMIC_LINKS']['user_links'])} grupos de usuário.")


    # CSRF Protection (Flask-WTF)
    # Se SECRET_KEY estiver definida, a proteção CSRF é habilitada por padrão para todos os formulários FlaskForm.
    # Não é necessário um app.extensions['csrf'] = CSRFProtect(app) explícito a menos que queira configurar.
    # A SECRET_KEY já é carregada de config.Config.

    # Importar modelos para que o SQLAlchemy os conheça
    from . import models

    with app.app_context():
        from .routes import main_bp
        app.register_blueprint(main_bp)

        # Comandos CLI
        from .commands import register_commands
        register_commands(app)

    return app
