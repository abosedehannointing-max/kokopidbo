import os
import re
import random
import logging
from datetime import datetime, timedelta
from typing import Dict
import requests

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ============ CONFIGURACIÓN ============
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not TELEGRAM_TOKEN:
    print("❌ ERROR CRÍTICO: TELEGRAM_BOT_TOKEN no está configurado")
    exit(1)

print(f"✅ Token del bot cargado correctamente")
print(f"✅ OpenAI API: {'Configurada' if OPENAI_API_KEY else 'No configurada - usando plantillas'}")

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ ALMACENAMIENTO EN MEMORIA ============
campanas_activas: Dict[int, Dict] = {}

# ============ GENERADOR DE CONTENIDO ============
def generar_contenido(tema: str, dia: int, num_publicacion: int, total_publicaciones: int) -> str:
    """Genera contenido único usando OpenAI o plantillas"""
    
    if OPENAI_API_KEY:
        try:
            prompt = f"Escribe una publicación corta y atractiva para Telegram sobre '{tema}'. Esta es la publicación #{num_publicacion} de {total_publicaciones} para el Día {dia}. Usa emojis, mantén menos de 300 caracteres. Incluye hashtags relevantes."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.9
                },
                timeout=15
            )
            if response.status_code == 200:
                texto = response.json()["choices"][0]["message"]["content"].strip()
                return f"{texto}\n\n📅 Día {dia} • Publicación {num_publicacion}/{total_publicaciones}"
            else:
                logger.error(f"Error OpenAI: {response.status_code}")
        except Exception as e:
            logger.error(f"Excepción OpenAI: {e}")

    # Plantillas de respaldo
    plantillas = [
        f"🤖 **{tema.upper()}** - ¡Información diaria!\nMantente al día con contenido valioso.",
        f"💡 **CONSEJO DE {tema.upper()}**\n¿Quieres dominar {tema}? La consistencia es clave. ¡Sigue aprendiendo cada día!",
        f"📢 **ACTUALIZACIÓN DE {tema.upper()}**\nEl mundo de {tema} avanza rápido. ¡No te quedes atrás!",
        f"🔥 **{tema.upper()}**\nEl éxito en {tema} llega a quienes toman acción. ¡Empieza hoy!",
        f"✨ **DATOS SOBRE {tema.upper()}**\nAquí hay algo valioso sobre {tema} que quizás no sabías."
    ]
    publicacion = random.choice(plantillas)
    publicacion += f"\n\n📅 Día {dia} • Publicación {num_publicacion}/{total_publicaciones}\n"
    publicacion += f"#{tema.replace(' ', '')} #{tema.replace(' ', '')}Diario"
    return publicacion

# ============ MANEJADORES DEL BOT ============
def start(update: Update, context: CallbackContext):
    """Maneja el comando /start"""
    estado_ia = "🧠 Modo IA (OpenAI)" if OPENAI_API_KEY else "📝 Modo Plantillas"
    update.message.reply_text(
        f"🤖 *Bot de Contenido Automático*\n\n"
        f"*Estado:* `{estado_ia}`\n\n"
        f"*Configuración Rápida:*\n"
        f"`@canal | tema | días`\n\n"
        f"*Ejemplo:*\n"
        f"`@AIToolsDail | Herramientas IA | 7 días`\n\n"
        f"*Comandos:*\n"
        f"/estado - Ver tu campaña activa\n"
        f"/detener - Detener tu campaña activa\n"
        f"/ayuda - Mostrar esta ayuda",
        parse_mode=ParseMode.MARKDOWN
    )

def ayuda(update: Update, context: CallbackContext):
    """Maneja el comando /ayuda"""
    update.message.reply_text(
        f"📚 *Comandos Disponibles*\n\n"
        f"/start - Iniciar el bot\n"
        f"/estado - Ver estado de tu campaña\n"
        f"/detener - Detener campaña activa\n"
        f"/ayuda - Mostrar esta ayuda\n\n"
        f"*Formato para empezar:*\n"
        f"`@nombre_canal | tema | días`\n\n"
        f"*Ejemplo:*\n"
        f"`@micanal | Marketing Digital | 7`",
        parse_mode=ParseMode.MARKDOWN
    )

def manejar_mensaje(update: Update, context: CallbackContext):
    """Procesa el mensaje con formato: @canal | tema | días"""
    user_id = update.effective_user.id
    texto = update.message.text.strip()

    if '|' not in texto:
        start(update, context)
        return

    partes = [p.strip() for p in texto.split('|')]
    if len(partes) != 3:
        update.message.reply_text("❌ Formato inválido. Usa: `@canal | tema | días`", parse_mode=ParseMode.MARKDOWN)
        return

    canal, tema, dias_parte = partes
    dias_match = re.search(r'(\d+)', dias_parte)
    if not dias_match:
        update.message.reply_text("❌ Especifica un número válido de días (ej: `7 días` o solo `7`).")
        return

    dias = int(dias_match.group(1))
    if not 1 <= dias <= 30:
        update.message.reply_text("❌ Los días deben estar entre 1 y 30.")
        return
    if not canal.startswith('@'):
        update.message.reply_text("❌ El canal debe comenzar con `@`. Ejemplo: `@micanal`", parse_mode=ParseMode.MARKDOWN)
        return

    # Finalizar campaña existente si la hay
    if user_id in campanas_activas:
        if 'trabajos_campana' in context.chat_data and user_id in context.chat_data['trabajos_campana']:
            context.chat_data['trabajos_campana'][user_id].schedule_removal()
            del context.chat_data['trabajos_campana'][user_id]
        campanas_activas.pop(user_id, None)

    # Crear nueva campaña
    fecha_fin = datetime.now() + timedelta(days=dias)
    campanas_activas[user_id] = {
        'canal': canal,
        'tema': tema,
        'dias': dias,
        'fecha_inicio': datetime.now(),
        'fecha_fin': fecha_fin,
        'publicaciones_hechas': 0,
        'num_publicacion_actual': 1
    }

    # Programar publicaciones cada 90 minutos
    if 'trabajos_campana' not in context.chat_data:
        context.chat_data['trabajos_campana'] = {}
    trabajo = context.job_queue.run_repeating(publicar_al_canal, interval=5400, first=2, context=user_id)
    context.chat_data['trabajos_campana'][user_id] = trabajo

    nota_ia = "🧠 *¡Cada publicación será única y generada por IA!*" if OPENAI_API_KEY else "📝 *Usando plantillas. Agrega `OPENAI_API_KEY` para contenido generado por IA.*"

    update.message.reply_text(
        f"🚀 *¡Campaña Iniciada!*\n\n"
        f"📢 Canal: `{canal}`\n"
        f"📝 Tema: `{tema}`\n"
        f"📅 Duración: `{dias} días`\n"
        f"⏱️ Intervalo: `~90 minutos`\n"
        f"{nota_ia}\n\n"
        f"¡La primera publicación está en camino!",
        parse_mode=ParseMode.MARKDOWN
    )

def publicar_al_canal(context: CallbackContext):
    """Función llamada por el programador para enviar publicaciones"""
    trabajo = context.job
    user_id = trabajo.context
    campana = campanas_activas.get(user_id)

    if not campana:
        trabajo.schedule_removal()
        return

    if datetime.now() > campana['fecha_fin']:
        finalizar_campana(user_id, context)
        trabajo.schedule_removal()
        return

    campana['publicaciones_hechas'] += 1
    dia_numero = (datetime.now() - campana['fecha_inicio']).days + 1
    num_publicacion_actual = campana['num_publicacion_actual']
    total_publicaciones_por_dia = 16

    texto_publicacion = generar_contenido(campana['tema'], dia_numero, num_publicacion_actual, total_publicaciones_por_dia)

    campana['num_publicacion_actual'] += 1
    if campana['num_publicacion_actual'] > total_publicaciones_por_dia:
        campana['num_publicacion_actual'] = 1

    try:
        context.bot.send_message(
            chat_id=campana['canal'],
            text=texto_publicacion,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"✅ Publicado en {campana['canal']} para usuario {user_id}. Total: {campana['publicaciones_hechas']}")
    except Exception as e:
        logger.error(f"❌ Error al publicar en {campana['canal']}. Error: {e}")
        context.bot.send_message(
            chat_id=user_id,
            text=f"❌ *Error Grave:* No se pudo publicar en `{campana['canal']}`.\n\n"
                 f"Asegúrate de que soy administrador en ese canal. Deteniendo campaña.",
            parse_mode=ParseMode.MARKDOWN
        )
        finalizar_campana(user_id, context)
        if 'trabajos_campana' in context.chat_data and user_id in context.chat_data['trabajos_campana']:
            context.chat_data['trabajos_campana'][user_id].schedule_removal()
            del context.chat_data['trabajos_campana'][user_id]

def estado(update: Update, context: CallbackContext):
    """Muestra el estado de la campaña activa del usuario"""
    user_id = update.effective_user.id
    campana = campanas_activas.get(user_id)

    if not campana:
        update.message.reply_text("❌ No hay campaña activa. Comienza una con `@canal | tema | días`", parse_mode=ParseMode.MARKDOWN)
        return

    dias_pasados = (datetime.now() - campana['fecha_inicio']).days
    dias_restantes = (campana['fecha_fin'] - datetime.now()).days
    porcentaje_progreso = (campana['publicaciones_hechas'] / (campana['dias'] * 16)) * 100

    update.message.reply_text(
        f"📊 *Estado de la Campaña*\n\n"
        f"📢 Canal: `{campana['canal']}`\n"
        f"📝 Tema: `{campana['tema']}`\n"
        f"📨 Publicaciones hechas: `{campana['publicaciones_hechas']}`\n"
        f"📅 Día `{dias_pasados + 1}` de `{campana['dias']}`\n"
        f"⏰ Días restantes: `{dias_restantes}`\n"
        f"📈 Progreso: `{porcentaje_progreso:.1f}%`\n\n"
        f"Usa /detener para finalizar esta campaña.",
        parse_mode=ParseMode.MARKDOWN
    )

def detener(update: Update, context: CallbackContext):
    """Detiene la campaña activa del usuario"""
    user_id = update.effective_user.id
    campana = campanas_activas.pop(user_id, None)

    if not campana:
        update.message.reply_text("❌ No hay campaña activa para detener.")
        return

    if 'trabajos_campana' in context.chat_data and user_id in context.chat_data['trabajos_campana']:
        context.chat_data['trabajos_campana'][user_id].schedule_removal()
        del context.chat_data['trabajos_campana'][user_id]

    update.message.reply_text(
        f"🛑 *Campaña Detenida*\n\n"
        f"📝 Tema: `{campana['tema']}`\n"
        f"📨 Total de publicaciones: `{campana['publicaciones_hechas']}`\n\n"
        f"Puedes comenzar una nueva en cualquier momento.",
        parse_mode=ParseMode.MARKDOWN
    )

def finalizar_campana(user_id: int, context: CallbackContext):
    """Limpia una campaña finalizada o fallida"""
    campana = campanas_activas.pop(user_id, None)
    if campana:
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *¡Campaña Completada!*\n\n"
                     f"📝 Tema: `{campana['tema']}`\n"
                     f"📨 Total de publicaciones: `{campana['publicaciones_hechas']}`\n"
                     f"📅 Duración: `{campana['dias']} días`\n\n"
                     f"¡Gracias por usar el bot! Comienza una nueva campaña cuando estés listo.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"No se pudo notificar al usuario {user_id}: {e}")

def manejar_error(update, context):
    """Registra errores causados por actualizaciones"""
    logger.warning(f"Actualización {update} causó error {context.error}")

# ============ FUNCIÓN PRINCIPAL ============
def main():
    """Inicia el bot"""
    print("=" * 50)
    print("🤖 Iniciando Bot de Contenido Automático...")
    print(f"   Token del Bot: {'✅ Encontrado' if TELEGRAM_TOKEN else '❌ Faltante'}")
    print(f"   OpenAI API: {'✅ Configurada' if OPENAI_API_KEY else '❌ No configurada'}")
    print("=" * 50)
    
    # Crear el Updater
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Agregar manejadores de comandos
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("estado", estado))
    dp.add_handler(CommandHandler("detener", detener))
    dp.add_handler(CommandHandler("ayuda", ayuda))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, manejar_mensaje))
    dp.add_error_handler(manejar_error)

    # Iniciar el Bot
    print("🚀 Bot iniciando y escuchando mensajes...")
    updater.start_polling()
    print("✅ ¡El bot está EN VIVO y esperando comandos en Telegram!")
    print("=" * 50)
    print("Envía /start a tu bot en Telegram para comenzar")
    print("=" * 50)

    # Mantener el bot en ejecución
    updater.idle()

if __name__ == '__main__':
    main()
