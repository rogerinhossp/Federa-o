# Federa-o
Bot da federação 
# Telegram Global Ban Bot

Bot simples de ban local + global para Telegram.

## Como usar

1. Crie o bot no @BotFather e pegue o token
2. Coloque seu ID do Telegram em `SUPERUSERS`
3. Instale as dependências: `pip install -r requirements.txt`
4. Rode: `python bot.py`
5. Adicione o bot como **administrador** nos grupos (com permissão de banir usuários)

## Comandos

- `/ban` — Ban local
- `/unban` — Unban local  
- `/gban` — Ban global (só superusuários)
- `/ungban` — Remove ban global
- `/gbanlist` — Lista de bans

## Deploy

Pode rodar em VPS, Railway, Render, etc.
