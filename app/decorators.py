from functools import wraps
from flask import flash, redirect, url_for, current_app
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Por favor, faça login para acessar esta página.", "info")
            return redirect(url_for('main.login', next=request.url))
        if getattr(current_user, 'user_type', 'user') != 'admin': # getattr para o caso de current_user ser anônimo
            flash("Você não tem permissão para acessar esta página.", "danger")
            return redirect(url_for('main.index')) # Ou uma página de erro 403
        return f(*args, **kwargs)
    return decorated_function
