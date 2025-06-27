import subprocess
import shlex
from flask import current_app
from flask_login import current_user
from . import db
from .models import FirewallLog

# NOTA DE SEGURANÇA IMPORTANTE:
# Estas funções assumem que o usuário executando a aplicação Flask tem permissão
# para executar os comandos `iptables` via `sudo` sem senha.
# Isso deve ser configurado com muito cuidado no arquivo /etc/sudoers.
# Exemplo (restritivo):
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -A WHITELIST -s [0-9.]* -j ACCEPT
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -D WHITELIST -s [0-9.]* -j ACCEPT
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -L INPUT -n -v
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -L FORWARD -n -v
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -L WHITELIST -n -v
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -F
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -X
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -Z
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -P INPUT DROP
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -P FORWARD DROP
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -P OUTPUT ACCEPT
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -N WHITELIST
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -A INPUT -j WHITELIST
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -A FORWARD -j WHITELIST
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -A INPUT -i lo -j ACCEPT
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/iptables -A INPUT -p tcp --dport [0-9]* -j ACCEPT
# Onde 'www-data' é o usuário que executa sua aplicação Flask.
# Testar esta configuração é crucial em um ambiente seguro.

def _run_iptables_command(command_str):
    """Executa um comando iptables com sudo e lida com a saída."""
    try:
        # Adiciona sudo ao comando
        full_command = f"sudo {command_str}"
        current_app.logger.info(f"Executando comando firewall: {full_command}")

        # shlex.split para lidar com argumentos corretamente
        process = subprocess.Popen(shlex.split(full_command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=15) # Timeout para evitar bloqueios indefinidos

        stdout_decoded = stdout.decode('utf-8').strip()
        stderr_decoded = stderr.decode('utf-8').strip()

        if process.returncode == 0:
            current_app.logger.info(f"Comando IPTables bem-sucedido: {command_str}. Saída: {stdout_decoded}")
            return True, stdout_decoded
        else:
            current_app.logger.error(f"Erro ao executar comando IPTables: {command_str}. Código: {process.returncode}. Erro: {stderr_decoded}. Saída: {stdout_decoded}")
            return False, f"Erro: {stderr_decoded} (Saída: {stdout_decoded})"

    except subprocess.TimeoutExpired:
        current_app.logger.error(f"Timeout ao executar comando IPTables: {command_str}")
        process.kill() # Garante que o processo seja morto
        return False, "Timeout ao executar o comando."
    except Exception as e:
        current_app.logger.error(f"Exceção ao executar comando IPTables: {command_str}. Erro: {e}")
        return False, f"Exceção: {str(e)}"

def allow_ip(ip_address):
    """
    Adiciona o IP à chain WHITELIST do IPTables e registra a ação.
    """
    if not ip_address:
        current_app.logger.warning("Tentativa de permitir IP vazio.")
        return False, "IP não fornecido."

    # Adiciona a regra para o IP na chain WHITELIST
    command = f"iptables -A WHITELIST -s {ip_address} -j ACCEPT"
    success, message = _run_iptables_command(command)
    if success:
        current_app.logger.info(f"IP {ip_address} adicionado à WHITELIST do IPTables.")
        # Registrar a ação no banco de dados
        user_id = current_user.id if current_user.is_authenticated else None
        log_entry = FirewallLog(ip_address=ip_address, action='allow', user_id=user_id)
        db.session.add(log_entry)
        db.session.commit()
    return success, message

def deny_ip(ip_address):
    """
    Remove o IP da chain WHITELIST do IPTables e registra a ação.
    """
    if not ip_address:
        current_app.logger.warning("Tentativa de negar IP vazio.")
        return False, "IP não fornecido."

    # Remove a regra para o IP da chain WHITELIST
    command = f"iptables -D WHITELIST -s {ip_address} -j ACCEPT"
    success, message = _run_iptables_command(command)
    if success:
        current_app.logger.info(f"IP {ip_address} removido da WHITELIST do IPTables.")
        # Registrar a ação no banco de dados
        user_id = current_user.id if current_user.is_authenticated else None
        log_entry = FirewallLog(ip_address=ip_address, action='deny', user_id=user_id)
        db.session.add(log_entry)
        db.session.commit()
    return success, message

def get_firewall_status():
    """Obtém o status das regras do IPTables."""
    # Retorna todas as regras para INPUT, FORWARD e WHITELIST
    input_status = _run_iptables_command("iptables -L INPUT -n -v")
    forward_status = _run_iptables_command("iptables -L FORWARD -n -v")
    whitelist_status = _run_iptables_command("iptables -L WHITELIST -n -v")
    return {
        "INPUT": input_status,
        "FORWARD": forward_status,
        "WHITELIST": whitelist_status
    }

def setup_initial_firewall_rules(ssh_port="22", web_ports=["80", "443"]):
    """
    Configura as regras iniciais e básicas do firewall IPTables.
    Esta função é destrutiva e deve ser usada com extremo cuidado.
    Certifique-se de que a porta SSH está correta para não perder acesso ao servidor.
    """
    current_app.logger.warning("Iniciando configuração das regras iniciais do firewall IPTables. ISSO PODE SER DESTRUTIVO.")

    results = {}
    success_overall = True

    # Limpar todas as regras existentes e chains personalizadas
    commands_flush = [
        "iptables -F", # Limpa todas as regras de todas as chains
        "iptables -X", # Deleta todas as chains vazias criadas pelo usuário
        "iptables -Z"  # Zera contadores
    ]
    for cmd in commands_flush:
        success, msg = _run_iptables_command(cmd)
        results[cmd] = {"success": success, "message": msg}
        if not success:
            success_overall = False
            current_app.logger.error(f"Falha ao limpar regras IPTables: {cmd}")

    # Definir políticas padrão para DROP
    commands_policy = [
        "iptables -P INPUT DROP",
        "iptables -P FORWARD DROP",
        "iptables -P OUTPUT ACCEPT" # Geralmente, saída é permitida
    ]
    for cmd in commands_policy:
        success, msg = _run_iptables_command(cmd)
        results[cmd] = {"success": success, "message": msg}
        if not success:
            success_overall = False
            current_app.logger.error(f"Falha ao definir política padrão IPTables: {cmd}")

    # Criar a chain WHITELIST
    success, msg = _run_iptables_command("iptables -N WHITELIST")
    results["iptables -N WHITELIST"] = {"success": success, "message": msg}
    if not success:
        success_overall = False
        current_app.logger.error("Falha ao criar chain WHITELIST.")

    # Adicionar regras JUMP para a WHITELIST nas chains INPUT e FORWARD
    commands_jump = [
        "iptables -A INPUT -j WHITELIST",
        "iptables -A FORWARD -j WHITELIST"
    ]
    for cmd in commands_jump:
        success, msg = _run_iptables_command(cmd)
        results[cmd] = {"success": success, "message": msg}
        if not success:
            success_overall = False
            current_app.logger.error(f"Falha ao adicionar regra JUMP para WHITELIST: {cmd}")

    # Regras para permitir tráfego específico
    commands_specific = [
        "iptables -A INPUT -i lo -j ACCEPT", # Permitir loopback
        "iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT", # Permitir conexões estabelecidas/relacionadas
        f"iptables -A INPUT -p tcp --dport {ssh_port} -j ACCEPT" # Permitir SSH
    ]
    for port in web_ports:
        commands_specific.append(f"iptables -A INPUT -p tcp --dport {port} -j ACCEPT") # Permitir portas web

    for cmd in commands_specific:
        success, msg = _run_iptables_command(cmd)
        results[cmd] = {"success": success, "message": msg}
        if not success:
            success_overall = False
            current_app.logger.error(f"Falha ao adicionar regra específica IPTables: {cmd}")

    if success_overall:
        current_app.logger.info("Regras iniciais do firewall IPTables configuradas.")
    else:
        current_app.logger.error("UMA OU MAIS REGRAS INICIAIS DO FIREWALL IPTABLES FALHARAM. VERIFIQUE IMEDIATAMENTE.")

    return success_overall, results
