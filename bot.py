import os
import re
import random
import logging
from datetime import datetime, timedelta
import requests

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Configuracion
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN no esta configurado")
    exit(1)

print("Token del bot cargado correctamente")

# Almacenamiento
campanas_activas = {}

def generar_contenido(tema, dia, num_publicacion, total_publicaciones):
    if OPENAI_API_KEY:
        try:
            prompt = f"Escribe una publicacion corta sobre '{tema}'. Publicacion {num_publicacion} de {total_publicaciones} para el Dia {dia}. Incluye hashtags."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150},
                timeout=10
            )
            if response.status_code == 200:
                texto = response.json()["choices"][0]["message"]["content"].strip()
                return f"{texto}\n\n📅 Dia {dia} • {num_publicacion}/{total_publicaciones}"
        except:
            pass
    
    plantillas = [
        f"🤖 **{tema.upper()}** - Informacion diaria!",
        f"💡 **Consejo de {tema.upper()}** - Mantente consistente!",
        f"📢 **Actualizacion de {tema.upper()}** - No te lo pierdas!",
        f"🔥 **{tema.upper()}** - Toma accion hoy!",
    ]
    publicacion = random.choice(plantillas)
    publicacion += f"\n\n📅 Dia {dia} • {num_publicacion}/{total_publicaciones}\n#{tema.replace(' ', '')}"
    return publicacion

def start(update, context):
    update.message.reply_text(
        "🤖 *Bot de Contenido Automatico*\n\n"
        "*Configuracion:*\n"
        "`@canal | tema | dias`\n\n"
        "*Ejemplo:*\n"
        "`@AIToolsDail | IA Tools | 7`\n\n"
        "*Comandos:*\n"
        "/estado - Ver campaña\n"
        "/detener - Detener campaña",
        parse_mode=ParseMode.MARKDOWN
    )

def manejar_mensaje(update, context):
    user_id = update.effective_user.id
    texto = update.message.text.strip()
    
    if '|' not in texto:
        start(update, context)
        return
    
    partes = [p.strip() for p in texto.split('|')]
    if len(partes) != 3:
        update.message.reply_text("Usa: @canal | tema | dias")
        return
    
    canal, tema, dias_parte = partes
    dias_match = re.search(r'(\d+)', dias_parte)
    if not dias_match:
        update.message.reply_text("Especifica un numero de dias valido")
        return
    
    dias = int(dias_match.group(1))
    if not canal.startswith('@'):
        update.message.reply_text("El canal debe empezar con @")
        return
    
    # Detener campaña existente
    if user_id in campanas_activas:
        if 'jobs' in context.chat_data and user_id in context.chat_data['jobs']:
            context.chat_data['jobs'][user_id].schedule_removal()
        campanas_activas.pop(user_id, None)
    
    # Crear nueva campaña
    fecha_fin = datetime.now() + timedelta(days=dias)
    campanas_activas[user_id] = {
        'canal': canal,
        'tema': tema,
        'dias': dias,
        'fecha_inicio': datetime.now(),
        'fecha_fin': fecha_fin,
        'publicaciones': 0,
        'num_publicacion': 1
    }
    
    if 'jobs' not in context.chat_data:
        context.chat_data['jobs'] = {}
    job = context.job_queue.run_repeating(publicar, interval=5400, first=2, context=user_id)
    context.chat_data['jobs'][user_id] = job
    
    update.message.reply_text(
        f"🚀 *Campaña Iniciada!*\n\n"
        f"📢 Canal: {canal}\n"
        f"📝 Tema: {tema}\n"
        f"📅 Duracion: {dias} dias\n"
        f"⏱️ Cada 90 minutos",
        parse_mode=ParseMode.MARKDOWN
    )

def publicar(context):
    job = context.job
    user_id = job.context
    campana = campanas_activas.get(user_id)
    
    if not campana:
        job.schedule_removal()
        return
    
    if datetime.now() > campana['fecha_fin']:
        if user_id in campanas_activas:
            campanas_activas.pop(user_id)
        job.schedule_removal()
        return
    
    campana['publicaciones'] += 1
    dia = (datetime.now() - campana['fecha_inicio']).days + 1
    num_post = campana['num_publicacion']
    
    texto = generar_contenido(campana['tema'], dia, num_post, 16)
    
    campana['num_publicacion'] += 1
    if campana['num_publicacion'] > 16:
        campana['num_publicacion'] = 1
    
    try:
        context.bot.send_message(
            chat_id=campana['canal'],
            text=texto,
            parse_mode=ParseMode.MARKDOWN
        )
        print(f"Publicado en {campana['canal']} - #{campana['publicaciones']}")
    except Exception as e:
        print(f"Error: {e}")
        context.bot.send_message(
            chat_id=user_id,
            text=f"Error al publicar en {campana['canal']}. Deteniendo campaña."
        )
        if user_id in campanas_activas:
            campanas_activas.pop(user_id)
        job.schedule_removal()

def estado(update, context):
    user_id = update.effective_user.id
    campana = campanas_activas.get(user_id)
    
    if not campana:
        update.message.reply_text("No hay campaña activa")
        return
    
    dias_restantes = (campana['fecha_fin'] - datetime.now()).days
    update.message.reply_text(
        f"📊 *Estado*\n\n"
        f"Canal: {campana['canal']}\n"
        f"Tema: {campana['tema']}\n"
        f"Publicaciones: {campana['publicaciones']}\n"
        f"Dias restantes: {dias_restantes}",
        parse_mode=ParseMode.MARKDOWN
    )

def detener(update, context):
    user_id = update.effective_user.id
    
    if user_id in campanas_activas:
        if 'jobs' in context.chat_data and user_id in context.chat_data['jobs']:
            context.chat_data['jobs'][user_id].schedule_removal()
            del context.chat_data['jobs'][user_id]
        campanas_activas.pop(user_id)
        update.message.reply_text("✅ Campaña detenida")
    else:
        update.message.reply_text("No hay campaña activa")

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("estado", estado))
    dp.add_handler(CommandHandler("detener", detener))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, manejar_mensaje))
    
    print("Bot iniciando...")
    updater.start_polling()
    print("Bot ejecutandose!")
    updater.idle()

if __name__ == "__main__":
    main()
