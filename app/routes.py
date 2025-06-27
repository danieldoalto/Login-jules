from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from .forms import RegistrationForm, LoginForm, AdminUserActionForm, generate_math_challenge # AdminUserActionForm importado
from .models import User, AdminUser
from . import db
from .email_utils import send_confirmation_email, send_registration_received_email, send_admin_new_user_notification_email
from .firewall_utils import allow_ip, deny_ip
from flask_login import login_user, logout_user, login_required, current_user
from .decorators import admin_required # Importar o novo decorador
from datetime import datetime # Para approved_at

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
        current_app.logger.info(f"[REGISTER - POST] Iniciando verificação. Session keys: {list(session.keys())}")
        expected_sum_from_session = session.get('math_expected_sum')
        user_math_answer = form.math_answer.data # Já é convertido para int pelo IntegerField
        current_app.logger.info(f"[REGISTER - POST] Valor esperado da sessão: {expected_sum_from_session}, Resposta do usuário: {user_math_answer}")

        if expected_sum_from_session is None:
            current_app.logger.error("[REGISTER - POST] Erro: 'math_expected_sum' não encontrado na sessão.")
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
                new_user = User(
                    email=user_email,
                    user_type='user', # Padrão, mas explícito
                    is_approved=False, # Novo usuário precisa de aprovação
                    email_confirmed=False # E-mail ainda não confirmado
                )
                new_user.set_password(form.password.data)

                # Não geramos token de confirmação de e-mail aqui ainda.
                # Será gerado quando o admin aprovar.

                db.session.add(new_user)
                db.session.commit()

                # Enviar e-mail para o usuário informando que o pedido foi recebido
                try:
                    send_registration_received_email(user_email=new_user.email)
                except Exception as mail_exc:
                    current_app.logger.error(f"Falha ao enviar e-mail de 'pedido recebido' para {new_user.email}: {mail_exc}")
                    # Continuar mesmo se o e-mail falhar, o registro no DB é mais importante.

                # Enviar e-mail de notificação para o administrador
                admin_notify_email = current_app.config.get('ADMIN_NOTIFICATIONS_EMAIL')
                if admin_notify_email:
                    try:
                        send_admin_new_user_notification_email(admin_email=admin_notify_email, new_user_email=new_user.email, user_id=new_user.id)
                    except Exception as mail_exc:
                        current_app.logger.error(f"Falha ao enviar e-mail de notificação de novo usuário para admin {admin_notify_email}: {mail_exc}")
                else:
                    current_app.logger.warning("ADMIN_NOTIFICATIONS_EMAIL não configurado. Não foi possível notificar o admin sobre novo registro.")

                flash(f'Seu pedido de registro para {new_user.email} foi recebido! Você será notificado por e-mail quando sua conta for aprovada e estiver pronta para confirmação.', 'success')
                session.pop('math_expected_sum', None)
                return redirect(url_for('main.index')) # Redireciona para o índice ou uma página de "pedido recebido"
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
    current_app.logger.info(f"[REGISTER - GET/Fallback] Novo desafio matemático gerado. Expected sum: {expected_sum}. Armazenado na sessão.")

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
        if current_user.user_type == 'admin':
            return redirect(url_for('main.admin_dashboard'))
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    math_error_login = None

    if request.method == 'POST':
        expected_sum_login = session.get('math_expected_sum_login')
        user_answer_login = form.math_answer_login.data
        valid_math = False

        if expected_sum_login is None:
            flash('Houve um problema com a verificação de login. Por favor, tente novamente.', 'danger')
        elif user_answer_login != expected_sum_login:
            math_error_login = "Resposta da verificação incorreta."
        else:
            valid_math = True

        if valid_math and form.validate_on_submit():
            form_email = form.email.data.lower()
            form_password = form.password.data
            admin_env_email = current_app.config.get('ADMIN_EMAIL')
            admin_env_password = current_app.config.get('ADMIN_PASSWORD')
            authenticated_user_object = None
            login_success = False

            # 1. Tentar login como Administrador
            if form_email == admin_env_email and form_password == admin_env_password:
                admin_user_obj = AdminUser(email=admin_env_email)
                login_user(admin_user_obj, remember=form.remember.data)
                authenticated_user_object = admin_user_obj
                login_success = True
            else:
                # 2. Tentar login como Usuário do Banco de Dados
                user_from_db = User.query.filter_by(email=form_email).first()
                if user_from_db and user_from_db.check_password(form_password):
                    if not user_from_db.email_confirmed:
                        flash('Sua conta ainda não teve o e-mail confirmado. Por favor, verifique seu e-mail.', 'warning')
                    elif not user_from_db.is_approved:
                        flash('Sua conta ainda não foi aprovada por um administrador. Você será notificado por e-mail quando for aprovada.', 'warning')
                    else:
                        login_user(user_from_db, remember=form.remember.data)
                        user_from_db.update_login_session(ip_address=request.remote_addr)
                        db.session.commit()
                        authenticated_user_object = user_from_db
                        login_success = True
                else:
                    flash('Login falhou. Verifique seu e-mail e senha.', 'danger')

            # Se o login (admin ou usuário) foi bem-sucedido
            if login_success and authenticated_user_object:
                client_ip = request.remote_addr

                # Lógica para "atualizar" IP para AdminUser (em memória)
                if authenticated_user_object.user_type == 'admin':
                    authenticated_user_object.current_logged_in_ip = client_ip
                    session['admin_logged_in_ip'] = client_ip

                # Adicionar IP ao firewall para qualquer login bem-sucedido
                fw_success, fw_message = allow_ip(client_ip)
                if fw_success:
                    flash(f'Login bem-sucedido! Bem-vindo, {authenticated_user_object.email}. Seu IP {client_ip} foi permitido no firewall.', 'success')
                else:
                    flash(f'Login bem-sucedido, mas houve um problema ao liberar seu IP ({client_ip}) no firewall: {fw_message}. Por favor, contate o suporte.', 'warning')

                session.pop('math_expected_sum_login', None)
                next_page = request.args.get('next')

                if authenticated_user_object.user_type == 'admin':
                    return redirect(next_page) if next_page else redirect(url_for('main.admin_dashboard'))
                else:
                    return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        
        elif valid_math and form.errors:
            flash('Por favor, corrija os erros no formulário de login.', 'danger')

    # Para GET request ou se POST falhou e precisa re-renderizar o form
    num1_login, num2_login, expected_sum_login_sess = generate_math_challenge()
    form.num1_login.data = num1_login
    form.num2_login.data = num2_login
    session['math_expected_sum_login'] = expected_sum_login_sess

    return render_template('login.html', title='Login', form=form, math_error_login=math_error_login)

@main_bp.route('/logout')
@login_required
def logout():
    user_ip_to_deny = None
    if current_user.is_authenticated:
        if current_user.user_type == 'user': # Usuário normal do DB
            user_ip_to_deny = current_user.current_logged_in_ip
            current_user.clear_login_session() # Limpa IP e expiração no DB
            db.session.commit() # Salva a limpeza do IP no DB
        elif current_user.user_type == 'admin': # AdminUser em memória
            # O AdminUser não armazena o IP no DB. Precisamos recuperá-lo de outra forma
            # se quisermos negar o IP específico que foi permitido para a sessão do admin.
            # Uma opção é armazenar o IP do admin na sessão do Flask no momento do login.
            # Ou, se AdminUser foi modificado para ter current_logged_in_ip (como sugerido antes):
            user_ip_to_deny = getattr(current_user, 'current_logged_in_ip', session.get('admin_logged_in_ip'))
            # Limpar da sessão se estiver lá
            session.pop('admin_logged_in_ip', None)

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
@login_required
def dashboard():
    # Esta rota é para usuários 'user'. Admins têm '/admin/dashboard'.
    if current_user.user_type == 'admin':
        flash("Administradores devem usar o Painel do Administrador.", "info")
        return redirect(url_for('main.admin_dashboard'))

    if not current_user.is_approved or not current_user.email_confirmed:
        flash("Sua conta precisa ser aprovada e seu e-mail confirmado para acessar o painel.", "warning")
        # Poderia ser logout_user() aqui e redirecionar para login,
        # ou apenas para o index com a mensagem.
        return redirect(url_for('main.index'))

    dynamic_links_config = current_app.config.get('DYNAMIC_LINKS', {})
    user_dynamic_links = dynamic_links_config.get('user_links', [])

    return render_template('dashboard.html',
                           title='Painel de Controle do Usuário',
                           user_links=user_dynamic_links)

# Criar app/templates/dashboard.html (já existe, será atualizado para user_links)
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

# --- Admin Routes ---
@main_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    pending_users = User.query.filter_by(is_approved=False, user_type='user').order_by(User.created_at.desc()).all()

    dynamic_links_config = current_app.config.get('DYNAMIC_LINKS', {})
    admin_dynamic_links = dynamic_links_config.get('admin_links', [])

    approve_form = AdminUserActionForm()
    delete_form = AdminUserActionForm()

    return render_template('admin/dashboard.html',
                           title="Painel do Administrador",
                           pending_users=pending_users,
                           admin_links=admin_dynamic_links,
                           approve_form=approve_form,
                           delete_form=delete_form)

@main_bp.route('/admin/users/approve/<int:user_id>', methods=['POST'])
@admin_required
def admin_approve_user(user_id):
    form = AdminUserActionForm()
    if form.validate_on_submit(): # Valida CSRF
        user_to_approve = User.query.get_or_404(user_id)
        if user_to_approve.user_type != 'user':
            flash("Apenas usuários do tipo 'user' podem ser aprovados/rejeitados desta forma.", "warning")
            return redirect(url_for('main.admin_dashboard'))

        if user_to_approve.is_approved:
            flash(f"Usuário {user_to_approve.email} já está aprovado.", "info")
            return redirect(url_for('main.admin_dashboard'))

        try:
            user_to_approve.is_approved = True
            user_to_approve.approved_by_email = current_user.email # Email do admin logado
            user_to_approve.approved_at = datetime.utcnow()

            confirmation_token = user_to_approve.generate_email_confirmation_token()
            db.session.commit()

            try:
                send_confirmation_email(user_email=user_to_approve.email, token=confirmation_token)
                flash(f"Usuário {user_to_approve.email} aprovado com sucesso! E-mail de confirmação enviado.", "success")
            except Exception as mail_exc:
                current_app.logger.error(f"Usuário {user_to_approve.email} aprovado, mas falha ao enviar e-mail de confirmação: {mail_exc}")
                flash(f"Usuário {user_to_approve.email} aprovado, mas houve um erro ao enviar o e-mail de confirmação. Por favor, verifique os logs.", "warning")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao aprovar usuário {user_to_approve.email}: {e}")
            flash(f"Erro ao aprovar usuário: {str(e)}", "danger")
    else:
        flash("Falha na submissão do formulário de aprovação ou CSRF inválido.", "danger")
        # Log form.errors se houver outros erros de validação no AdminUserActionForm
        if form.errors:
            current_app.logger.error(f"Erros no formulário de aprovação: {form.errors}")

    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    form = AdminUserActionForm()
    if form.validate_on_submit(): # Valida CSRF
        user_to_delete = User.query.get_or_404(user_id)

        if user_to_delete.user_type == 'admin':
            flash("Administradores não podem ser deletados por esta interface.", "danger")
            return redirect(url_for('main.admin_dashboard'))

        try:
            email_deleted = user_to_delete.email
            if user_to_delete.current_logged_in_ip:
                deny_ip(user_to_delete.current_logged_in_ip)

            db.session.delete(user_to_delete)
            db.session.commit()
            flash(f"Usuário {email_deleted} (ID: {user_id}) foi deletado com sucesso.", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao deletar usuário ID {user_id}: {e}")
            flash(f"Erro ao deletar usuário: {str(e)}", "danger")
    else:
        flash("Falha na submissão do formulário de deleção ou CSRF inválido.", "danger")
        if form.errors:
            current_app.logger.error(f"Erros no formulário de deleção: {form.errors}")

    return redirect(url_for('main.admin_dashboard'))



# A rota de logout já existe e funciona para admin também.
# O redirecionamento pós-login do admin para /admin/dashboard já foi ajustado.
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
