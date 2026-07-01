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
GLOBAL_BOT_MODE = "NORMAL"

# ============ ARMAZENAMENTO ============
campanhas_ativas = {}

# ============ LANGUAGE MESSAGES ============
LANGUAGE_MESSAGES = {
    "english": {
        "welcome": (
            "🇬🇧 *Welcome to Secret EA!*\n\n"
            "🤖 Welcome to Secret EA!\n\n"
            "Choose your language and access exclusive content.\n\n"
            "📊 *Forex AI Community – by Secret*\n\n"
            "Here you will receive:\n\n"
            "• Daily verified results\n"
            "• Safe & aggressive presets\n"
            "• MyFXBook proofs\n"
            "• Investor access to real accounts\n"
            "• Copytrade information\n"
            "• Exclusive EA updates\n\n"
            "🔹 *Join us now and start your journey!*"
        ),
        "button": "🔴 JOIN FOREX AI COMMUNITY",
        "url": "https://t.me/+N6dbbnO8JBBmYzJh",
        "language_name": "English"
    },
    "spanish": {
        "welcome": (
            "🇪🇸 *¡Bienvenido a Secret EA!*\n\n"
            "🤖 ¡Bienvenido a Secret EA!\n\n"
            "Elige tu idioma y accede al contenido exclusivo.\n\n"
            "📊 *Comunidad Forex AI – by Secret*\n\n"
            "Aquí recibirás:\n\n"
            "• Resultados diarios verificados\n"
            "• Presets seguros y agresivos\n"
            "• Pruebas de MyFXBook\n"
            "• Acceso de inversor a cuentas reales\n"
            "• Información de Copytrade\n"
            "• Actualizaciones exclusivas de EA\n\n"
            "🔹 *¡Únete ahora y comienza tu viaje!*"
        ),
        "button": "🔴 UNIRSE A LA COMUNIDAD FOREX AI",
        "url": "https://t.me/+N6dbbnO8JBBmYzJh",
        "language_name": "Español"
    },
    "french": {
        "welcome": (
            "🇫🇷 *Bienvenue sur Secret EA !*\n\n"
            "🤖 Bienvenue sur Secret EA !\n\n"
            "Choisissez votre langue et accédez au contenu exclusif.\n\n"
            "📊 *Communauté Forex AI – by Secret*\n\n"
            "Vous recevrez ici :\n\n"
            "• Résultats quotidiens vérifiés\n"
            "• Presets sécurisés et agressifs\n"
            "• Preuves MyFXBook\n"
            "• Accès investisseur à des comptes réels\n"
            "• Informations Copytrade\n"
            "• Mises à jour exclusives EA\n\n"
            "🔹 *Rejoignez-nous maintenant et commencez votre voyage !*"
        ),
        "button": "🔴 REJOINDRE LA COMMUNAUTÉ FOREX AI",
        "url": "https://t.me/+N6dbbnO8JBBmYzJh",
        "language_name": "Français"
    }
}

# ============ FUNÇÕES DE NOTÍCIAS DE FUTEBOL ============
def obter_noticias_futebol():
    """Obtém notícias de futebol de API gratuita"""
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
    """Gera notícia de futebol usando IA ou template"""
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

# ============ MENU PRINCIPAL (Portuguese) ============
def menu_principal():
    """Cria o menu principal com botões em português"""
    teclado = [
        [InlineKeyboardButton("📝 Criar Campanha", callback_data="criar_campanha")],
        [InlineKeyboardButton("⚽ Notícias do Futebol", callback_data="noticias_futebol")],
        [InlineKeyboardButton("📊 Meu Status", callback_data="meu_status")],
        [InlineKeyboardButton("🛑 Parar Campanha", callback_data="parar")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")],
    ]
    return InlineKeyboardMarkup(teclado)

# ============ LANGUAGE SELECTION MENU ============
def language_selection_menu():
    """Cria o menu de seleção de idioma"""
    teclado = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_english")],
        [InlineKeyboardButton("🇪🇸 Español", callback_data="lang_spanish")],
        [InlineKeyboardButton("🇫🇷 Français", callback_data="lang_french")],
    ]
    return InlineKeyboardMarkup(teclado)

# ============ MANIPULADORES DO BOT ============
def start_command(update, context):
    """Comando /start - Always shows language selection first"""
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
    query = update.callback_query
    query.answer()
    
    data = query.data
    
    if data == "lang_english":
        lang_data = LANGUAGE_MESSAGES["english"]
        welcome_text = lang_data["welcome"]
        button_text = lang_data["button"]
        url = lang_data["url"]
        
        query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        keyboard = [[InlineKeyboardButton(button_text, url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(
            "👇 *Click below to join the community:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    elif data == "lang_spanish":
        lang_data = LANGUAGE_MESSAGES["spanish"]
        welcome_text = lang_data["welcome"]
        button_text = lang_data["button"]
        url = lang_data["url"]
        
        query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        keyboard = [[InlineKeyboardButton(button_text, url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(
            "👇 *Haz clic abajo para unirte a la comunidad:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    elif data == "lang_french":
        lang_data = LANGUAGE_MESSAGES["french"]
        welcome_text = lang_data["welcome"]
        button_text = lang_data["button"]
        url = lang_data["url"]
        
        query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        keyboard = [[InlineKeyboardButton(button_text, url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text(
            "👇 *Cliquez ci-dessous pour rejoindre la communauté :*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

def manipulador_botoes(update, context):
    """Manipula cliques nos botões"""
    query = update.callback_query
    data = query.data
    
    # Check if it's a language selection button
    if data.startswith("lang_"):
        language_button_handler(update, context)
        return
    
    query.answer()
    user_id = query.from_user.id
    
    if data == "criar_campanha":
        query.edit_message_text(
            "📝 *Criar Campanha*\n\n"
            "Envie uma mensagem neste formato:\n"
            "`@canal | tema | dias`\n\n"
            "*Exemplo:*\n"
            "`@AIToolsDail | Futebol | 7`\n\n"
            "O bot publicará a cada 90 minutos.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Voltar", callback_data="voltar")
            ]])
        )
    
    elif data == "noticias_futebol":
        noticia = gerar_noticia_futebol_ia()
        query.edit_message_text(
            f"⚽ *NOTÍCIAS DO FUTEBOL*\n\n{noticia}\n\n"
            "Use /futebol para mais notícias.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Atualizar", callback_data="noticias_futebol")],
                [InlineKeyboardButton("◀️ Voltar", callback_data="voltar")]
            ])
        )
    
    elif data == "meu_status":
        campanha = campanhas_ativas.get(user_id)
        if campanha:
            dias_restantes = (campanha['data_fim'] - datetime.now()).days
            texto = (
                f"📊 *Seu Status*\n\n"
                f"Canal: {campanha['canal']}\n"
                f"Tema: {campanha['tema']}\n"
                f"Publicações: {campanha['publicacoes']}\n"
                f"Dias restantes: {dias_restantes}"
            )
        else:
            texto = "📊 *Nenhuma campanha ativa*\n\nUse 'Criar Campanha' para começar."
        
        query.edit_message_text(
            texto,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Voltar", callback_data="voltar")
            ]])
        )
    
    elif data == "parar":
        if user_id in campanhas_ativas:
            if 'trabalhos' in context.chat_data and user_id in context.chat_data['trabalhos']:
                context.chat_data['trabalhos'][user_id].schedule_removal()
                del context.chat_data['trabalhos'][user_id]
            campanhas_ativas.pop(user_id, None)
            texto = "🛑 *Campanha parada com sucesso*"
        else:
            texto = "🛑 *Nenhuma campanha ativa*"
        
        query.edit_message_text(
            texto,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Voltar", callback_data="voltar")
            ]])
        )
    
    elif data == "ajuda":
        query.edit_message_text(
            "❓ *Ajuda*\n\n"
            "*Comandos:*\n"
            "/start - Menu de idiomas\n"
            "/futebol - Notícias de futebol\n"
            "/status - Ver campanha\n"
            "/parar - Parar campanha\n\n"
            "*Formato da campanha:*\n"
            "`@canal | tema | dias`\n\n"
            "*Exemplo:*\n"
            "`@meucanal | Futebol | 7`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Voltar", callback_data="voltar")
            ]])
        )
    
    elif data == "voltar":
        query.edit_message_text(
            "⚽ *Menu Principal*\n\n"
            "Selecione uma opção:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=menu_principal()
        )

def futebol_command(update, context):
    """Comando /futebol - Notícias de futebol"""
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
            "🔴 *Modo Redirecionamento ATIVADO!*\n\n"
            "O bot agora irá redirecionar todos os usuários para a comunidade Forex.",
            parse_mode=ParseMode.MARKDOWN
        )
        print("🔄 BOT MODE CHANGED: REDIRECT")
        return
    
    elif texto == "REVERSE":
        GLOBAL_BOT_MODE = "NORMAL"
        update.message.reply_text(
            "✅ *Modo Normal RESTAURADO!*\n\n"
            "O bot agora está funcionando normalmente.",
            parse_mode=ParseMode.MARKDOWN
        )
        print("🔄 BOT MODE CHANGED: NORMAL")
        return
    
    # ============ NORMAL BOT LOGIC ============
    if '|' not in texto:
        # Show language selection first, not the menu
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
        f"🚀 *Campanha Iniciada!*\n\n"
        f"📢 Canal: {canal}\n"
        f"📝 Tema: {tema}\n"
        f"📅 Duração: {dias} dias\n"
        f"⏱️ A cada 90 minutos\n\n"
        f"Use /status para acompanhar o progresso.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 Ver Status", callback_data="meu_status")
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
        context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Erro ao publicar em {campanha['canal']}. Certifique-se de que sou administrador."
        )
        if user_id in campanhas_ativas:
            campanhas_ativas.pop(user_id)
        trabalho.schedule_removal()

def status_command(update, context):
    """Comando /status - Ver status da campanha"""
    user_id = update.effective_user.id
    campanha = campanhas_ativas.get(user_id)
    
    if not campanha:
        update.message.reply_text(
            "📊 *Nenhuma campanha ativa*\n\nUse /start para começar.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=menu_principal()
        )
        return
    
    dias_restantes = (campanha['data_fim'] - datetime.now()).days
    update.message.reply_text(
        f"📊 *Status da Campanha*\n\n"
        f"📢 Canal: `{campanha['canal']}`\n"
        f"📝 Tema: `{campanha['tema']}`\n"
        f"📨 Publicações: `{campanha['publicacoes']}`\n"
        f"📅 Dias restantes: `{dias_restantes}`\n\n"
        f"Use /parar para finalizar.",
        parse_mode=ParseMode.MARKDOWN
    )

def parar_command(update, context):
    """Comando /parar - Parar campanha"""
    user_id = update.effective_user.id
    
    if user_id in campanhas_ativas:
        if 'trabalhos' in context.chat_data and user_id in context.chat_data['trabalhos']:
            context.chat_data['trabalhos'][user_id].schedule_removal()
            del context.chat_data['trabalhos'][user_id]
        campanhas_ativas.pop(user_id)
        update.message.reply_text("✅ *Campanha parada*", parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text(
            "❌ *Nenhuma campanha ativa*\n\nUse /start para começar.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=menu_principal()
        )

def ajuda_command(update, context):
    """Comando /ajuda - Mostrar ajuda"""
    update.message.reply_text(
        "❓ *Ajuda*\n\n"
        "*Comandos:*\n"
        "/start - Menu de idiomas\n"
        "/futebol - Notícias de futebol\n"
        "/status - Ver campanha ativa\n"
        "/parar - Parar campanha\n\n"
        "*Botões:* Use o menu para acessar todos os recursos.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_principal()
    )

# ============ FUNÇÃO PRINCIPAL ============
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Comandos
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("futebol", futebol_command))
    dp.add_handler(CommandHandler("status", status_command))
    dp.add_handler(CommandHandler("parar", parar_command))
    dp.add_handler(CommandHandler("ajuda", ajuda_command))
    
    # Manipuladores de mensagens e botões
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
