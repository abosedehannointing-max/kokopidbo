import os
import re
import random
import logging
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

# ============ ARMAZENAMENTO ============
campanhas_ativas = {}

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
    
    # Notícias de fallback
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
    
    # Templates de notícias
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

# ============ MENU PRINCIPAL ============
def menu_principal():
    """Cria o menu principal com botões"""
    teclado = [
        [InlineKeyboardButton("📝 Criar Campanha", callback_data="criar_campanha")],
        [InlineKeyboardButton("⚽ Notícias do Futebol", callback_data="noticias_futebol")],
        [InlineKeyboardButton("📊 Meu Status", callback_data="meu_status")],
        [InlineKeyboardButton("🛑 Parar Campanha", callback_data="parar")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")],
    ]
    return InlineKeyboardMarkup(teclado)

# ============ MANIPULADORES DO BOT ============
def start(update, context):
    """Comando /start com menu de botões"""
    update.message.reply_text(
        "⚽ *Bem-vindo ao Bot de Conteúdo!*\n\n"
        "Crie conteúdo automático para seu canal "
        "ou receba notícias de futebol.\n\n"
        "*Selecione uma opção:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_principal()
    )

def manipulador_botoes(update, context):
    """Manipula cliques nos botões"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
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
        # Gerar notícia de futebol
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
            "/start - Menu principal\n"
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
    """Processa mensagem com formato: @canal | tema | dias"""
    user_id = update.effective_user.id
    texto = update.message.text.strip()
    
    if '|' not in texto:
        start(update, context)
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
    update.message.reply_text(
        "❓ *Ajuda*\n\n"
        "*Comandos:*\n"
        "/start - Menu principal\n"
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
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("futebol", futebol_command))
    dp.add_handler(CommandHandler("status", status_command))
    dp.add_handler(CommandHandler("parar", parar_command))
    dp.add_handler(CommandHandler("ajuda", ajuda_command))
    
    # Manipuladores de mensagens e botões
    dp.add_handler(CallbackQueryHandler(manipulador_botoes))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, manipular_mensagem))
    
    print("Bot iniciando com menu de botões e notícias de futebol...")
    updater.start_polling()
    print("Bot está rodando!")
    updater.idle()

if __name__ == "__main__":
    main()
