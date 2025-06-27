from . import db, bcrypt # db e bcrypt objects from app/__init__.py
from flask_login import UserMixin # Importa UserMixin
from . import login_manager # Importa login_manager para o user_loader
from datetime import datetime, timedelta
import secrets

from flask import current_app

# Classe especial para representar o Admin em memória
class AdminUser(UserMixin):
    def __init__(self, email):
        self.id = email # Usar e-mail como ID para o admin do .env
        self.email = email
        self.user_type = 'admin'
        self.password_hash = None # Admin não tem hash de senha no DB
        self.is_approved = True # Admin é sempre aprovado
        self.email_confirmed = True # E-mail do Admin é considerado confirmado
        # Outros campos do modelo User podem ter valores padrão ou None
        self.current_logged_in_ip = None
        self.login_session_expiration = None
        self.email_confirm_token = None
        self.email_confirm_token_expiration = None
        self.created_at = None
        self.updated_at = None
        self.approved_by_email = None
        self.approved_at = None

    # UserMixin espera que is_active e is_anonymous sejam propriedades.
    # Para um admin logado, is_active é True e is_anonymous é False.
    # is_authenticated é True se o login foi bem-sucedido (Flask-Login lida com isso).

    # Se UserMixin não fornecer padrões adequados, podemos defini-los:
    # @property
    # def is_active(self):
    #     return True

    # @property
    # def is_anonymous(self):
    #     return False

    # def get_id(self): # Já fornecido por UserMixin se self.id estiver definido
    #     return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    """Carrega um usuário. Pode ser o Admin (do .env) ou um User (do DB)."""
    admin_email = current_app.config.get('ADMIN_EMAIL')
    if user_id == admin_email:
        return AdminUser(email=admin_email)

    # Tenta carregar como um ID numérico normal do banco de dados
    try:
        user_db_id = int(user_id)
        return User.query.get(user_db_id)
    except ValueError:
        # Se user_id não for o e-mail do admin nem um inteiro, não é um usuário válido conhecido.
        return None

class User(db.Model, UserMixin): # Herda de UserMixin
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True) # UserMixin espera um campo 'id' para usuários do DB
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True) # Nullable True para admin do .env sem hash no DB

    user_type = db.Column(db.String(20), default='user', nullable=False) # 'user' ou 'admin'
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    approved_by_email = db.Column(db.String(120), nullable=True) # E-mail do admin que aprovou
    approved_at = db.Column(db.DateTime, nullable=True)

    # Campos para confirmação de e-mail
    email_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    email_confirm_token = db.Column(db.String(100), unique=True, nullable=True)
    email_confirm_token_expiration = db.Column(db.DateTime, nullable=True)

    # Campos para gerenciamento de login e IP
    current_logged_in_ip = db.Column(db.String(45), nullable=True) # IPv4 ou IPv6
    login_session_expiration = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, password):
        """Gera e define o hash da senha usando bcrypt da app."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Verifica a senha fornecida contra o hash armazenado usando bcrypt da app."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def generate_email_confirmation_token(self, expires_in_seconds=None):
        """
        Gera um token para confirmação de e-mail.
        Usa a configuração CONFIRMATION_TOKEN_MAX_AGE do app se expires_in_seconds não for fornecido.
        """
        from flask import current_app
        if expires_in_seconds is None:
            expires_in_seconds = current_app.config.get('CONFIRMATION_TOKEN_MAX_AGE', 3600)

        self.email_confirm_token = secrets.token_urlsafe(32)
        self.email_confirm_token_expiration = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        return self.email_confirm_token

    def verify_email_confirmation_token(self, token):
        """Verifica o token de confirmação de e-mail."""
        if self.email_confirm_token == token and \
           self.email_confirm_token_expiration > datetime.utcnow():
            self.email_confirmed = True
            self.email_confirm_token = None # Token usado, invalidar
            self.email_confirm_token_expiration = None
            return True
        return False

    def update_login_session(self, ip_address, expires_in_hours=None):
        """
        Atualiza o IP logado e o tempo de expiração da sessão.
        Usa a configuração LOGIN_SESSION_MAX_AGE_HOURS do app se expires_in_hours não for fornecido.
        """
        from flask import current_app
        if expires_in_hours is None:
            expires_in_hours = current_app.config.get('LOGIN_SESSION_MAX_AGE_HOURS', 24)

        self.current_logged_in_ip = ip_address
        self.login_session_expiration = datetime.utcnow() + timedelta(hours=expires_in_hours)

    def clear_login_session(self):
        """Limpa os dados da sessão de login (IP e expiração)."""
        self.current_logged_in_ip = None
        self.login_session_expiration = None

    def is_login_session_valid(self, current_ip):
        """Verifica se a sessão de login atual é válida para o IP fornecido."""
        if self.current_logged_in_ip == current_ip and \
           self.login_session_expiration and \
           self.login_session_expiration > datetime.utcnow():
            return True
        # Se a sessão expirou, limpa os campos
        if self.login_session_expiration and self.login_session_expiration <= datetime.utcnow():
            self.clear_login_session()
            # db.session.commit() # O chamador deve lidar com o commit
        return False


class FirewallLog(db.Model):
    __tablename__ = 'firewall_log'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False) # IPv4 ou IPv6
    action = db.Column(db.String(10), nullable=False) # 'allow' ou 'deny'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Quem fez a ação, se logado

    user = db.relationship('User', backref='firewall_logs')

    def __repr__(self):
        return f"<FirewallLog {self.action} {self.ip_address} at {self.timestamp}>"
