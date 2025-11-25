import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
URL_PRAIAS_PE = "https://pt.wikipedia.org/wiki/Lista_de_praias_de_Pernambuco"

# FUNÇÃO DE SCRAPING — PRAIAS DE PERNAMBUCO

def get_praias_pe():
    """
    Extrai:
      - Resumo inicial da página
      - Lista de praias por município
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(URL_PRAIAS_PE, headers=headers)

    if resp.status_code != 200:
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")
    article = soup.find("div", class_="mw-parser-output")
    if not article:
        return None, None

    # RESUMO 
    parags = article.find_all("p")
    textos = [p.get_text().strip() for p in parags if p.get_text().strip()]
    resumo = textos[0][:2000] if textos else ""

    # PRAIAS POR MUNICÍPIO 
    praias_por_municipio = {}
    current_city = None

    for tag in article.find_all(["h2", "h3", "ul"]):

        # Detecta município
        if tag.name in ["h2", "h3"]:
            titulo = tag.get_text().strip()
            titulo = titulo.replace("[editar | editar código-fonte]", "").strip()

            if titulo not in ["Referências", "Ver também"]:
                current_city = titulo
                praias_por_municipio[current_city] = []

        # Lista de praias
        elif tag.name == "ul" and current_city:
            for li in tag.find_all("li"):
                praia = li.get_text().strip()
                praias_por_municipio[current_city].append(praia)

    return resumo, praias_por_municipio

# HANDLERS DO BOT

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🏖️ *Bem-vindo ao TurisIA – Praias de Pernambuco!*\n\n"
        "Eu posso te mostrar todas as praias do estado de Pernambuco, "
        "organizadas por município, direto da Wikipedia.\n\n"
        "👉 Para começar, use o comando: /praias"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


async def praias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Buscando lista de praias de Pernambuco...")

    resumo, praias = get_praias_pe()

    if not resumo:
        await update.message.reply_text("Não consegui acessar a Wikipedia 😢")
        return

    # Salva em cache
    context.bot_data["praias_pe"] = praias

    # Envia resumo
    await update.message.reply_text(
        "🌊 *Lista de Praias de Pernambuco*\n\n" + resumo,
        parse_mode="Markdown"
    )

    # Cria lista de botões
    keyboard = []
    linha = []

    for cidade in praias.keys():
        linha.append(InlineKeyboardButton(cidade, callback_data=f"cidade_{cidade}"))
        if len(linha) == 2:
            keyboard.append(linha)
            linha = []

    if linha:
        keyboard.append(linha)

    await update.message.reply_text(
        "Selecione um município:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cidades_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("cidade_"):
        cidade = data.replace("cidade_", "")

        praias = context.bot_data.get("praias_pe", {})
        lista = praias.get(cidade, [])

        if not lista:
            await query.message.reply_text(f"Não encontrei praias em {cidade}.")
            return

        texto = f"*Praias de {cidade}:*\n\n"
        texto += "\n".join([f"• {p}" for p in lista])

        await query.message.reply_text(texto, parse_mode="Markdown")


# ======================================================
# MAIN
# ======================================================

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("praias", praias))
    app.add_handler(CallbackQueryHandler(cidades_handler))

    print("Bot Praias de Pernambuco iniciado! Use /start")
    app.run_polling()


if __name__ == "__main__":
    main()