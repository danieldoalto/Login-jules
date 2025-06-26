from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from .forms import RegistrationForm, LoginForm, generate_math_challenge
from .models import User
from . import db
from .email_utils import send_confirmation_email
from .firewall_utils import allow_ip, deny_ip # Importações do Firewall
from flask_login import login_user, logout_user, login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Por enquanto, uma página de boas-vindas simples.
    # Poderia ser app/templates/index.html
    return render_template('index.html', title="Página Inicial")


@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    math_error = None # Para erros específicos da verificação matemática não cobertos pelo WTForms

    if request.method == 'POST':
        expected_sum_from_session = session.get('math_expected_sum')
        user_math_answer = form.math_answer.data # Já é convertido para int pelo IntegerField

        if expected_sum_from_session is None:
            flash('Houve um problema com a verificação. Por favor, tente novamente.', 'danger')
            # Regenerar desafio para o GET
            num1, num2, new_expected_sum = generate_math_challenge()
            form.num1.data = num1
            form.num2.data = num2
            session['math_expected_sum'] = new_expected_sum
            return render_template('register.html', title='Registrar', form=form, math_error=math_error)

        if user_math_answer != expected_sum_from_session:
            math_error = "Resposta da verificação incorreta."
            # Os dados do formulário (e-mail, etc.) são preservados pelo WTForms

        # form.validate_on_submit() verifica CSRF e validadores dos campos.
        # Só prossegue para criar usuário se a matemática estiver correta E o resto do form for válido.
        if not math_error and form.validate_on_submit():
            try:
                user_email = form.email.data.lower()
                new_user = User(email=user_email)
                new_user.set_password(form.password.data)

                # Token de confirmação é gerado no modelo
                confirmation_token = new_user.generate_email_confirmation_token()

                db.session.add(new_user)
                db.session.commit()

                # Enviar e-mail de confirmação
                send_confirmation_email(user_email=new_user.email, token=confirmation_token)

                flash(f'Conta criada para {new_user.email}! Um e-mail de confirmação foi enviado. Por favor, verifique sua caixa de entrada (e pasta de spam).', 'success')
                session.pop('math_expected_sum', None) # Limpa o valor da sessão após uso
                return redirect(url_for('main.login')) # Redireciona para login ou uma página de "verifique seu e-mail"
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erro excepcional durante o registro de {form.email.data}: {e}")
                flash('Ocorreu um erro inesperado ao criar sua conta. Tente novamente mais tarde.', 'danger')
        else:
            # Se math_error ou form.errors (erros de validação do WTForms)
            if not math_error: # Se o erro não foi matemático, mas de validação do WTForms
                 flash('Por favor, corrija os erros destacados no formulário.', 'danger')
            # else: math_error será exibido no template

    # Método GET ou POST falhou (math_error ou form.errors)
    # Gerar (ou regenerar) números para o desafio matemático
    num1, num2, expected_sum = generate_math_challenge()
    form.num1.data = num1  # Para exibir a pergunta no template via {{ form.num1.data }}
    form.num2.data = num2  # Para exibir a pergunta no template via {{ form.num2.data }}
    session['math_expected_sum'] = expected_sum # Armazena a resposta correta na sessão para o POST

    return render_template('register.html', title='Registrar', form=form, math_error=math_error)


@main_bp.route('/confirm_email/<token>')
def confirm_email(token):
    if not token: # Embora a rota não corresponda sem token, é uma verificação extra.
        flash('Token de confirmação ausente ou inválido.', 'danger')
        return redirect(url_for('main.index'))

    user = User.query.filter_by(email_confirm_token=token).first()

    if user:
        if user.email_confirmed:
            flash('Esta conta já foi confirmada. Por favor, faça login.', 'info')
        elif user.verify_email_confirmation_token(token): # Valida token e expiração
            # O método verify_email_confirmation_token no modelo já define:
            # user.email_confirmed = True
            # user.email_confirm_token = None
            # user.email_confirm_token_expiration = None
            try:
                db.session.commit()
                flash('Sua conta foi confirmada com sucesso! Agora você pode fazer login.', 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erro ao salvar confirmação de e-mail para token {token}: {e}")
                flash('Ocorreu um erro ao confirmar sua conta. Tente novamente mais tarde.', 'danger')
        else:
            # Token não correspondeu ou expirou (verify_email_confirmation_token retornou False)
            flash('O link de confirmação é inválido ou expirou. Por favor, solicite um novo e-mail de confirmação ou tente se registrar novamente.', 'danger')
    else:
        # Nenhum usuário encontrado com este token
        flash('Token de confirmação não encontrado ou inválido.', 'danger')

    return redirect(url_for('main.login')) # Redireciona para login em todos os casos após tentativa de confirmação


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Ou para um painel de controle

    form = LoginForm()
    math_error_login = None

    if request.method == 'POST':
        expected_sum_login = session.get('math_expected_sum_login')
        user_answer_login = form.math_answer_login.data

        if expected_sum_login is None:
            flash('Houve um problema com a verificação de login. Por favor, tente novamente.', 'danger')
            num1, num2, new_expected_sum = generate_math_challenge()
            form.num1_login.data = num1
            form.num2_login.data = num2
            session['math_expected_sum_login'] = new_expected_sum
            return render_template('login.html', title='Login', form=form, math_error_login=math_error_login)

        if user_answer_login != expected_sum_login:
            math_error_login = "Resposta da verificação incorreta."

        if not math_error_login and form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data.lower()).first()

            if user and user.check_password(form.password.data):
                if user.email_confirmed:
                    login_user(user, remember=form.remember.data)

                    # Atualizar informações de login no DB (IP e expiração)
                    client_ip = request.remote_addr
                    user.update_login_session(ip_address=client_ip) # Expiração padrão de config
                    db.session.commit() # Salva o IP no DB antes de tentar adicioná-lo ao firewall

                    # Adicionar IP ao firewall
                    fw_success, fw_message = allow_ip(client_ip)
                    if fw_success:
                        flash(f'Login bem-sucedido! Bem-vindo, {user.email}. Seu IP {client_ip} foi permitido no firewall.', 'success')
                    else:
                        # O login foi bem-sucedido, mas o firewall falhou.
                        # O que fazer? Por enquanto, apenas avisar. Poderia fazer logout forçado.
                        flash(f'Login bem-sucedido, mas houve um problema ao liberar seu IP ({client_ip}) no firewall: {fw_message}. Por favor, contate o suporte.', 'warning')
                        # Considerar reverter o login ou não permitir o acesso se o firewall for crítico.
                        # Por ora, o usuário está logado na aplicação, mas o firewall pode não estar aberto.

                    session.pop('math_expected_sum_login', None)

                    # Redirecionar para a página que o usuário tentava acessar (se houver)
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('main.index'))
                else:
                    flash('Sua conta ainda não foi confirmada. Por favor, verifique seu e-mail.', 'warning')
            else:
                flash('Login falhou. Verifique seu e-mail e senha.', 'danger')
        else:
            if not math_error_login:
                flash('Por favor, corrija os erros no formulário de login.', 'danger')

    # Método GET ou POST falhou
    num1_login, num2_login, expected_sum_login_sess = generate_math_challenge()
    form.num1_login.data = num1_login
    form.num2_login.data = num2_login
    session['math_expected_sum_login'] = expected_sum_login_sess

    return render_template('login.html', title='Login', form=form, math_error_login=math_error_login)

@main_bp.route('/logout')
@login_required # Só usuários logados podem fazer logout
def logout():
    user_ip = None
    if current_user.is_authenticated: # current_user é o objeto User
        user_ip_to_deny = current_user.current_logged_in_ip

        current_user.clear_login_session() # Limpa IP e expiração no DB
        db.session.commit() # Salva a limpeza do IP no DB antes de tentar removê-lo do firewall

        if user_ip_to_deny:
            fw_success, fw_message = deny_ip(user_ip_to_deny)
            if fw_success:
                flash(f'Seu IP {user_ip_to_deny} foi removido das permissões do firewall.', 'info')
            else:
                # O usuário está deslogado da aplicação, mas o firewall pode não ter removido o IP.
                flash(f'Houve um problema ao remover seu IP ({user_ip_to_deny}) do firewall: {fw_message}. Contate o suporte se o problema persistir.', 'warning')
        else:
            flash('Nenhum IP estava registrado para esta sessão no firewall.', 'info')

    logout_user() # Função do Flask-Login que limpa a sessão
    flash(f'Você foi desconectado.', 'success') # Mensagem mais genérica, os detalhes do FW já foram dados.
    return redirect(url_for('main.login'))

# Exemplo de uma rota protegida
@main_bp.route('/dashboard')
@login_required # Requer que o usuário esteja logado
def dashboard():
    # Aqui, o current_user é o usuário logado.
    # Poderíamos verificar se current_user.current_logged_in_ip == request.remote_addr
    # como uma camada extra de segurança, mas o firewall já cuidará disso.
    return render_template('dashboard.html', title='Painel de Controle')

# Criar app/templates/dashboard.html
# Conteúdo simples:
# {% extends "base.html" %}
# {% block title %}Painel - {{ super() }}{% endblock %}
# {% block content %}
# <h2>Painel de Controle</h2>
# <p>Bem-vindo ao seu painel, {{ current_user.email }}!</p>
# <p>Seu IP logado é: {{ current_user.current_logged_in_ip }}</p>
# <p>Sua sessão de login expira em: {{ current_user.login_session_expiration.strftime('%d/%m/%Y %H:%M:%S') if current_user.login_session_expiration else 'N/A' }} UTC</p>
# <p><a href="{{ url_for('main.index') }}">Voltar para Início</a></p>
# {% endblock %}

# Modificar app/templates/index.html para usar current_user
# Modificar app/templates/base.html para incluir links de login/logout condicionalmente

# Adicionar um template index.html básico
# Criar app/templates/index.html (já existe, mas será atualizado)
# Conteúdo simples:
# {% extends "base.html" %}
# {% block title %}Página Inicial - {{ super() }}{% endblock %}
# {% block content %}
# <h2>Bem-vindo ao Sistema!</h2>
# <p>Este é o sistema de login com firewall.</p>
# <p><a href="{{ url_for('main.register') }}">Registrar</a></p>
# <p><a href="{{ url_for('main.login') }}">Login</a></p>
# {% endblock %}
# Este arquivo será criado na próxima ação.

# A função register_routes não é mais necessária aqui, pois o blueprint é
# importado e registrado diretamente em app/__init__.py.
# Remover as linhas comentadas sobre register_routes se ainda existirem.
# O código fornecido no SEARCH já não as tem de forma ativa.
# Garantir que não haja chamadas a register_routes neste arquivo.

# Import os para verificar a existência do template de login placeholder
import os

# A estrutura do __init__.py já está correta para importar e registrar 'main_bp'.
# from .routes import main_bp
# app.register_blueprint(main_bp)
# Isso está no __init__.py.
