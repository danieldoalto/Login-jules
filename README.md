# Sistema de Login com Gerenciamento de Firewall Dinâmico e Aprovação de Usuários

## Visão Geral

Este projeto implementa um sistema de login em Python utilizando o framework Flask. O objetivo principal é gerenciar dinamicamente uma lista de IPs permitidos no firewall do servidor (`ufw`). Após um login bem-sucedido, o IP do cliente (seja Administrador ou Usuário aprovado) é liberado no firewall para acesso a todos os serviços por 24 horas. Ao fazer logout, ou após a expiração da sessão, o acesso do IP é revogado.

O sistema distingue entre dois tipos de usuários: **Administrador** e **Usuário**. O login do Administrador é definido por variáveis de ambiente. Novos registros de Usuário requerem **aprovação de um Administrador** antes que possam confirmar o e-mail e acessar o sistema.

Administradores e Usuários têm painéis dedicados com links dinâmicos configuráveis através de um arquivo `config.yml`.

## Recursos Implementados

*   **Tipos de Usuário:**
    *   **Administrador:** Credenciais definidas via `.env`. Painel de administração para aprovar usuários e acessar links específicos.
    *   **Usuário:** Requer registro e aprovação do administrador. Painel de usuário com links específicos.
*   **Fluxo de Registro com Aprovação:**
    *   Usuário solicita registro.
    *   Usuário recebe e-mail de "pedido recebido".
    *   Administrador é notificado por e-mail sobre o novo pedido.
    *   Administrador aprova (ou rejeita/deleta) o pedido em seu painel.
    *   Após aprovação, o usuário recebe um e-mail de confirmação para validar seu endereço de e-mail (token com validade de 1 hora).
*   **Verificação Humana:**
    *   Desafio matemático simples nas páginas de registro e login.
*   **Login e Sessão:**
    *   Autenticação diferenciada para Administrador (via `.env`) e Usuários (via DB).
    *   Sessão de usuário com duração configurável (Flask-Login).
    *   Proteção CSRF em formulários (Flask-WTF).
*   **Gerenciamento Dinâmico de Firewall (UFW):**
    *   Liberação do IP do cliente (Admin ou Usuário) no `ufw` para todas as portas após login bem-sucedido.
    *   Remoção do IP do cliente do `ufw` após logout.
    *   Comando CLI (`flask setup-firewall`) para configuração inicial segura do `ufw`.
*   **Painéis com Links Dinâmicos:**
    *   Painel do Administrador (`/admin/dashboard`) com lista de usuários pendentes e links configuráveis.
    *   Painel do Usuário (`/dashboard`) com links configuráveis.
    *   Links são definidos em um arquivo `config.yml`.
*   **Segurança:**
    *   Hashing seguro de senhas para usuários do DB (Flask-Bcrypt).
    *   Suporte para HTTPS no servidor de desenvolvimento Flask.
    *   Configurações de cookies de sessão seguros.
*   **Interface:**
    *   Templates para registro, login, painéis de admin/usuário e e-mails.
    *   Comandos CLI para inicialização do banco de dados.

## Tecnologias Utilizadas

*   **Backend:** Python 3, Flask
*   **Banco de Dados:** SQLAlchemy (com SQLite por padrão)
*   **Extensões Flask:**
    *   `Flask-SQLAlchemy`, `Flask-Login`, `Flask-Mail`, `Flask-Bcrypt`, `Flask-WTF`
*   **Configuração:** `PyYAML` (para `config.yml`), `python-dotenv`
*   **Firewall:** UFW (Uncomplicated Firewall) - Linux

## Pré-requisitos

*   Python 3.7+
*   `pip` (gerenciador de pacotes Python)
*   `ufw` instalado e operacional no servidor.
*   Acesso `sudo` para configurar o `ufw` e o arquivo `sudoers`.

## Configuração do Ambiente

1.  **Clone o Repositório (se aplicável).**

2.  **Crie e Ative um Ambiente Virtual Python:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # No Windows: venv\Scripts\activate
    ```

3.  **Instale as Dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as Variáveis de Ambiente (`.env`):**
    *   Copie `.env.example` para `.env`: `cp .env.example .env`
    *   Edite `.env` e configure:
        *   `SECRET_KEY`: Chave secreta longa e aleatória.
        *   **Credenciais do Administrador:**
            *   `ADMIN_EMAIL`: E-mail do administrador principal.
            *   `ADMIN_PASSWORD`: Senha do administrador principal.
            *   `ADMIN_NOTIFICATIONS_EMAIL` (Opcional): E-mail para onde enviar notificações de novos registros (pode ser o mesmo que `ADMIN_EMAIL`).
        *   **Configurações de E-mail (Flask-Mail):**
            *   `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`.
        *   Outras variáveis como `FLASK_RUN_HOST`, `FLASK_RUN_PORT`, SSL, etc.

5.  **Configure os Links Dinâmicos (`config.yml`):**
    *   Copie `config.yml.example` para `config.yml`: `cp config.yml.example config.yml`
    *   Edite `config.yml` para definir os links que aparecerão nos painéis do administrador e do usuário. Veja o formato dentro do arquivo de exemplo.
    *   (Nota: `config.yml` é ignorado pelo Git, então suas configurações locais não serão versionadas).

## Configuração do Banco de Dados

Execute o comando CLI para criar/atualizar as tabelas do banco de dados:
```bash
export FLASK_APP=run.py # ou set FLASK_APP=run.py no Windows
flask init-db
```
*(Se você já tinha um banco `site.db` de uma versão anterior, pode ser necessário removê-lo para que o novo esquema com os campos de tipo de usuário e aprovação seja aplicado corretamente por `db.create_all()`)*.

## Configuração do Firewall (UFW)

**EXTREMAMENTE IMPORTANTE: Siga com CUIDADO.**

1.  **Configurar `sudoers`:**
    O usuário que executa a aplicação Flask (`www-data`, seu usuário local, etc.) precisa de permissão para executar comandos `ufw` específicos via `sudo` sem senha. Edite com `sudo visudo`:
    ```sudoers
    # Substitua 'your_flask_user' pelo usuário correto
    your_flask_user ALL=(ALL) NOPASSWD: /usr/sbin/ufw allow from [0-9.]*
    your_flask_user ALL=(ALL) NOPASSWD: /usr/sbin/ufw delete allow from [0-9.]*
    your_flask_user ALL=(ALL) NOPASSWD: /usr/sbin/ufw status
    your_flask_user ALL=(ALL) NOPASSWD: /usr/sbin/ufw --force enable
    your_flask_user ALL=(ALL) NOPASSWD: /usr/sbin/ufw default deny incoming
    your_flask_user ALL=(ALL) NOPASSWD: /usr/sbin/ufw default allow outgoing
    # Permita a porta SSH correta! Ex: /usr/sbin/ufw allow 22/tcp ou /usr/sbin/ufw allow OpenSSH
    your_flask_user ALL=(ALL) NOPASSWD: /usr/sbin/ufw allow in <PORTA_SSH>/tcp
    your_flask_user ALL=(ALL) NOPASSWD: /usr/sbin/ufw allow in http/tcp
    your_flask_user ALL=(ALL) NOPASSWD: /usr_sbin/ufw allow in https/tcp
    ```
    *Adapte `<PORTA_SSH>` para sua porta SSH real. `http` e `https` referem-se às portas 80 e 443 respectivamente.*

2.  **Executar a Configuração Inicial do Firewall via CLI:**
    **VERIFIQUE SUA PORTA SSH!**
    ```bash
    # Exemplo: flask setup-firewall --ssh-port 2222 --web-ports 80,443
    flask setup-firewall
    ```

## Executando a Aplicação

1.  **Servidor de Desenvolvimento Flask:**
    ```bash
    flask run --host=0.0.0.0 --port=5000
    ```
    (Configure HTTPS em `.env` se necessário para desenvolvimento).

## Endpoints Principais (Rotas da Aplicação)

*   `/` (GET): Página inicial.
*   `/register` (GET, POST): Página de registro de novos usuários.
*   `/login` (GET, POST): Página de login para administradores e usuários.
*   `/logout` (GET): Efetua logout do usuário/administrador logado.
*   `/confirm_email/<token>` (GET): Endpoint para onde o link de confirmação de e-mail (enviado após aprovação) aponta.
*   `/dashboard` (GET): Painel do usuário comum (requer login, aprovação e e-mail confirmado).
*   `/admin/dashboard` (GET): Painel do administrador (requer login como admin).
*   `/admin/users/approve/<int:user_id>` (POST): Ação para o administrador aprovar um usuário pendente.
*   `/admin/users/delete/<int:user_id>` (POST): Ação para o administrador rejeitar (deletar) um usuário pendente ou existente.

## Fluxo Detalhado de Uso e Testes Manuais

1.  **Login do Administrador:**
    *   **Ação:** Acesse a rota `/login`. Insira as credenciais de `ADMIN_EMAIL` e `ADMIN_PASSWORD` definidas no seu arquivo `.env`. Complete a verificação matemática.
    *   **Resultado Esperado:**
        *   Redirecionamento para `/admin/dashboard`.
        *   O painel exibe "Usuários Pendentes de Aprovação" (inicialmente vazio) e os links configurados em `config.yml` para `admin_links`.
        *   O IP da máquina do administrador é adicionado às regras do `ufw` (`sudo ufw status numbered` para verificar).

2.  **Registro de Novo Usuário:**
    *   **Ação:** Em um navegador diferente ou aba anônima, acesse `/register`. Preencha o formulário com um e-mail válido, senha e complete a verificação matemática.
    *   **Resultado Esperado:**
        *   Mensagem flash: "Seu pedido de registro para [email_usuario] foi recebido! Você será notificado por e-mail quando sua conta for aprovada e estiver pronta para confirmação."
        *   Redirecionamento para a página inicial (`/`).
        *   **E-mail para o Usuário:** O usuário recebe um e-mail no endereço fornecido, com o assunto "Seu pedido de registro foi recebido", informando que a conta aguarda aprovação.
        *   **E-mail para o Administrador:** O e-mail configurado em `ADMIN_NOTIFICATIONS_EMAIL` recebe uma notificação com o assunto "Novo Pedido de Registro: [email_usuario]", contendo o e-mail e ID do novo usuário, e um link para `/admin/dashboard`.
        *   **Banco de Dados:** Um novo registro na tabela `user` com `is_approved=False` e `email_confirmed=False`.

3.  **Aprovação do Usuário pelo Administrador:**
    *   **Ação:** Como administrador logado, acesse (ou atualize) `/admin/dashboard`. O novo usuário deve estar listado em "Usuários Pendentes". Clique no botão "Aprovar" para este usuário.
    *   **Resultado Esperado:**
        *   Mensagem flash no painel admin: "Usuário [email_usuario] aprovado com sucesso! E-mail de confirmação enviado."
        *   O usuário desaparece da lista de pendentes.
        *   **Banco de Dados:** Para o usuário, `is_approved` torna-se `True`, `approved_by_email` e `approved_at` são preenchidos. Um `email_confirm_token` e `email_confirm_token_expiration` são gerados e salvos.
        *   **E-mail para o Usuário Aprovado:** O usuário aprovado recebe um novo e-mail com o assunto "Confirme seu endereço de e-mail", contendo um link para `/confirm_email/<token>`.

4.  **Confirmação de E-mail pelo Usuário:**
    *   **Ação:** O usuário clica no link de confirmação recebido no último e-mail.
    *   **Resultado Esperado:**
        *   Redirecionamento para a página de login (`/login`).
        *   Mensagem flash: "Sua conta foi confirmada com sucesso! Agora você pode fazer login."
        *   **Banco de Dados:** Para o usuário, `email_confirmed` torna-se `True`, e o `email_confirm_token` é invalidado (geralmente definido como `None`).

5.  **Login do Usuário Aprovado e Confirmado:**
    *   **Ação:** O usuário acessa `/login` e entra com seu e-mail e senha. Completa a verificação matemática.
    *   **Resultado Esperado:**
        *   Login bem-sucedido. Redirecionamento para `/dashboard`.
        *   O painel do usuário exibe informações da conta e os links configurados em `config.yml` para `user_links`.
        *   O IP da máquina do usuário é adicionado às regras do `ufw`.

6.  **Tentativas de Login Inválidas:**
    *   **Usuário não aprovado:** Tentar login antes da aprovação do admin. **Esperado:** Mensagem "Sua conta ainda não foi aprovada...".
    *   **Usuário aprovado, e-mail não confirmado:** Tentar login após aprovação, mas antes de clicar no link de confirmação. **Esperado:** Mensagem "Sua conta ainda não teve o e-mail confirmado...".

7.  **Logout (Administrador e Usuário):**
    *   **Ação:** Clique no link "Logout".
    *   **Resultado Esperado:**
        *   Redirecionamento para `/login`.
        *   Mensagem flash indicando logout e remoção do IP do firewall.
        *   A regra `allow from <IP_do_deslogado>` é removida do `ufw`.

8.  **Acesso a Rotas Protegidas:**
    *   **Sem login:** Tentar acessar `/dashboard` ou `/admin/dashboard`. **Esperado:** Redirecionamento para `/login`.
    *   **Usuário logado tentando acessar `/admin/dashboard`:** **Esperado:** Redirecionamento para `/dashboard` ou `/index` com mensagem de acesso negado/informativa.
    *   **Admin logado tentando acessar `/dashboard`:** **Esperado:** Redirecionamento para `/admin/dashboard` com mensagem informativa.

## Considerações de Segurança

*   **Configuração `sudoers`:** Crítico. Mínimo privilégio.
*   **HTTPS em Produção:** Use Nginx/Apache com Let's Encrypt.
*   **Limpeza de IPs Expirados (Futuro):** Implementar um cron job.
*   **Proteção contra Ataques:** Rate limiting, fail2ban, etc.

## Estrutura do Projeto (Adições)

```
/
├── app/
│   ├── decorators.py             # Decoradores customizados (ex: @admin_required)
│   ├── config_loader.py          # Utilitário para carregar config.yml
│   └── ... (outros arquivos como antes)
├── config.yml                    # Configuração de links dinâmicos (local) - não versionado
├── config.yml.example            # Exemplo de config.yml
└── ... (outros arquivos como antes)
```
