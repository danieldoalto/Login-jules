@echo off
echo Encerrando processos na porta 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do (
    taskkill /pid %%a /f
)
echo Processos encerrados.

echo Ativando ambiente virtual...
call .\venv\Scripts\activate

echo Iniciando a aplicação Flask...
python run.py
