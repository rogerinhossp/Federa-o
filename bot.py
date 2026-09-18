import logging
import sqlite3
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatMemberStatus

# ==================== CONFIGURAÇÃO ====================
BOT_TOKEN = "8930807380:AAHDghtCplDwcduSYr4RBLgGphpDYyhG-zg"          # Token do @BotFather
SUPERUSERS = [7630139994]             # Seu ID do Telegram (pode colocar vários)
DB_NAME = "global_bans.db"
# ======================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- Banco de dados ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS global_bans (
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            banned_by INTEGER,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def is_globally_banned(user_id: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM global_bans WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_global_ban(user_id: int, reason: str, banned_by: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO global_bans (user_id, reason, banned_by) VALUES (?, ?, ?)",
        (user_id, reason, banned_by)
    )
    conn.commit()
    conn.close()

def remove_global_ban(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM global_bans WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ---------- Helpers ----------
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.effective_chat or update.effective_chat.type == "private":
        return False
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)

def is_superuser(user_id: int) -> bool:
    return user_id in SUPERUSERS

async def get_user_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pega o usuário por reply ou argumento"""
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    
    if context.args:
        arg = context.args[0]
        if arg.isdigit():
            try:
                user = await context.bot.get_chat(int(arg))
                return user
            except Exception:
                return None
        # username
        try:
            user = await context.bot.get_chat(arg if arg.startswith("@") else f"@{arg}")
            return user
        except Exception:
            return None
    return None

# ---------- Comandos ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔨 **Bot de Ban Global**\n\n"
        "Comandos:\n"
        "• `/ban` (reply ou ID) — Ban local\n"
        "• `/unban` (reply ou ID) — Unban local\n"
        "• `/gban` (reply ou ID) [motivo] — Ban global (só superusuários)\n"
        "• `/ungban` (reply ou ID) — Remove ban global\n"
        "• `/gbanlist` — Lista de bans globais\n\n"
        "O bot precisa ser **admin** com permissão de banir.",
        parse_mode="Markdown"
    )

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Apenas administradores podem usar este comando.")
        return

    user = await get_user_from_message(update, context)
    if not user:
        await update.message.reply_text("Responda a uma mensagem ou use: /ban <id ou @username>")
        return

    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"✅ {user.mention_html()} foi banido deste grupo.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao banir: {e}")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Apenas administradores.")
        return

    user = await get_user_from_message(update, context)
    if not user:
        await update.message.reply_text("Responda a uma mensagem ou use: /unban <id>")
        return

    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"✅ {user.mention_html()} foi desbanido.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

async def gban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superuser(update.effective_user.id):
        await update.message.reply_text("❌ Apenas superusuários podem usar /gban.")
        return

    user = await get_user_from_message(update, context)
    if not user:
        await update.message.reply_text("Responda a uma mensagem ou use: /gban <id> [motivo]")
        return

    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Sem motivo"
    add_global_ban(user.id, reason, update.effective_user.id)

    # Tenta banir no grupo atual também
    if update.effective_chat.type != "private":
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        except Exception:
            pass

    await update.message.reply_text(
        f"🔨 **Ban Global aplicado**\n"
        f"Usuário: {user.mention_html()}\n"
        f"Motivo: {reason}",
        parse_mode="HTML"
    )

async def ungban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superuser(update.effective_user.id):
        await update.message.reply_text("❌ Apenas superusuários.")
        return

    user = await get_user_from_message(update, context)
    if not user:
        await update.message.reply_text("Responda ou use: /ungban <id>")
        return

    remove_global_ban(user.id)
    await update.message.reply_text(f"✅ Ban global de {user.mention_html()} removido.", parse_mode="HTML")

async def gbanlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_superuser(update.effective_user.id):
        await update.message.reply_text("❌ Apenas superusuários.")
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, reason, banned_at FROM global_bans ORDER BY banned_at DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Lista de bans globais vazia.")
        return

    text = "📋 **Últimos bans globais:**\n\n"
    for uid, reason, date in rows:
        text += f"• `{uid}` — {reason} ({date})\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------- Auto-ban ao entrar ----------
async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if is_globally_banned(member.id):
            try:
                await context.bot.ban_chat_member(update.effective_chat.id, member.id)
                await update.message.reply_text(
                    f"🔨 {member.mention_html()} está na lista de **ban global** e foi banido automaticamente.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Erro ao auto-banir {member.id}: {e}")

# ---------- Main ----------
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("gban", gban_command))
    app.add_handler(CommandHandler("ungban", ungban_command))
    app.add_handler(CommandHandler("gbanlist", gbanlist_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))

    print("Bot iniciado...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
