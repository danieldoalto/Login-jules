import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(dotenv_path='/home/daniel/python/Login_phyton/.env')

# Configurações do SMTP do .env
MAIL_SERVER = os.getenv('MAIL_SERVER')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587)) # Default para 587 se não especificado
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL') # Usar como destinatário para teste

# Informações do e-mail de teste
SENDER_EMAIL = MAIL_USERNAME
RECEIVER_EMAIL = ADMIN_EMAIL
SUBJECT = "Teste de SMTP do Gmail"
BODY = "Este é um e-mail de teste enviado do seu script Python para verificar a configuração SMTP do Gmail."

print(f"Tentando conectar ao SMTP: {MAIL_SERVER}:{MAIL_PORT}")
print(f"Usando TLS: {MAIL_USE_TLS}")
print(f"Usuário: {MAIL_USERNAME}")
print(f"Destinatário: {RECEIVER_EMAIL}")

try:
    # Criar o objeto MIMEText
    msg = MIMEText(BODY)
    msg['Subject'] = SUBJECT
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    # Conectar ao servidor SMTP
    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
        if MAIL_USE_TLS:
            server.starttls() # Iniciar TLS
        
        server.login(MAIL_USERNAME, MAIL_PASSWORD) # Fazer login
        server.send_message(msg) # Enviar o e-mail

    print("E-mail de teste enviado com sucesso!")

except smtplib.SMTPAuthenticationError as e:
    print(f"Erro de autenticação SMTP: {e}")
    print("Verifique seu MAIL_USERNAME e MAIL_PASSWORD no arquivo .env.")
    print("Se estiver usando o Gmail, certifique-se de que 'Acesso a apps menos seguros' esteja ativado ou use 'Senhas de app' se a verificação em duas etapas estiver ativada.")
except smtplib.SMTPConnectError as e:
    print(f"Erro de conexão SMTP: {e}")
    print(f"Verifique se o servidor SMTP ({MAIL_SERVER}) e a porta ({MAIL_PORT}) estão corretos e se não há firewall bloqueando a conexão.")
except Exception as e:
    print(f"Ocorreu um erro ao enviar o e-mail: {e}")