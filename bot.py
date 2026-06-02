import math
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
user_data = {}

def calculate_spoke_length(flange_diameter, rim_diameter, flange_offset, spoke_count, crosses, rim_offset=0):
    """ТОЧНЫЙ расчёт длины спицы"""
    r_flange = flange_diameter / 2.0
    r_rim = rim_diameter / 2.0
    angle_degrees = 720.0 * crosses / spoke_count
    angle_radians = math.radians(angle_degrees)
    axial_distance = flange_offset + rim_offset / 2.0
    spoke_length_squared = (
        r_rim * r_rim +
        r_flange * r_flange -
        2.0 * r_rim * r_flange * math.cos(angle_radians) +
        axial_distance * axial_distance
    )
    return math.sqrt(spoke_length_squared)

def round_spoke_length(length):
    rounded = math.ceil(length * 2) / 2
    return int(rounded) if rounded.is_integer() else rounded

def calculate_both_sides(flange_diameter, rim_diameter, left_offset, right_offset, spoke_count, crosses, rim_offset=0):
    left_length = calculate_spoke_length(flange_diameter, rim_diameter, left_offset, spoke_count, crosses, rim_offset)
    right_length = calculate_spoke_length(flange_diameter, rim_diameter, right_offset, spoke_count, crosses, rim_offset)
    return left_length, right_length, round_spoke_length(left_length), round_spoke_length(right_length)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📏 Симметричный расчёт", callback_data='symmetric')],
        [InlineKeyboardButton("🔄 Разные стороны", callback_data='asymmetric')],
        [InlineKeyboardButton("📖 Справка", callback_data='help')],
        [InlineKeyboardButton("🔧 Пример", callback_data='example')]
    ]
    await update.message.reply_text(
        "🚴‍♂️ *Калькулятор длины спицы*\n\nВыбери режим расчёта:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 *Справка*\n\n*Параметры для измерения:*\n\n1. **Диаметр фланца втулки** (мм)\n2. **Диаметр обода** (мм)\n3. **Вылет фланца** (мм)\n4. **Количество спиц** (32 или 36)\n5. **Количество крестов** (1-4)\n6. **Смещение обода** (мм)\n\n*Пример:* фланец 44, обод 577, вылет 38, 36 спиц, 3 креста\n→ спицы 281 мм"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def example_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    length = calculate_spoke_length(44, 577, 38, 36, 3, 2)
    rec = round_spoke_length(length)
    await update.message.reply_text(
        f"🔧 *Пример расчёта*\n\nПараметры: 44, 577, 38, 36, 3, 2\n\n📏 Расчётная: *{length:.3f}* мм\n✅ Рекомендуемые: *{rec}* мм",
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if query.data == 'symmetric':
        user_data[user_id] = {'mode': 'symmetric', 'step': 'flange_diameter'}
        await query.edit_message_text(
            "📏 *Симметричный расчёт*\n\nШаг 1 из 6\nВведите *диаметр фланца* (мм):\nПример: `44`",
            parse_mode='Markdown'
        )
    elif query.data == 'asymmetric':
        user_data[user_id] = {'mode': 'asymmetric', 'step': 'flange_diameter'}
        await query.edit_message_text(
            "🔄 *Расчёт для разных сторон*\n\nШаг 1 из 7\nВведите *диаметр фланца* (мм):\nПример: `44`",
            parse_mode='Markdown'
        )
    elif query.data == 'help':
        await query.edit_message_text("📖 Отправь /help для справки")
    elif query.data == 'example':
        await example_command(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_data:
        await update.message.reply_text("Нажми /start, чтобы начать")
        return
    
    data = user_data[user_id]
    step = data.get('step')
    mode = data.get('mode')
    
    try:
        value = float(text)
        
        # СИММЕТРИЧНЫЙ РЕЖИМ
        if mode == 'symmetric':
            if step == 'flange_diameter':
                data['flange_diameter'] = value
                data['step'] = 'rim_diameter'
                await update.message.reply_text(f"✅ Фланец: {value:.1f} мм\n\nВведите *диаметр обода* (мм):", parse_mode='Markdown')
            elif step == 'rim_diameter':
                data['rim_diameter'] = value
                data['step'] = 'flange_offset'
                await update.message.reply_text(f"✅ Обод: {value:.1f} мм\n\nВведите *вылет фланца* (мм):", parse_mode='Markdown')
            elif step == 'flange_offset':
                data['flange_offset'] = value
                data['step'] = 'spoke_count'
                await update.message.reply_text(f"✅ Вылет: {value:.1f} мм\n\nВведите *количество спиц* (32 или 36):", parse_mode='Markdown')
            elif step == 'spoke_count':
                data['spoke_count'] = int(value)
                data['step'] = 'crosses'
                await update.message.reply_text(f"✅ Спиц: {int(value)}\n\nВведите *количество крестов* (1-4):", parse_mode='Markdown')
            elif step == 'crosses':
                data['crosses'] = int(value)
                data['step'] = 'rim_offset'
                await update.message.reply_text(f"✅ Крестов: {int(value)}\n\nВведите *смещение обода* (мм, 0 если симметричный):", parse_mode='Markdown')
            elif step == 'rim_offset':
                data['rim_offset'] = value
                length = calculate_spoke_length(
                    data['flange_diameter'], data['rim_diameter'],
                    data['flange_offset'], data['spoke_count'],
                    data['crosses'], data['rim_offset']
                )
                rec = round_spoke_length(length)
                await update.message.reply_text(
                    f"✅ *Результат*\n\n📏 Расчётная: *{length:.3f}* мм\n✅ Рекомендуемые: *{rec}* мм",
                    parse_mode='Markdown'
                )
                del user_data[user_id]
        
        # АСИММЕТРИЧНЫЙ РЕЖИМ
        elif mode == 'asymmetric':
            if step == 'flange_diameter':
                data['flange_diameter'] = value
                data['step'] = 'rim_diameter'
                await update.message.reply_text(f"✅ Фланец: {value:.1f} мм\n\nВведите *диаметр обода* (мм):", parse_mode='Markdown')
            elif step == 'rim_diameter':
                data['rim_diameter'] = value
                data['step'] = 'left_offset'
                await update.message.reply_text(f"✅ Обод: {value:.1f} мм\n\nВведите *левый вылет* (мм):", parse_mode='Markdown')
            elif step == 'left_offset':
                data['left_offset'] = value
                data['step'] = 'right_offset'
                await update.message.reply_text(f"✅ Левый вылет: {value:.1f} мм\n\nВведите *правый вылет* (мм):", parse_mode='Markdown')
            elif step == 'right_offset':
                data['right_offset'] = value
                data['step'] = 'spoke_count'
                await update.message.reply_text(f"✅ Правый вылет: {value:.1f} мм\n\nВведите *количество спиц*:", parse_mode='Markdown')
            elif step == 'spoke_count':
                data['spoke_count'] = int(value)
                data['step'] = 'crosses'
                await update.message.reply_text(f"✅ Спиц: {int(value)}\n\nВведите *количество крестов*:", parse_mode='Markdown')
            elif step == 'crosses':
                data['crosses'] = int(value)
                data['step'] = 'rim_offset'
                await update.message.reply_text(f"✅ Крестов: {int(value)}\n\nВведите *смещение обода* (мм):", parse_mode='Markdown')
            elif step == 'rim_offset':
                data['rim_offset'] = value
                left_len, right_len, left_rec, right_rec = calculate_both_sides(
                    data['flange_diameter'], data['rim_diameter'],
                    data['left_offset'], data['right_offset'],
                    data['spoke_count'], data['crosses'], data['rim_offset']
                )
                await update.message.reply_text(
                    f"✅ *Результат*\n\n🔵 Левая: {left_len:.3f} мм → {left_rec} мм\n🔴 Правая: {right_len:.3f} мм → {right_rec} мм",
                    parse_mode='Markdown'
                )
                del user_data[user_id]
    
    except ValueError:
        await update.message.reply_text("❌ Введите число (например: 44.5)")

def main():
    if not TOKEN:
        logger.error("Токен не найден!")
        return
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🤖 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
