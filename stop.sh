#!/bin/bash

# Define a porta do aplicativo
APP_PORT=5000

# Encontrar o PID do processo que está usando a porta
PROCESS_PID=$(lsof -t -i:${APP_PORT})

# Verificar se um processo foi encontrado
if [ -n "$PROCESS_PID" ]; then
    echo "Parando processo Flask (PID: $PROCESS_PID) que está usando a porta ${APP_PORT}..."
    kill -9 $PROCESS_PID
    echo "Processo parado com sucesso."
else
    echo "Nenhum processo encontrado rodando na porta ${APP_PORT}."
fi
