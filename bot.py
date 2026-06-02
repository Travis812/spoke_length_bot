import math
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения Railway
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Хранение данных пользователя (в памяти)
user_data = {}

def calculate_spoke_length(flange_diameter, rim_diameter, flange_offset, spoke_count, crosses, rim_offset=0):
    """Расчёт длины спицы для одной стороны"""
    r_flange = flange_diameter / 2.0
    r_rim = rim_diameter / 2.0
    angle_rad = math.radians(720 * crosses / spoke_count)
    axial_distance = flange_offset + rim_offset / 2.0
    
    spoke_length = math.sqrt(
        r_rim**2 + r_flange**2 
        - 2 * r_rim * r_flange * math.cos(angle_rad)
        + axial_distance**2
    )
    return spoke_length

def round_spoke_length(length):
    """Округление до рекомендуемой длины"""
    rounded = math.ceil(length * 2) / 2
    return int(rounded) if rounded.is_integer() else rounded

def calculate_both_sides(flange_diameter, rim_diameter, left_offset, right_offset, spoke_count, crosses, rim_offset=0):
    """Расчёт длины спиц для левой и правой стороны"""
    left_length = calculate_spoke_length(flange_diameter, rim_diameter, left_offset, spoke_count, crosses, rim_offset)
    right_length = calculate_spoke_length(flange_diameter, rim_diameter, right_offset, spoke_count, crosses, rim_offset)
    return left_length, right_length, round_spoke_length(left_length), round_spoke_length(right_length)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    
    keyboard = [
        [InlineKeyboardButton("📏 Рассчитать спицу (симметрично)", callback_data='calculate_symmetric')],
        [InlineKeyboardButton("🔄 Рассчитать спицы (разные стороны)", callback_data='calculate_asymmetric')],
        [InlineKeyboardButton("📖 Справка", callback_data='help')],
        [InlineKeyboardButton("🔧 Примеры", callback_data='examples')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🚴‍♂️ Привет, {update.effective_user.first_name}!\n\n"
        "Я бот для расчёта длины велосипедной спицы.\n\n"
        "Выбери режим расчёта:",
        reply_markup=reply_markup
    )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 *Как пользоваться ботом*

*Режим 1: Симметричный расчёт*
Подходит, когда вылеты левого и правого фланца одинаковые

*Режим 2: Разные стороны*
Для втулок с разными вылетами (дисковые тормоза)

📏 *Как измерить параметры:*
• *Фланец втулки* — расстояние между центрами противоположных отверстий
• *Обод* — внутренний диаметр
• *Вылет* — от центра втулки до фланца по оси
• *Кресты* — 1, 2, 3 или 4

⚠️ *Важно:* все размеры в миллиметрах
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Команда /examples
async def examples(update: Update, context: ContextTypes.DEFAULT_TYPE):
    examples_text = """
🔧 *Примеры расчётов*

*Симметричная втулка (36 спиц, обод 577 мм)*
• Фланец 44 мм, вылет 38 мм, смещение 2 мм
  ➜ 3 креста → спицы 281 мм

*Асимметричная втулка (под диск)*
• Фланец 44 мм, обод 577 мм
• Левый вылет: 32 мм, Правый вылет: 45 мм
  ➜ 3 креста → левые 274 мм, правые 287 мм

*Горный велосипед (32 спицы)*
• Фланец 50 мм, обод 560 мм
• Левый вылет: 35 мм, Правый вылет: 42 мм
  ➜ 3 креста → левые 273 мм, правые 282 мм
    """
    await update.message.reply_text(examples_text, parse_mode='Markdown')

# Обработка кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == 'calculate_symmetric':
        user_data[user_id] = {'mode': 'symmetric', 'step': 'flange_diameter'}
        await query.edit_message_text(
            "📏 *Симметричный расчёт*\n\n"
            "Шаг 1 из 6\n\n"
            "Введите *диаметр фланца втулки* (мм):\n"
            "Пример: `44`",
            parse_mode='Markdown'
        )
    
    elif query.data == 'calculate_asymmetric':
        user_data[user_id] = {'mode': 'asymmetric', 'step': 'flange_diameter'}
        await query.edit_message_text(
            "🔄 *Расчёт для разных сторон*\n\n"
            "Шаг 1 из 7\n\n"
            "Введите *диаметр фланца втулки* (мм):\n"
            "Пример: `44`",
            parse_mode='Markdown'
        )
    
    elif query.data == 'help':
        await query.edit_message_text(
            "📖 *Справка*\n\n"
            "• /start — начать заново\n"
            "• /help — показать справку\n"
            "• /examples — примеры расчётов",
            parse_mode='Markdown'
        )
    
    elif query.data == 'examples':
        await query.edit_message_text(
            "🔧 *Примеры*\n\n"
            "1. Дорожный: фланец 44, обод 577, вылет 38, 36 спиц, 3 креста\n"
            "   → 281 мм\n\n"
            "2. Горный: фланец 50, обод 560, вылет 35, 32 спицы, 3 креста\n"
            "   → 276 мм",
            parse_mode='Markdown'
        )

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_data:
        await update.message.reply_text("Нажми /start, чтобы начать расчёт")
        return
    
    data = user_data[user_id]
    step = data.get('step')
    mode = data.get('mode')
    
    if not step:
        await update.message.reply_text("Нажми /start, чтобы начать расчёт")
        return
    
    try:
        value = float(text)
        
        # Симметричный режим
        if mode == 'symmetric':
            if step == 'flange_diameter':
                data['flange_diameter'] = value
                data['step'] = 'rim_diameter'
                await update.message.reply_text(
                    f"✅ Диаметр фланца: {value} мм\n\n"
                    "Введите *диаметр обода* (мм):\n"
                    "Пример: `577`",
                    parse_mode='Markdown'
                )
            
            elif step == 'rim_diameter':
                data['rim_diameter'] = value
                data['step'] = 'flange_offset'
                await update.message.reply_text(
                    f"✅ Диаметр обода: {value} мм\n\n"
                    "Введите *вылет фланца* (мм):\n"
                    "Пример: `38`",
                    parse_mode='Markdown'
                )
            
            elif step == 'flange_offset':
                data['flange_offset'] = value
                data['step'] = 'spoke_count'
                await update.message.reply_text(
                    f"✅ Вылет фланца: {value} мм\n\n"
                    "Введите *количество спиц*:\n"
                    "Обычно 32 или 36\n"
                    "Пример: `36`",
                    parse_mode='Markdown'
                )
            
            elif step == 'spoke_count':
                data['spoke_count'] = int(value)
                data['step'] = 'crosses'
                await update.message.reply_text(
                    f"✅ Количество спиц: {int(value)}\n\n"
                    "Введите *количество крестов*:\n"
                    "1, 2, 3 или 4\n"
                    "Пример: `3`",
                    parse_mode='Markdown'
                )
            
            elif step == 'crosses':
                if value not in [1, 2, 3, 4]:
                    await update.message.reply_text("⚠️ Введите 1, 2, 3 или 4")
                    return
                data['crosses'] = int(value)
                data['step'] = 'rim_offset'
                await update.message.reply_text(
                    f"✅ Количество крестов: {int(value)}\n\n"
                    "Введите *смещение обода* (мм):\n"
                    "Если обод симметричный, введите 0\n"
                    "Пример: `2` или `0`",
                    parse_mode='Markdown'
                )
            
            elif step == 'rim_offset':
                data['rim_offset'] = value
                
                length = calculate_spoke_length(
                    data['flange_diameter'],
                    data['rim_diameter'],
                    data['flange_offset'],
                    data['spoke_count'],
                    data['crosses'],
                    data['rim_offset']
                )
                recommended = round_spoke_length(length)
                
                result_text = f"""
✅ *Результат расчёта*

📊 *Ваши параметры:*
• Диаметр фланца: {data['flange_diameter']:.1f} мм
• Диаметр обода: {data['rim_diameter']:.1f} мм
• Вылет фланца: {data['flange_offset']:.1f} мм
• Количество спиц: {data['spoke_count']}
• Количество крестов: {data['crosses']}
• Смещение обода: {data['rim_offset']:.1f} мм

📏 *Длина спицы:*
• Расчётная: *{length:.3f}* мм
• Рекомендуемая: *{recommended}* мм
"""
                await update.message.reply_text(result_text, parse_mode='Markdown')
                del user_data[user_id]
                
                # Показать меню
                keyboard = [
                    [InlineKeyboardButton("🔄 Новый расчёт", callback_data='calculate_symmetric')],
                    [InlineKeyboardButton("📖 Справка", callback_data='help')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        
        # Асимметричный режим
        elif mode == 'asymmetric':
            if step == 'flange_diameter':
                data['flange_diameter'] = value
                data['step'] = 'rim_diameter'
                await update.message.reply_text(
                    f"✅ Диаметр фланца: {value} мм\n\n"
                    "Введите *диаметр обода* (мм):",
                    parse_mode='Markdown'
                )
            
            elif step == 'rim_diameter':
                data['rim_diameter'] = value
                data['step'] = 'left_offset'
                await update.message.reply_text(
                    f"✅ Диаметр обода: {value} мм\n\n"
                    "Введите *левый вылет фланца* (мм):\n"
                    "Пример: `32`",
                    parse_mode='Markdown'
                )
            
            elif step == 'left_offset':
                data['left_offset'] = value
                data['step'] = 'right_offset'
                await update.message.reply_text(
                    f"✅ Левый вылет: {value} мм\n\n"
                    "Введите *правый вылет фланца* (мм):\n"
                    "Пример: `45`",
                    parse_mode='Markdown'
                )
            
            elif step == 'right_offset':
                data['right_offset'] = value
                data['step'] = 'spoke_count'
                await update.message.reply_text(
                    f"✅ Правый вылет: {value} мм\n\n"
                    "Введите *количество спиц*:",
                    parse_mode='Markdown'
                )
            
            elif step == 'spoke_count':
                data['spoke_count'] = int(value)
                data['step'] = 'crosses'
                await update.message.reply_text(
                    f"✅ Количество спиц: {int(value)}\n\n"
                    "Введите *количество крестов*:",
                    parse_mode='Markdown'
                )
            
            elif step == 'crosses':
                if value not in [1, 2, 3, 4]:
                    await update.message.reply_text("⚠️ Введите 1, 2, 3 или 4")
                    return
                data['crosses'] = int(value)
                data['step'] = 'rim_offset'
                await update.message.reply_text(
                    f"✅ Количество крестов: {int(value)}\n\n"
                    "Введите *смещение обода* (мм, 0 если симметричный):",
                    parse_mode='Markdown'
                )
            
            elif step == 'rim_offset':
                data['rim_offset'] = value
                
                left_len, right_len, left_rec, right_rec = calculate_both_sides(
                    data['flange_diameter'],
                    data['rim_diameter'],
                    data['left_offset'],
                    data['right_offset'],
                    data['spoke_count'],
                    data['crosses'],
                    data['rim_offset']
                )
                
                result_text = f"""
✅ *Результат расчёта (разные стороны)*

📊 *Ваши параметры:*
• Диаметр фланца: {data['flange_diameter']:.1f} мм
• Диаметр обода: {data['rim_diameter']:.1f} мм
• Левый вылет: {data['left_offset']:.1f} мм
• Правый вылет: {data['right_offset']:.1f} мм
• Спиц: {data['spoke_count']}, Крестов: {data['crosses']}
• Смещение обода: {data['rim_offset']:.1f} мм

📏 *Длина спиц:*
🔵 *Левая сторона:* {left_len:.3f} мм → *{left_rec}* мм
🔴 *Правая сторона:* {right_len:.3f} мм → *{right_rec}* мм

📊 *Разница:* {abs(left_len - right_len):.1f} мм
"""
                await update.message.reply_text(result_text, parse_mode='Markdown')
                del user_data[user_id]
    
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число (например: 44.5)")

def main():
    """Запуск бота"""
    if not TOKEN:
        logger.error("Токен не найден! Установите переменную TELEGRAM_BOT_TOKEN")
        return
    
    # Создаём приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("examples", examples))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем polling (для Railway)
    logger.info("Бот запущен и работает...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
