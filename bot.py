import os
import re
import random
import logging
from datetime import datetime, timedelta
import requests

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# Configuracion
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN no esta configurado")
    exit(1)

print("Token del bot cargado correctamente")

# Almacenamiento
campanas_activas = {}

# ============ FUNCIONES DE NOTICIAS DE FUTBOL ============
def obtener_noticias_futbol():
    """Obtiene noticias de futbol desde API gratuita"""
    try:
        # Usar API gratuita de noticias (TheSportsDB o similar)
        response = requests.get("https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id=4328", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("events"):
                eventos = data["events"][:5]
                noticias = []
                for evento in eventos:
                    noticia = f"⚽ **{evento.get('strEvent', 'Partido')}**\n"
                    noticia += f"📅 {evento.get('dateEvent', 'Fecha por confirmar')}\n"
                    noticia += f"🏆 {evento.get('strLeague', 'Liga')}\n"
                    noticias.append(noticia)
                return "\n\n".join(noticias)
    except:
        pass
    
    # Noticias de respaldo (generadas localmente)
    noticias_futbol = [
        "⚽ **Real Madrid vs Barcelona**\n📅 Este fin de semana\n🏆 El clasico promete emocion!",
        "⚽ **Messi lidera Argentina**\n📅 Eliminatorias\n🏆 La seleccion se prepara para el proximo partido",
        "⚽ **Champions League**\n📅 Semifinales\n🏆 Los mejores equipos de Europa se enfrentan",
        "⚽ **Mercado de pases**\n📅 Temporada de fichajes\n🏆 Grandes movimientos en Europa",
    ]
    return random.choice(noticias_futbol)

def generar_noticia_futbol_ia():
    """Genera noticia de futbol usando IA o plantilla"""
    if OPENAI_API_KEY:
        try:
            prompt = "Escribe una noticia corta de futbol actual, incluyendo resultados o fichajes. Maximo 200 caracteres."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150},
                timeout=10
            )
            if response.status_code == 200:
                texto = response.json()["choices"][0]["message"]["content"].strip()
                return f"⚽ **NOTICIA DE FUTBOL**\n\n{texto}\n\n#Futbol #Noticias"
        except:
            pass
    
    # Plantillas de noticias
    plantillas = [
        "⚽ **ULTIMA HORA**\n\nEl Real Madrid gana su partido con un gol en los ultimos minutos.\n\n#LaLiga",
        "⚽ **MERCADO DE FICHAJES**\n\nClub busca reforzar su plantilla para la proxima temporada.\n\n#Fichajes",
        "⚽ **LESION IMPORTANTE**\n\nJugador estrella sera baja para el proximo partido.\n\n#Lesion",
        "⚽ **DECLARACIONES**\n\nEl entrenador confia en su equipo para ganar el titulo.\n\n#Entrevista",
    ]
    return random.choice(plantillas)

# ============ FUNCIONES DE CONTENIDO GENERAL ============
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

# ============ MANEJADORES DEL BOT ============
def menu_principal():
    """Crea el menu de botones principal"""
    teclado = [
        [InlineKeyboardButton("📝 Crear Campaña", callback_data="crear_campana")],
        [InlineKeyboardButton("⚽ Noticias de Futbol", callback_data="noticias_futbol")],
        [InlineKeyboardButton("📊 Mi Estado", callback_data="mi_estado")],
        [InlineKeyboardButton("🛑 Detener Campaña", callback_data="detener")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="ayuda")],
    ]
    return InlineKeyboardMarkup(teclado)

def start(update, context):
    """Maneja el comando /start con menu de botones"""
    update.message.reply_text(
        "⚽ *Bienvenido al Bot de Contenido!*\n\n"
        "Puedes crear contenido automatico para tu canal "
        "o recibir noticias de futbol.\n\n"
        "*Selecciona una opcion:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_principal()
    )

def botones(update, context):
    """Maneja los clics en los botones"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "crear_campana":
        query.edit_message_text(
            "📝 *Crear Campaña*\n\n"
            "Envía el mensaje con este formato:\n"
            "`@canal | tema | días`\n\n"
            "*Ejemplo:*\n"
            "`@AIToolsDail | Futbol | 7`\n\n"
            "El bot publicará cada 90 minutos.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Volver", callback_data="volver")
            ]])
        )
    
    elif data == "noticias_futbol":
        # Generar noticia de futbol
        noticia = generar_noticia_futbol_ia()
        query.edit_message_text(
            f"⚽ *NOTICIAS DE FUTBOL*\n\n{noticia}\n\n"
            "¿Quieres más noticias? Usa /futbol para actualizar.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Actualizar", callback_data="noticias_futbol")],
                [InlineKeyboardButton("◀️ Volver", callback_data="volver")]
            ])
        )
    
    elif data == "mi_estado":
        campana = campanas_activas.get(user_id)
        if campana:
            dias_restantes = (campana['fecha_fin'] - datetime.now()).days
            texto = (
                f"📊 *Tu Estado*\n\n"
                f"Canal: {campana['canal']}\n"
                f"Tema: {campana['tema']}\n"
                f"Publicaciones: {campana['publicaciones']}\n"
                f"Días restantes: {dias_restantes}"
            )
        else:
            texto = "📊 *No tienes campañas activas*\n\nUsa 'Crear Campaña' para comenzar."
        
        query.edit_message_text(
            texto,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Volver", callback_data="volver")
            ]])
        )
    
    elif data == "detener":
        if user_id in campanas_activas:
            if 'jobs' in context.chat_data and user_id in context.chat_data['jobs']:
                context.chat_data['jobs'][user_id].schedule_removal()
                del context.chat_data['jobs'][user_id]
            campanas_activas.pop(user_id, None)
            texto = "🛑 *Campaña detenida exitosamente*"
        else:
            texto = "🛑 *No tienes campañas activas*"
        
        query.edit_message_text(
            texto,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Volver", callback_data="volver")
            ]])
        )
    
    elif data == "ayuda":
        query.edit_message_text(
            "❓ *Ayuda*\n\n"
            "*Comandos:*\n"
            "/start - Menu principal\n"
            "/futbol - Noticias de futbol\n"
            "/estado - Ver campaña\n"
            "/detener - Detener campaña\n\n"
            "*Formato para campaña:*\n"
            "`@canal | tema | días`\n\n"
            "*Ejemplo:*\n"
            "`@micanal | Futbol | 7`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Volver", callback_data="volver")
            ]])
        )
    
    elif data == "volver":
        query.edit_message_text(
            "⚽ *Menu Principal*\n\n"
            "Selecciona una opcion:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=menu_principal()
        )

def futbol_command(update, context):
    """Comando /futbol - Noticias de futbol"""
    noticia = generar_noticia_futbol_ia()
    update.message.reply_text(
        f"⚽ *NOTICIAS DE FUTBOL*\n\n{noticia}\n\n"
        "Usa /futbol para más noticias.",
        parse_mode=ParseMode.MARKDOWN
    )

def manejar_mensaje(update, context):
    """Procesa el mensaje con formato: @canal | tema | días"""
    user_id = update.effective_user.id
    texto = update.message.text.strip()
    
    if '|' not in texto:
        start(update, context)
        return
    
    partes = [p.strip() for p in texto.split('|')]
    if len(partes) != 3:
        update.message.reply_text("Usa: `@canal | tema | días`", parse_mode=ParseMode.MARKDOWN)
        return
    
    canal, tema, dias_parte = partes
    dias_match = re.search(r'(\d+)', dias_parte)
    if not dias_match:
        update.message.reply_text("Especifica un número de días válido")
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
        f"📅 Duración: {dias} días\n"
        f"⏱️ Cada 90 minutos\n\n"
        f"Usa /estado para ver el progreso.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 Ver Estado", callback_data="mi_estado")
        ]])
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
            text=f"❌ Error al publicar en {campana['canal']}. Verifica que soy administrador."
        )
        if user_id in campanas_activas:
            campanas_activas.pop(user_id)
        job.schedule_removal()

def estado(update, context):
    user_id = update.effective_user.id
    campana = campanas_activas.get(user_id)
    
    if not campana:
        update.message.reply_text(
            "📊 *No hay campaña activa*\n\nUsa /start para comenzar.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=menu_principal()
        )
        return
    
    dias_restantes = (campana['fecha_fin'] - datetime.now()).days
    update.message.reply_text(
        f"📊 *Estado de tu Campaña*\n\n"
        f"📢 Canal: `{campana['canal']}`\n"
        f"📝 Tema: `{campana['tema']}`\n"
        f"📨 Publicaciones: `{campana['publicaciones']}`\n"
        f"📅 Días restantes: `{dias_restantes}`\n\n"
        f"Usa /detener para finalizar.",
        parse_mode=ParseMode.MARKDOWN
    )

def detener(update, context):
    user_id = update.effective_user.id
    
    if user_id in campanas_activas:
        if 'jobs' in context.chat_data and user_id in context.chat_data['jobs']:
            context.chat_data['jobs'][user_id].schedule_removal()
            del context.chat_data['jobs'][user_id]
        campanas_activas.pop(user_id)
        update.message.reply_text("✅ *Campaña detenida*", parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text(
            "❌ *No hay campaña activa*\n\nUsa /start para comenzar.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=menu_principal()
        )

def ayuda(update, context):
    update.message.reply_text(
        "❓ *Ayuda*\n\n"
        "*Comandos:*\n"
        "/start - Menu principal\n"
        "/futbol - Noticias de futbol\n"
        "/estado - Ver campaña activa\n"
        "/detener - Detener campaña\n\n"
        "*Botones:* Usa el menu para acceder a todas las funciones.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_principal()
    )

# ============ FUNCION PRINCIPAL ============
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Comandos
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("futbol", futbol_command))
    dp.add_handler(CommandHandler("estado", estado))
    dp.add_handler(CommandHandler("detener", detener))
    dp.add_handler(CommandHandler("ayuda", ayuda))
    
    # Manejador de mensajes y botones
    dp.add_handler(CallbackQueryHandler(botones))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, manejar_mensaje))
    
    print("Bot iniciando con menu de botones y noticias de futbol...")
    updater.start_polling()
    print("Bot ejecutandose!")
    updater.idle()

if __name__ == "__main__":
    main()
