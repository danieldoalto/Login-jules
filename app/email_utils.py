from flask import render_template, current_app
from flask_mail import Message
from . import mail # Instância do Mail de app/__init__.py
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, text_body, html_body, sender=None):
    """
    Envia um e-mail.
    :param subject: Assunto do e-mail.
    :param recipients: Lista de destinatários.
    :param text_body: Corpo do e-mail em texto puro.
    :param html_body: Corpo do e-mail em HTML.
    :param sender: Remetente. Se None, usa MAIL_DEFAULT_SENDER da configuração.
    """
    app = current_app._get_current_object() # Obter o objeto real da aplicação para o thread

    if sender is None:
        sender = app.config.get('MAIL_DEFAULT_SENDER')
        if not sender: # Fallback para MAIL_USERNAME se MAIL_DEFAULT_SENDER não estiver definido
             sender = app.config.get('MAIL_USERNAME')

    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body

    # Enviar e-mail de forma assíncrona para não bloquear a requisição
    thread = Thread(target=send_async_email, args=[app, msg])
    thread.start()
    # Para depuração síncrona, você pode usar:
    # mail.send(msg)
    # print(f"E-mail enviado (simulado): Para {recipients}, Assunto: {subject}")


def send_confirmation_email(user_email, token):
    """Envia o e-mail de confirmação de cadastro."""
from flask import url_for, request # Adicionado request

# ... (send_async_email e send_email permanecem os mesmos)

def send_confirmation_email(user_email, token):
    """Envia o e-mail de confirmação de cadastro."""
    app = current_app._get_current_object()

    # Tenta obter SERVER_NAME da configuração. Isso é o ideal.
    server_name = app.config.get('SERVER_NAME')
    preferred_scheme = app.config.get('PREFERRED_URL_SCHEME', 'http')

    if app.config.get('FLASK_USE_SSL'): # Se SSL está configurado para o servidor de dev
        preferred_scheme = 'https'

    # Se SERVER_NAME não estiver definido, tentamos construir a base da URL
    # a partir do contexto da requisição atual, se disponível.
    # Isso é útil para desenvolvimento, mas para produção, SERVER_NAME deve ser definido.
    if not server_name:
        if request: # Verifica se estamos em um contexto de requisição
            server_name = request.host.split(':')[0] # host sem a porta
            # Adiciona a porta se não for a padrão para o esquema
            port = request.host.split(':')[1] if ':' in request.host else None
            if port and not ((preferred_scheme == 'http' and port == '80') or \
                             (preferred_scheme == 'https' and port == '443')):
                server_name = f"{server_name}:{port}"
            # Se request.scheme está disponível e confiável, use-o
            if hasattr(request, 'scheme') and request.scheme:
                 preferred_scheme = request.scheme
        else:
            # Fallback se não houver SERVER_NAME nem contexto de request (ex: CLI)
            # Neste caso, o link pode não ser ideal.
            host = app.config.get('FLASK_RUN_HOST', 'localhost')
            if host == '0.0.0.0': host = 'localhost' # Para links clicáveis
            port = app.config.get('FLASK_RUN_PORT', 5000)
            server_name = f"{host}:{port}"
            # preferred_scheme já tem um padrão de 'http' ou de FLASK_USE_SSL

    # Gerar o caminho da URL para a confirmação
    # _external=False porque vamos construir o domínio base manualmente ou a partir de SERVER_NAME
    with app.test_request_context(base_url=f"{preferred_scheme}://{server_name}"):
        # Forçar SERVER_NAME para url_for usar corretamente para _external=True
        # ou para construir o link manualmente.
        # Uma forma mais limpa é garantir que SERVER_NAME e PREFERRED_URL_SCHEME estejam
        # corretamente configurados no app.config.
        original_server_name = app.config.get('SERVER_NAME')
        original_scheme = app.config.get('PREFERRED_URL_SCHEME')

        app.config['SERVER_NAME'] = server_name
        app.config['PREFERRED_URL_SCHEME'] = preferred_scheme

        try:
            # Agora url_for com _external=True deve funcionar se SERVER_NAME está temporariamente definido
            confirm_link = url_for('main.confirm_email', token=token, _external=True)
        except RuntimeError as e:
            # Fallback se ainda houver problemas (ex: contexto de app não ativo corretamente para url_for)
            # Isso pode acontecer se chamado de um thread sem o contexto correto empurrado.
            # A função send_async_email já lida com app_context.
            # O problema pode ser se url_for é chamado fora do contexto da app no thread principal.
            # A chamada para send_confirmation_email deve estar dentro de um app_context.
            print(f"Erro ao gerar URL de confirmação: {e}. Usando fallback manual.")
            path = url_for('main.confirm_email', token=token, _external=False) # Só o caminho
            confirm_link = f"{preferred_scheme}://{server_name}{path}"
        finally:
            # Restaurar configurações originais se foram alteradas
            if original_server_name is not None:
                app.config['SERVER_NAME'] = original_server_name
            else:
                app.config.pop('SERVER_NAME', None)

            if original_scheme is not None:
                app.config['PREFERRED_URL_SCHEME'] = original_scheme
            else:
                app.config.pop('PREFERRED_URL_SCHEME', None)

    subject = "Confirme seu endereço de e-mail"

    send_email(
        subject=subject,
        recipients=[user_email],
        text_body=render_template('email/confirm_email.txt', confirm_url=confirm_link, email=user_email),
        html_body=render_template('email/confirm_email.html', confirm_url=confirm_link, email=user_email)
    )

def send_registration_received_email(user_email):
    """Envia e-mail ao usuário informando que o pedido de registro foi recebido."""
    app = current_app._get_current_object()
    subject = "Seu pedido de registro foi recebido"
    send_email(
        subject=subject,
        recipients=[user_email],
        text_body=render_template('email/registration_received.txt', email=user_email),
        html_body=render_template('email/registration_received.html', email=user_email)
    )

def send_admin_new_user_notification_email(admin_email, new_user_email, user_id):
    """Notifica o administrador sobre um novo pedido de registro."""
    app = current_app._get_current_object()
    subject = f"Novo Pedido de Registro: {new_user_email}"
    # O link de aprovação será parte do painel do admin, aqui apenas notificamos.
    # Poderíamos incluir um link direto para a página de gerenciamento de usuários se já soubermos a URL.
    # Ex: admin_panel_url = url_for('main.admin_users_pending', _external=True) # Se tal rota existir

    # Para construir a URL do painel admin, precisamos de um contexto de request ou SERVER_NAME
    server_name = app.config.get('SERVER_NAME', 'localhost:5000') # Fallback
    preferred_scheme = app.config.get('PREFERRED_URL_SCHEME', 'http')
    if app.config.get('FLASK_USE_SSL'): preferred_scheme = 'https'

    admin_dashboard_url = f"{preferred_scheme}://{server_name}{url_for('main.admin_dashboard')}" # Assumindo que admin_dashboard é a rota

    send_email(
        subject=subject,
        recipients=[admin_email],
        text_body=render_template('email/admin_new_user_notification.txt',
                                  new_user_email=new_user_email,
                                  user_id=user_id,
                                  admin_dashboard_url=admin_dashboard_url),
        html_body=render_template('email/admin_new_user_notification.html',
                                  new_user_email=new_user_email,
                                  user_id=user_id,
                                  admin_dashboard_url=admin_dashboard_url)
    )

# A função send_confirmation_email (para confirmar e-mail após aprovação) já existe
# e será chamada pela lógica de aprovação do administrador.
