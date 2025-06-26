import click
from flask.cli import with_appcontext
from . import db # db de app/__init__.py
# Importe seus modelos aqui para que o db.create_all() os conheça
from .models import User

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Limpa os dados existentes e cria novas tabelas."""
    # Ordem de drop e create pode ser importante se houver FKs complexas.
    # Para User simples, db.drop_all() e db.create_all() é suficiente.
    # Em um cenário mais complexo, você pode querer usar Flask-Migrate para gerenciar alterações de esquema.

    # Para evitar erros se as tabelas não existirem, ou para recriar:
    # db.drop_all() # Comentado para não perder dados acidentalmente em execuções repetidas

    db.create_all()
    click.echo('Banco de dados inicializado e tabelas criadas.')

@click.command('create-user')
@with_appcontext
@click.argument('email')
@click.argument('password')
def create_user_command(email, password):
    """Cria um novo usuário."""
    if User.query.filter_by(email=email).first():
        click.echo(f'Usuário {email} já existe.')
        return

    new_user = User(email=email)
    new_user.set_password(password)
    new_user.email_confirmed = True # Para usuários criados via CLI, podemos confirmar automaticamente

    db.session.add(new_user)
    db.session.commit()
    click.echo(f'Usuário {email} criado com sucesso.')

@click.command('setup-firewall')
@with_appcontext
@click.option('--ssh-port', default='22', help='Porta SSH a ser permitida.')
@click.option('--web-ports', default='80,443', help='Portas web a serem permitidas, separadas por vírgula (ex: 80,443).')
def setup_firewall_command(ssh_port, web_ports):
    """Configura as regras iniciais do firewall UFW. Use com CUIDADO."""
    from .firewall_utils import setup_initial_firewall_rules

    click.confirm(
        f"ATENÇÃO: Isso irá redefinir as regras do UFW para:\n"
        f"- Negar tráfego de entrada por padrão\n"
        f"- Permitir tráfego de saída por padrão\n"
        f"- Permitir SSH na porta {ssh_port}/tcp\n"
        f"- Permitir tráfego web nas portas {web_ports}/tcp\n"
        f"- Habilitar UFW (se inativo)\n"
        f"Certifique-se de que a porta SSH ({ssh_port}) está correta ou você pode PERDER ACESSO ao servidor.\n"
        "Você tem certeza que quer continuar?",
        abort=True # Aborta se o usuário não confirmar
    )

    list_web_ports = [port.strip() for port in web_ports.split(',')]

    click.echo("Iniciando configuração do firewall...")
    success, results = setup_initial_firewall_rules(ssh_port=ssh_port, web_ports=list_web_ports)

    for cmd, res in results.items():
        status = "SUCESSO" if res["success"] else "FALHA"
        click.echo(f"- Comando '{cmd}': {status} -> {res['message']}")

    if success:
        click.secho("Configuração inicial do firewall concluída com sucesso.", fg="green")
    else:
        click.secho("ERRO: Uma ou mais etapas da configuração do firewall falharam. Verifique os logs e o status do UFW.", fg="red")


def register_commands(app):
    """Registra comandos CLI com a aplicação Flask."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_user_command)
    app.cli.add_command(setup_firewall_command)

# Para usar esses comandos:
# flask init-db
# flask create-user seuemail@example.com su_asenha
# flask setup-firewall --ssh-port 2222 --web-ports 80,443,8080
# (Certifique-se de que FLASK_APP=run.py está definido no ambiente)
