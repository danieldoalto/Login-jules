# Login-Jules - Documentação Técnica

## Visão Geral do Sistema

Login-Jules é uma aplicação web Flask que implementa um sistema de login com gerenciamento dinâmico de firewall usando `ufw`. O sistema permite o controle de acesso baseado em autenticação, onde os IPs dos usuários autenticados são automaticamente adicionados às regras de permissão do firewall e removidos quando o usuário faz logout.

## Arquitetura

A aplicação segue uma arquitetura monolítica baseada em Flask, com os seguintes componentes principais:

### Estrutura de Diretórios

```
Login_phyton/
├── app/                      # Pacote principal da aplicação
│   ├── __init__.py           # Inicialização da aplicação e extensões
│   ├── commands.py           # Comandos CLI personalizados
│   ├── config_loader.py      # Carregador de configurações dinâmicas
│   ├── firewall_utils.py     # Utilitários para gerenciamento do firewall
│   ├── forms.py              # Definições de formulários
│   ├── models.py             # Modelos de dados
│   ├── routes.py             # Rotas e controladores
│   ├── templates/            # Templates Jinja2
│   └── utils.py              # Funções utilitárias gerais
├── config.yml                # Configuração de links dinâmicos
├── .env                      # Variáveis de ambiente e segredos
├── instance/                 # Dados específicos da instância (banco de dados)
│   └── site.db               # Banco de dados SQLite
├── logs/                     # Diretório de logs
│   └── app.log               # Arquivo de log principal
├── restart.sh                # Script para reiniciar a aplicação
├── stop.sh                   # Script para parar a aplicação
└── run.py                    # Ponto de entrada da aplicação
```

## Componentes Principais

### 1. Sistema de Autenticação

#### Tipos de Usuário
- **Administrador**: Definido por variáveis de ambiente no `.env`, não persistido no banco de dados
- **Usuário Regular**: Armazenado no banco de dados, requer aprovação do administrador e confirmação de email

#### Fluxo de Autenticação
1. **Registro**: O usuário se registra fornecendo email, senha e resolvendo um desafio matemático
2. **Aprovação**: Um administrador deve aprovar a conta do usuário
3. **Confirmação**: O usuário confirma seu email através de um link enviado por email
4. **Login**: O usuário faz login com email, senha e resolve um desafio matemático
5. **Gerenciamento de Firewall**: O IP do usuário é adicionado às regras de permissão do firewall
6. **Logout**: O IP do usuário é removido das regras de permissão do firewall

### 2. Integração com Firewall (UFW)

O sistema utiliza o UFW (Uncomplicated Firewall) para gerenciar dinamicamente o acesso baseado em autenticação:

#### Principais Funções (firewall_utils.py)
- `allow_ip(ip_address)`: Adiciona o IP do usuário às regras de permissão do firewall
- `deny_ip(ip_address)`: Remove o IP do usuário das regras de permissão do firewall
- `_run_ufw_command(command_str)`: Executa comandos UFW com sudo e gerencia resultados

#### Requisitos de Segurança
- O usuário que executa a aplicação Flask deve ter permissão para executar comandos UFW via sudo sem senha
- Configuração específica no arquivo sudoers é necessária (detalhada nos comentários do código)

### 3. Banco de Dados

- **ORM**: SQLAlchemy
- **Banco de Dados**: SQLite (localizado em `instance/site.db`)
- **Modelos Principais**:
  - `User`: Representa usuários regulares com campos para email, senha, status de aprovação, etc.
  - `AdminUser`: Classe não persistida para representar administradores (dados vêm de variáveis de ambiente)

### 4. Formulários e Validação

- **Biblioteca**: Flask-WTF
- **Proteção CSRF**: Implementada automaticamente em todos os formulários
- **Desafio Matemático**: Implementado em formulários de login e registro como verificação anti-bot
- **Validação de Senha**: Regras personalizadas para força de senha

### 5. Sistema de Logging

- **Configuração**: Logging rotativo configurado em `app/__init__.py`
- **Arquivo de Log**: `logs/app.log`
- **Rotação**: Arquivos de log são limitados a 1MB com até 10 backups
- **Formato**: `timestamp level: message [in file:line]`

### 6. Configuração

- **Variáveis de Ambiente**: Armazenadas em `.env` para configurações sensíveis
  - `ADMIN_EMAIL`: Email do administrador
  - `ADMIN_PASSWORD`: Senha do administrador
  - `SECRET_KEY`: Chave secreta para sessões Flask
  - `MAIL_*`: Configurações de email

- **Links Dinâmicos**: Configurados em `config.yml`
  - Define links para dashboards de administrador e usuário
  - Carregados dinamicamente na inicialização da aplicação

## Fluxos Principais

### 1. Fluxo de Login

```
┌─────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│ Formulário  │────►│ Validação de   │────►│ Autenticação   │────►│ Adição de IP   │
│ de Login    │     │ Desafio Math   │     │ (Admin/User)   │     │ ao Firewall    │
└─────────────┘     └────────────────┘     └────────────────┘     └────────────────┘
                                                   │                      │
                                                   ▼                      ▼
                                           ┌────────────────┐     ┌────────────────┐
                                           │ Login_user e   │     │ Redirecionamento│
                                           │ Sessão Flask   │     │ para Dashboard │
                                           └────────────────┘     └────────────────┘
```

### 2. Fluxo de Registro e Aprovação

```
┌─────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│ Formulário  │────►│ Validação e    │────►│ Criação de     │────►│ Email com Link │
│ de Registro │     │ Desafio Math   │     │ Usuário (DB)   │     │ de Confirmação │
└─────────────┘     └────────────────┘     └────────────────┘     └────────────────┘
                                                                          │
                                                                          ▼
┌─────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│ Login       │◄────│ Confirmação    │◄────│ Aprovação por  │◄────│ Verificação    │
│ Permitido   │     │ de Email       │     │ Administrador  │     │ de Token       │
└─────────────┘     └────────────────┘     └────────────────┘     └────────────────┘
```

## Segurança

### Medidas Implementadas

1. **Hashing de Senha**: Implementado com Flask-Bcrypt
2. **Proteção CSRF**: Implementada em todos os formulários com Flask-WTF
3. **Desafio Matemático**: Proteção anti-bot em formulários de login e registro
4. **Decoradores de Proteção de Rota**: Verificação de autenticação e tipo de usuário
5. **Gerenciamento Dinâmico de Firewall**: Controle de acesso baseado em IP
6. **Validação de Entrada**: Sanitização e validação de todas as entradas do usuário
7. **Logging Abrangente**: Registro de atividades e tentativas de acesso

### Considerações de Segurança

- O sistema requer configuração adequada de sudoers para operações de firewall
- Recomenda-se usar HTTPS em produção
- As senhas de administrador devem ser fortes e alteradas regularmente

## Scripts de Utilitários

- **restart.sh**: Para e reinicia a aplicação
- **stop.sh**: Para todos os processos relacionados à aplicação

## Requisitos do Sistema

- Python 3.8+
- UFW instalado e configurado
- Permissões sudo para comandos UFW
- Dependências Python listadas em requirements.txt

## Inicialização do Banco de Dados

Para inicializar o banco de dados:
```
flask init-db
```

## Execução da Aplicação

Para executar a aplicação:
```
./restart.sh
```

Para parar a aplicação:
```
./stop.sh
```
