from . import db, bcrypt # db e bcrypt objects from app/__init__.py
from flask_login import UserMixin # Importa UserMixin
from . import login_manager # Importa login_manager para o user_loader
from datetime import datetime, timedelta
import secrets

@login_manager.user_loader
def load_user(user_id):
    """Função callback para Flask-Login carregar um usuário pelo ID."""
    return User.query.get(int(user_id))

class User(db.Model, UserMixin): # Herda de UserMixin
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True) # UserMixin espera um campo 'id'
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

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
