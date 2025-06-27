#!/bin/bash

# --- Verificação de Segurança ---
# Impede que o script seja executado como root (com sudo)
if [ "$EUID" -eq 0 ]; then
  echo "[ERRO] Não execute este script com sudo ou como root."
  echo "A aplicação deve ser executada pelo seu usuário normal ('daniel')."
  exit 1
fi

# --- Lógica do Script ---
# Encontrar e matar o processo Flask em execução
APP_PORT=5000
# O comando lsof pode falhar se não encontrar nada, então suprimimos o erro.
PROCESS_PID=$(lsof -t -i:${APP_PORT} 2>/dev/null)

if [ -n "$PROCESS_PID" ]; then
    echo "Matando processo Flask existente no PID: $PROCESS_PID"
    kill -9 $PROCESS_PID
    # Aguardar um pouco para garantir que a porta seja liberada
    sleep 2
else
    echo "Nenhum processo Flask encontrado na porta ${APP_PORT}."
fi

# Iniciar o aplicativo
echo "Iniciando o aplicativo Flask..."
/home/daniel/python/Login_phyton/venv/bin/python run.py
