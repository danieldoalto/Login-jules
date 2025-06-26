import subprocess
import shlex
from flask import current_app

# NOTA DE SEGURANÇA IMPORTANTE:
# Estas funções assumem que o usuário executando a aplicação Flask tem permissão
# para executar os comandos `ufw` via `sudo` sem senha.
# Isso deve ser configurado com muito cuidado no arquivo /etc/sudoers.
# Exemplo (restritivo):
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw allow from [0-9.]* to any
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw delete allow from [0-9.]* to any
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw status
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw reload
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw --force enable
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw default deny incoming
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw default allow outgoing
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw allow ssh
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw allow http
# www-data ALL=(ALL) NOPASSWD: /usr/sbin/ufw allow https
# Onde 'www-data' é o usuário que executa sua aplicação Flask.
# Testar esta configuração é crucial em um ambiente seguro.

def _run_ufw_command(command_str):
    """Executa um comando ufw com sudo e lida com a saída."""
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
            current_app.logger.info(f"Comando UFW bem-sucedido: {command_str}. Saída: {stdout_decoded}")
            return True, stdout_decoded
        else:
            current_app.logger.error(f"Erro ao executar comando UFW: {command_str}. Código: {process.returncode}. Erro: {stderr_decoded}. Saída: {stdout_decoded}")
            return False, f"Erro: {stderr_decoded} (Saída: {stdout_decoded})"

    except subprocess.TimeoutExpired:
        current_app.logger.error(f"Timeout ao executar comando UFW: {command_str}")
        process.kill() # Garante que o processo seja morto
        return False, "Timeout ao executar o comando."
    except Exception as e:
        current_app.logger.error(f"Exceção ao executar comando UFW: {command_str}. Erro: {e}")
        return False, f"Exceção: {str(e)}"

def allow_ip(ip_address):
    """
    Adiciona o IP à lista de permissões do UFW para todas as portas e protocolos.
    Considerar restringir portas/protocolos se necessário.
    """
    if not ip_address:
        current_app.logger.warning("Tentativa de permitir IP vazio.")
        return False, "IP não fornecido."

    # Comando para permitir todas as portas para o IP específico.
    # Pode ser mais restritivo: "ufw allow from {ip_address} to any port 80,443 proto tcp"
    # Mas o requisito é "acesso a todas as portas".
    command = f"ufw allow from {ip_address}"
    success, message = _run_ufw_command(command)
    if success:
        # UFW pode precisar ser recarregado para aplicar algumas regras,
        # mas 'allow from' geralmente é aplicado imediatamente.
        # _run_ufw_command("ufw reload") # Descomentar se necessário após testes.
        current_app.logger.info(f"IP {ip_address} permitido no firewall.")
    return success, message

def deny_ip(ip_address):
    """Remove uma regra de permissão para o IP do UFW."""
    if not ip_address:
        current_app.logger.warning("Tentativa de negar IP vazio.")
        return False, "IP não fornecido."

    command = f"ufw delete allow from {ip_address}"
    # Nota: `ufw delete` pode requerer o número da regra se houver múltiplas regras idênticas
    # ou se a regra foi adicionada de forma mais específica.
    # Se `ufw allow from <ip>` foi usado, `ufw delete allow from <ip>` deve funcionar.
    # É importante que a regra de negação corresponda à regra de permissão.
    success, message = _run_ufw_command(command)
    if success:
        # _run_ufw_command("ufw reload") # Descomentar se necessário
        current_app.logger.info(f"Regra de permissão para IP {ip_address} removida do firewall.")
    return success, message

def get_firewall_status():
    """Obtém o status do UFW."""
    return _run_ufw_command("ufw status")

def setup_initial_firewall_rules(ssh_port="22", web_ports=["80", "443"]):
    """
    Configura as regras iniciais e básicas do firewall UFW.
    Esta função é destrutiva e deve ser usada com extremo cuidado.
    Certifique-se de que a porta SSH está correta para não perder acesso ao servidor.
    """
    current_app.logger.warning("Iniciando configuração das regras iniciais do firewall. ISSO PODE SER DESTRUTIVO.")

    results = {}
    success_overall = True

    commands = [
        "ufw default deny incoming",    # Bloqueia todas as conexões de entrada por padrão
        "ufw default allow outgoing",   # Permite todas as conexões de saída por padrão
        f"ufw allow {ssh_port}/tcp",    # PERMITE ACESSO SSH! VERIFIQUE ESTA PORTA!
    ]
    for port in web_ports:
        commands.append(f"ufw allow {port}/tcp") # Permite tráfego HTTP/HTTPS

    for cmd_suffix in commands:
        success, msg = _run_ufw_command(cmd_suffix)
        results[cmd_suffix] = {"success": success, "message": msg}
        if not success:
            success_overall = False
            current_app.logger.error(f"Falha crítica ao configurar regra inicial: {cmd_suffix}")
            # Considerar parar aqui ou reverter, dependendo da política.

    # Habilitar UFW (se não estiver ativo). Use --force para não pedir confirmação.
    # Verificar status antes pode ser uma boa ideia.
    # status_success, status_msg = get_firewall_status()
    # if "inactive" in status_msg.lower():
    enable_success, enable_msg = _run_ufw_command("ufw --force enable")
    results["enable_ufw"] = {"success": enable_success, "message": enable_msg}
    if not enable_success:
        success_overall = False
        current_app.logger.error("Falha ao habilitar UFW.")

    if success_overall:
        current_app.logger.info("Regras iniciais do firewall configuradas e UFW habilitado.")
    else:
        current_app.logger.error("UMA OU MAIS REGRAS INICIAIS DO FIREWALL FALHARAM. VERIFIQUE IMEDIATAMENTE.")

    return success_overall, results
