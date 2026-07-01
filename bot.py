import os
import re
import random
import logging
import asyncio
from datetime import datetime, timedelta
import requests

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# ============ CONFIGURAÇÃO ============
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not TELEGRAM_TOKEN:
    print("ERRO: TELEGRAM_BOT_TOKEN não configurado")
    exit(1)

print("Token do bot carregado com sucesso")

# ============ GLOBAL STATE ============
GLOBAL_BOT_MODE = "NORMAL"  # "NORMAL" or "REDIRECT"
USER_LANGUAGE = {}  # Store user's selected language

# ============ ARMAZENAMENTO ============
campanhas_ativas = {}

# ============ LANGUAGE MESSAGES ============
LANGUAGE_MESSAGES = {
    "english": {
        "name": "English",
        "flag": "🇬🇧",
        "welcome": (
            "🤖 *Welcome to the Content Bot!*\n\n"
            "Create automatic content for your channel "
            "or get football news.\n\n"
            "*Select an option:*"
        ),
        "menu": {
            "create": "📝 Create Campaign",
            "football": "⚽ Football News",
            "status": "📊 My Status",
            "stop": "🛑 Stop Campaign",
            "help": "❓ Help",
            "back": "◀️ Back",
            "refresh": "🔄 Refresh"
        },
        "campaign": (
            "📝 *Create Campaign*\n\n"
            "Send a message in this format:\n"
            "`@channel | topic | days`\n\n"
            "*Example:*\n"
            "`@AIToolsDail | Football | 7`\n\n"
            "The bot will post every 90 minutes."
        ),
        "status_text": "📊 *Your Status*",
        "no_campaign": "📊 *No active campaigns*\n\nUse 'Create Campaign' to start.",
        "help_text": (
            "❓ *Help*\n\n"
            "*Commands:*\n"
            "/start - Language selection\n"
            "/football - Football news\n"
            "/status - Check active campaign\n"
            "/stop - Stop campaign\n\n"
            "*Campaign format:*\n"
            "`@channel | topic | days`\n\n"
            "*Example:*\n"
            "`@mychannel | Football | 7`"
        ),
        "campaign_started": "🚀 *Campaign Started!*",
        "campaign_stopped": "🛑 *Campaign stopped successfully*",
        "no_active": "🛑 *No active campaigns*",
        "error_post": "❌ Error posting to {channel}. Make sure I'm admin.",
        "join_button": "🔴 CONTACT ADMIN TO JOIN",
        "redirect_title": "📈 *SECRET EA - PREMIUM TRADING*",
        "redirect_welcome": (
            "🔥 *Forex AI Community - SECRET EA*\n\n"
            "Welcome to Forex AI Community - by Secret\n\n"
            "Here you will receive:\n\n"
            "• Daily verified results\n"
            "• Safe & aggressive presets\n"
            "• MyFXBook proofs\n"
            "• Investor access to real accounts\n"
            "• Copytrade information\n"
            "• Exclusive EA updates\n\n"
            "🔹 *Contact @suportforexai to request access!*"
        ),
        "click_to_join": "👇 *Contact the admin below to join:*"
    },
    "spanish": {
        "name": "Español",
        "flag": "🇪🇸",
        "welcome": (
            "🤖 *¡Bienvenido al Bot de Contenido!*\n\n"
            "Crea contenido automático para tu canal "
            "o recibe noticias de fútbol.\n\n"
            "*Selecciona una opción:*"
        ),
        "menu": {
            "create": "📝 Crear Campaña",
            "football": "⚽ Noticias del Fútbol",
            "status": "📊 Mi Estado",
            "stop": "🛑 Parar Campaña",
            "help": "❓ Ayuda",
            "back": "◀️ Volver",
            "refresh": "🔄 Actualizar"
        },
        "campaign": (
            "📝 *Crear Campaña*\n\n"
            "Envía un mensaje en este formato:\n"
            "`@canal | tema | días`\n\n"
            "*Ejemplo:*\n"
            "`@AIToolsDail | Fútbol | 7`\n\n"
            "El bot publicará cada 90 minutos."
        ),
        "status_text": "📊 *Tu Estado*",
        "no_campaign": "📊 *No hay campañas activas*\n\nUsa 'Crear Campaña' para comenzar.",
        "help_text": (
            "❓ *Ayuda*\n\n"
            "*Comandos:*\n"
            "/start - Selección de idioma\n"
            "/futbol - Noticias de fútbol\n"
            "/status - Ver campaña activa\n"
            "/parar - Parar campaña\n\n"
            "*Formato de campaña:*\n"
            "`@canal | tema | días`\n\n"
            "*Ejemplo:*\n"
            "`@micanal | Fútbol | 7`"
        ),
        "campaign_started": "🚀 *¡Campaña Iniciada!*",
        "campaign_stopped": "🛑 *Campaña detenida con éxito*",
        "no_active": "🛑 *No hay campañas activas*",
        "error_post": "❌ Error al publicar en {channel}. Asegúrate de que soy administrador.",
        "join_button": "🔴 CONTACTAR ADMIN PARA UNIRSE",
        "redirect_title": "📈 *SECRET EA - TRADING PREMIUM*",
        "redirect_welcome": (
            "🔥 *Comunidad Forex AI - SECRET EA*\n\n"
            "Bienvenido a la Comunidad Forex AI - by Secret\n\n"
            "Aquí recibirás:\n\n"
            "• Resultados diarios verificados\n"
            "• Presets seguros y agresivos\n"
            "• Pruebas de MyFXBook\n"
            "• Acceso de inversor a cuentas reales\n"
            "• Información de Copytrade\n"
            "• Actualizaciones exclusivas de EA\n\n"
            "🔹 *¡Contacta a @suportforexai para solicitar acceso!*"
        ),
        "click_to_join": "👇 *Contacta al administrador abajo para unirte:*"
    },
    "french": {
        "name": "Français",
        "flag": "🇫🇷",
        "welcome": (
            "🤖 *Bienvenue sur le Bot de Contenu !*\n\n"
            "Créez du contenu automatique pour votre chaîne "
            "ou recevez des actualités football.\n\n"
            "*Sélectionnez une option :*"
        ),
        "menu": {
            "create": "📝 Créer une Campagne",
            "football": "⚽ Actualités Football",
            "status": "📊 Mon Statut",
            "stop": "🛑 Arrêter la Campagne",
            "help": "❓ Aide",
            "back": "◀️ Retour",
            "refresh": "🔄 Actualiser"
        },
        "campaign": (
            "📝 *Créer une Campagne*\n\n"
            "Envoyez un message au format :\n"
            "`@canal | sujet | jours`\n\n"
            "*Exemple :*\n"
            "`@AIToolsDail | Football | 7`\n\n"
            "Le bot publiera toutes les 90 minutes."
        ),
        "status_text": "📊 *Votre Statut*",
        "no_campaign": "📊 *Aucune campagne active*\n\nUtilisez 'Créer une Campagne' pour commencer.",
        "help_text": (
            "❓ *Aide*\n\n"
            "*Commandes :*\n"
            "/start - Sélection de langue\n"
            "/football - Actualités football\n"
            "/status - Voir la campagne active\n"
            "/stop - Arrêter la campagne\n\n"
            "*Format de campagne :*\n"
            "`@canal | sujet | jours`\n\n"
            "*Exemple :*\n"
            "`@machaine | Football | 7`"
        ),
        "campaign_started": "🚀 *Campagne Lancée !*",
        "campaign_stopped": "🛑 *Campagne arrêtée avec succès*",
        "no_active": "🛑 *Aucune campagne active*",
        "error_post": "❌ Erreur lors de la publication sur {channel}. Assurez-vous que je suis administrateur.",
        "join_button": "🔴 CONTACTER L'ADMIN POUR REJOINDRE",
        "redirect_title": "📈 *SECRET EA - TRADING PREMIUM*",
        "redirect_welcome": (
            "🔥 *Communauté Forex AI - SECRET EA*\n\n"
            "Bienvenue dans la Communauté Forex AI - by Secret\n\n"
            "Vous recevrez ici :\n\n"
            "• Résultats quotidiens vérifiés\n"
            "• Presets sécurisés et agressifs\n"
            "• Preuves MyFXBook\n"
            "• Accès investisseur à des comptes réels\n"
            "• Informations Copytrade\n"
            "• Mises à jour exclusives EA\n\n"
            "🔹 *Contactez @suportforexai pour demander l'accès !*"
        ),
        "click_to_join": "👇 *Contactez l'administrateur ci-dessous pour rejoindre :*"
    }
}

# ============ FUNÇÕES DE NOTÍCIAS DE FUTEBOL ============
def obter_noticias_futebol():
    try:
        response = requests.get("https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id=4328", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("events"):
                eventos = data["events"][:5]
                noticias = []
                for evento in eventos:
                    item = f"⚽ **{evento.get('strEvent', 'Jogo')}**\n"
                    item += f"📅 {evento.get('dateEvent', 'Data a definir')}\n"
                    item += f"🏆 {evento.get('strLeague', 'Liga')}\n"
                    noticias.append(item)
                return "\n\n".join(noticias)
    except:
        pass
    
    noticias_futebol = [
        "⚽ **Real Madrid vs Barcelona**\n📅 Neste fim de semana\n🏆 O Clássico promete emoção!",
        "⚽ **Messi lidera Argentina**\n📅 Eliminatórias\n🏆 A seleção se prepara para o próximo jogo",
        "⚽ **Champions League**\n📅 Semifinais\n🏆 Os melhores times da Europa competem",
        "⚽ **Janela de Transferências**\n📅 Temporada de contratações\n🏆 Grandes movimentos na Europa",
    ]
    return random.choice(noticias_futebol)

def gerar_noticia_futebol_ia():
    if OPENAI_API_KEY:
        try:
            prompt = "Escreva uma notícia curta de futebol, incluindo resultados ou transferências. Máximo 200 caracteres."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150},
                timeout=10
            )
            if response.status_code == 200:
                texto = response.json()["choices"][0]["message"]["content"].strip()
                return f"⚽ **NOTÍCIAS DO FUTEBOL**\n\n{texto}\n\n#Futebol #Notícias"
        except:
            pass
    
    templates = [
        "⚽ **ÚLTIMA HORA**\n\nReal Madrid vence com gol nos últimos minutos.\n\n#LaLiga",
        "⚽ **MERCADO DA BOLA**\n\nClube busca reforçar elenco para próxima temporada.\n\n#Transferências",
        "⚽ **LESÃO IMPORTANTE**\n\nJogador estrela ficará de fora do próximo jogo.\n\n#Lesão",
        "⚽ **DECLARAÇÕES**\n\nTécnico confia no time para vencer o título.\n\n#Entrevista",
    ]
    return random.choice(templates)

# ============ GERAÇÃO DE CONTEÚDO ============
def gerar_conteudo(tema, dia, num_publicacao, total_publicacoes):
    if OPENAI_API_KEY:
        try:
            prompt = f"Escreva uma publicação curta sobre '{tema}'. Publicação {num_publicacao} de {total_publicacoes} para o Dia {dia}. Inclua hashtags."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150},
                timeout=10
            )
            if response.status_code == 200:
                texto = response.json()["choices"][0]["message"]["content"].strip()
                return f"{texto}\n\n📅 Dia {dia} • {num_publicacao}/{total_publicacoes}"
        except:
            pass
    
    templates = [
        f"🤖 **{tema.upper()}** - Informação diária!",
        f"💡 **DICA DE {tema.upper()}** - Mantenha-se consistente!",
        f"📢 **ATUALIZAÇÃO DE {tema.upper()}** - Não perca!",
        f"🔥 **{tema.upper()}** - Aja hoje!",
    ]
    publicacao = random.choice(templates)
    publicacao += f"\n\n📅 Dia {dia} • {num_publicacao}/{total_publicacoes}\n#{tema.replace(' ', '')}"
    return publicacao

# ============ MENUS ============
def language_selection_menu():
    teclado = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_english")],
        [InlineKeyboardButton("🇪🇸 Español", callback_data="lang_spanish")],
        [InlineKeyboardButton("🇫🇷 Français", callback_data="lang_french")],
    ]
    return InlineKeyboardMarkup(teclado)

def main_menu(lang="english"):
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    menu = messages["menu"]
    
    teclado = [
        [InlineKeyboardButton(menu["create"], callback_data="criar_campanha")],
        [InlineKeyboardButton(menu["football"], callback_data="noticias_futebol")],
        [InlineKeyboardButton(menu["status"], callback_data="meu_status")],
        [InlineKeyboardButton(menu["stop"], callback_data="parar")],
        [InlineKeyboardButton(menu["help"], callback_data="ajuda")],
    ]
    return InlineKeyboardMarkup(teclado)

def back_button(lang="english"):
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(messages["menu"]["back"], callback_data="voltar")
    ]])

def refresh_button(lang="english"):
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(messages["menu"]["refresh"], callback_data="noticias_futebol")],
        [InlineKeyboardButton(messages["menu"]["back"], callback_data="voltar")]
    ])

# ============ CONTACT BUTTON ============
def contact_admin_button(lang="english"):
    """Create a button that opens a chat with the admin"""
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    # This button opens a chat with @suportforexai
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(messages["join_button"], url="https://t.me/suportforexai")
    ]])

# ============ FOREX REDIRECT FUNCTION ============
def send_forex_redirect(update, context, lang="english"):
    """Send the Secret EA channel redirect message in the selected language"""
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    
    # Send welcome message with title
    update.message.reply_text(
        f"{messages['redirect_title']}\n\n{messages['redirect_welcome']}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Send contact button
    keyboard = [[InlineKeyboardButton(messages["join_button"], url="https://t.me/suportforexai")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        messages["click_to_join"],
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# ============ MANIPULADORES DO BOT ============
def start_command(update, context):
    """Comando /start - Mostra seleção de idioma"""
    global GLOBAL_BOT_MODE
    
    # If in REDIRECT mode, go directly to Forex redirect
    if GLOBAL_BOT_MODE == "REDIRECT":
        send_forex_redirect(update, context, "english")
        return
    
    update.message.reply_text(
        "🌍 *Select your language / Elige tu idioma / Choisissez votre langue*\n\n"
        "Please choose your preferred language:\n"
        "Por favor, elige tu idioma preferido:\n"
        "Veuillez choisir votre langue préférée :",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=language_selection_menu()
    )

def language_button_handler(update, context):
    """Manipula a seleção de idioma"""
    global GLOBAL_BOT_MODE
    
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Extract language from callback data
    lang = data.replace("lang_", "")
    USER_LANGUAGE[user_id] = lang
    
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    
    # If in REDIRECT mode, show Forex redirect message
    if GLOBAL_BOT_MODE == "REDIRECT":
        query.edit_message_text(
            f"{messages['redirect_title']}\n\n{messages['redirect_welcome']}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        keyboard = [[InlineKeyboardButton(messages["join_button"], url="https://t.me/suportforexai")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(
            messages["click_to_join"],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Show normal welcome message in selected language
    query.edit_message_text(
        messages["welcome"],
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(lang)
    )

def manipulador_botoes(update, context):
    """Manipula cliques nos botões"""
    global GLOBAL_BOT_MODE
    
    query = update.callback_query
    data = query.data
    
    # Check if it's a language selection button
    if data.startswith("lang_"):
        language_button_handler(update, context)
        return
    
    query.answer()
    user_id = query.from_user.id
    lang = USER_LANGUAGE.get(user_id, "english")
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    menu = messages["menu"]
    
    # If in REDIRECT mode, show Forex redirect
    if GLOBAL_BOT_MODE == "REDIRECT":
        query.edit_message_text(
            f"{messages['redirect_title']}\n\n{messages['redirect_welcome']}",
            parse_mode=ParseMode.MARKDOWN
        )
        keyboard = [[InlineKeyboardButton(messages["join_button"], url="https://t.me/suportforexai")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(
            messages["click_to_join"],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    if data == "criar_campanha":
        query.edit_message_text(
            messages["campaign"],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_button(lang)
        )
    
    elif data == "noticias_futebol":
        noticia = gerar_noticia_futebol_ia()
        query.edit_message_text(
            f"⚽ *NOTÍCIAS DO FUTEBOL*\n\n{noticia}\n\n"
            "Use /futebol para mais notícias.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=refresh_button(lang)
        )
    
    elif data == "meu_status":
        campanha = campanhas_ativas.get(user_id)
        if campanha:
            dias_restantes = (campanha['data_fim'] - datetime.now()).days
            texto = (
                f"{messages['status_text']}\n\n"
                f"Canal: {campanha['canal']}\n"
                f"Tema: {campanha['tema']}\n"
                f"Publicações: {campanha['publicacoes']}\n"
                f"Dias restantes: {dias_restantes}"
            )
        else:
            texto = messages["no_campaign"]
        
        query.edit_message_text(
            texto,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_button(lang)
        )
    
    elif data == "parar":
        if user_id in campanhas_ativas:
            if 'trabalhos' in context.chat_data and user_id in context.chat_data['trabalhos']:
                context.chat_data['trabalhos'][user_id].schedule_removal()
                del context.chat_data['trabalhos'][user_id]
            campanhas_ativas.pop(user_id, None)
            texto = messages["campaign_stopped"]
        else:
            texto = messages["no_active"]
        
        query.edit_message_text(
            texto,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_button(lang)
        )
    
    elif data == "ajuda":
        query.edit_message_text(
            messages["help_text"],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_button(lang)
        )
    
    elif data == "voltar":
        query.edit_message_text(
            messages["welcome"],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(lang)
        )

def futebol_command(update, context):
    """Comando /futebol - Notícias de futebol"""
    global GLOBAL_BOT_MODE
    
    user_id = update.effective_user.id
    lang = USER_LANGUAGE.get(user_id, "english")
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    
    # If in REDIRECT mode, show Forex redirect
    if GLOBAL_BOT_MODE == "REDIRECT":
        send_forex_redirect(update, context, lang)
        return
    
    noticia = gerar_noticia_futebol_ia()
    update.message.reply_text(
        f"⚽ *NOTÍCIAS DO FUTEBOL*\n\n{noticia}\n\n"
        "Use /futebol para mais notícias.",
        parse_mode=ParseMode.MARKDOWN
    )

def manipular_mensagem(update, context):
    """Processa mensagens - verifica comandos REDIRECT/REVERSE primeiro"""
    global GLOBAL_BOT_MODE
    
    user_id = update.effective_user.id
    texto = update.message.text.strip()
    
    # ============ SECRET ADMIN COMMANDS ============
    if texto == "REDIRECT":
        GLOBAL_BOT_MODE = "REDIRECT"
        update.message.reply_text(
            "🔴 *Redirect Mode ACTIVATED!*\n\n"
            "The bot will now redirect users to the Secret EA channel.\n"
            "Send REVERSE to deactivate.",
            parse_mode=ParseMode.MARKDOWN
        )
        print("🔄 BOT MODE CHANGED: REDIRECT")
        return
    
    elif texto == "REVERSE":
        GLOBAL_BOT_MODE = "NORMAL"
        update.message.reply_text(
            "✅ *Normal Mode RESTORED!*\n\n"
            "The bot is now working normally.\n"
            "Send REDIRECT to activate redirect mode.",
            parse_mode=ParseMode.MARKDOWN
        )
        print("🔄 BOT MODE CHANGED: NORMAL")
        return
    
    # ============ NORMAL BOT LOGIC ============
    lang = USER_LANGUAGE.get(user_id, "english")
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    
    # If in REDIRECT mode, show Forex redirect for any message
    if GLOBAL_BOT_MODE == "REDIRECT":
        send_forex_redirect(update, context, lang)
        return
    
    if '|' not in texto:
        start_command(update, context)
        return
    
    partes = [p.strip() for p in texto.split('|')]
    if len(partes) != 3:
        update.message.reply_text("Use: `@canal | tema | dias`", parse_mode=ParseMode.MARKDOWN)
        return
    
    canal, tema, dias_parte = partes
    dias_match = re.search(r'(\d+)', dias_parte)
    if not dias_match:
        update.message.reply_text("Por favor, especifique um número válido de dias")
        return
    
    dias = int(dias_match.group(1))
    if not canal.startswith('@'):
        update.message.reply_text("O canal deve começar com @")
        return
    
    # Parar campanha existente
    if user_id in campanhas_ativas:
        if 'trabalhos' in context.chat_data and user_id in context.chat_data['trabalhos']:
            context.chat_data['trabalhos'][user_id].schedule_removal()
        campanhas_ativas.pop(user_id, None)
    
    # Criar nova campanha
    data_fim = datetime.now() + timedelta(days=dias)
    campanhas_ativas[user_id] = {
        'canal': canal,
        'tema': tema,
        'dias': dias,
        'data_inicio': datetime.now(),
        'data_fim': data_fim,
        'publicacoes': 0,
        'num_publicacao': 1
    }
    
    if 'trabalhos' not in context.chat_data:
        context.chat_data['trabalhos'] = {}
    trabalho = context.job_queue.run_repeating(publicar_no_canal, interval=5400, first=2, context=user_id)
    context.chat_data['trabalhos'][user_id] = trabalho
    
    update.message.reply_text(
        f"{messages['campaign_started']}\n\n"
        f"📢 Canal: {canal}\n"
        f"📝 Tema: {tema}\n"
        f"📅 Duração: {dias} dias\n"
        f"⏱️ A cada 90 minutos\n\n"
        f"Use /status para acompanhar o progresso.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(messages["menu"]["status"], callback_data="meu_status")
        ]])
    )

def publicar_no_canal(context):
    trabalho = context.job
    user_id = trabalho.context
    campanha = campanhas_ativas.get(user_id)
    
    if not campanha:
        trabalho.schedule_removal()
        return
    
    if datetime.now() > campanha['data_fim']:
        if user_id in campanhas_ativas:
            campanhas_ativas.pop(user_id)
        trabalho.schedule_removal()
        return
    
    campanha['publicacoes'] += 1
    dia = (datetime.now() - campanha['data_inicio']).days + 1
    num_publicacao = campanha['num_publicacao']
    
    texto = gerar_conteudo(campanha['tema'], dia, num_publicacao, 16)
    
    campanha['num_publicacao'] += 1
    if campanha['num_publicacao'] > 16:
        campanha['num_publicacao'] = 1
    
    try:
        context.bot.send_message(
            chat_id=campanha['canal'],
            text=texto,
            parse_mode=ParseMode.MARKDOWN
        )
        print(f"Publicado em {campanha['canal']} - #{campanha['publicacoes']}")
    except Exception as e:
        print(f"Erro: {e}")
        lang = USER_LANGUAGE.get(user_id, "english")
        messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
        context.bot.send_message(
            chat_id=user_id,
            text=messages["error_post"].format(channel=campanha['canal'])
        )
        if user_id in campanhas_ativas:
            campanhas_ativas.pop(user_id)
        trabalho.schedule_removal()

def status_command(update, context):
    """Comando /status - Ver status da campanha"""
    global GLOBAL_BOT_MODE
    
    user_id = update.effective_user.id
    lang = USER_LANGUAGE.get(user_id, "english")
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    
    # If in REDIRECT mode, show Forex redirect
    if GLOBAL_BOT_MODE == "REDIRECT":
        send_forex_redirect(update, context, lang)
        return
    
    campanha = campanhas_ativas.get(user_id)
    
    if not campanha:
        update.message.reply_text(
            messages["no_campaign"],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(lang)
        )
        return
    
    dias_restantes = (campanha['data_fim'] - datetime.now()).days
    update.message.reply_text(
        f"{messages['status_text']}\n\n"
        f"Canal: {campanha['canal']}\n"
        f"Tema: {campanha['tema']}\n"
        f"Publicações: {campanha['publicacoes']}\n"
        f"Dias restantes: {dias_restantes}\n\n"
        f"Use /parar para finalizar.",
        parse_mode=ParseMode.MARKDOWN
    )

def parar_command(update, context):
    """Comando /parar - Parar campanha"""
    global GLOBAL_BOT_MODE
    
    user_id = update.effective_user.id
    lang = USER_LANGUAGE.get(user_id, "english")
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    
    # If in REDIRECT mode, show Forex redirect
    if GLOBAL_BOT_MODE == "REDIRECT":
        send_forex_redirect(update, context, lang)
        return
    
    if user_id in campanhas_ativas:
        if 'trabalhos' in context.chat_data and user_id in context.chat_data['trabalhos']:
            context.chat_data['trabalhos'][user_id].schedule_removal()
            del context.chat_data['trabalhos'][user_id]
        campanhas_ativas.pop(user_id)
        update.message.reply_text(messages["campaign_stopped"], parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text(
            messages["no_active"],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(lang)
        )

def ajuda_command(update, context):
    """Comando /ajuda - Mostrar ajuda"""
    global GLOBAL_BOT_MODE
    
    user_id = update.effective_user.id
    lang = USER_LANGUAGE.get(user_id, "english")
    messages = LANGUAGE_MESSAGES.get(lang, LANGUAGE_MESSAGES["english"])
    
    # If in REDIRECT mode, show Forex redirect
    if GLOBAL_BOT_MODE == "REDIRECT":
        send_forex_redirect(update, context, lang)
        return
    
    update.message.reply_text(
        messages["help_text"],
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(lang)
    )

# ============ FUNÇÃO PRINCIPAL ============
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("futebol", futebol_command))
    dp.add_handler(CommandHandler("status", status_command))
    dp.add_handler(CommandHandler("parar", parar_command))
    dp.add_handler(CommandHandler("ajuda", ajuda_command))
    
    dp.add_handler(CallbackQueryHandler(manipulador_botoes))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, manipular_mensagem))
    
    print("=" * 50)
    print("🤖 Bot iniciando com seleção de idioma...")
    print("📌 Comandos secretos:")
    print("   REDIRECT - Ativa modo de redirecionamento")
    print("   REVERSE  - Retorna ao modo normal")
    print("=" * 50)
    
    updater.start_polling()
    print("✅ Bot está rodando!")
    updater.idle()

if __name__ == "__main__":
    main()
