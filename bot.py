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
    """ТОЧНАЯ формула из вашей Excel-таблицы"""
    term1 = (flange_diameter * flange_diameter) / 4.0
    term2 = (rim_diameter * rim_diameter) / 4.0
    angle_radians = (crosses * 4 * math.pi) / spoke_count
    term3 = (flange_diameter / 2.0) * rim_diameter * math.cos(angle_radians)
    axial_term = (flange_offset - rim_offset / 2.0)
    term4 = axial_term * axial_term
    sum_squared = term1 + term2 - term3 + term4
    return math.sqrt(sum_squared)

def round_spoke_length(length):
    rounded = math.ceil(length * 2) / 2
    return int(rounded) if rounded.is_integer() else rounded

def calculate_both_sides(flange_diameter, rim_diameter, left_offset, right_offset, spoke_count, crosses, rim_offset=0):
    left_length = calculate_spoke_length(flange_diameter, rim_diameter, left_offset, spoke_count, crosses, rim_offset)
    right_length = calculate_spoke_length(flange_diameter, rim_diameter, right_offset, spoke_count, crosses, rim_offset)
    return left_length, right_length, round_spoke_length(left_length), round_spoke_length(right_length)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    """Показывает главное меню с кнопками"""
    keyboard = [
        [InlineKeyboardButton("📏 Симметричный расчёт", callback_data='symmetric')],
        [InlineKeyboardButton("🔄 Разные стороны", callback_data='asymmetric')],
        [InlineKeyboardButton("📖 Справка", callback_data='help')],
        [InlineKeyboardButton("🔧 Пример", callback_data='example')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🚴‍♂️ *Калькулятор длины спицы*\n\n"
            "🔧 *Точный расчёт по формуле из Excel*\n\n"
            "Выбери режим:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🚴‍♂️ *Калькулятор длины спицы*\n\n"
            "🔧 *Точный расчёт по формуле из Excel*\n\n"
            "Выбери режим:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def show_new_calculation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню после завершения расчёта"""
    keyboard = [
        [InlineKeyboardButton("📏 Новый симметричный расчёт", callback_data='symmetric')],
        [InlineKeyboardButton("🔄 Новый расчёт (разные стороны)", callback_data='asymmetric')],
        [InlineKeyboardButton("📖 Справка", callback_data='help')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "✅ *Расчёт завершён!*\n\nЧто делаем дальше?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "✅ *Расчёт завершён!*\n\nЧто делаем дальше?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def cancel_and_restart(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """Отменяет текущий расчёт и показывает главное меню"""
    if user_id in user_data:
        del user_data[user_id]
    
    keyboard = [
        [InlineKeyboardButton("📏 Симметричный расчёт", callback_data='symmetric')],
        [InlineKeyboardButton("🔄 Разные стороны", callback_data='asymmetric')],
        [InlineKeyboardButton("📖 Справка", callback_data='help')],
        [InlineKeyboardButton("🔧 Пример", callback_data='example')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🔄 *Расчёт отменён*\n\nВыбери новый режим:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🔄 *Расчёт отменён*\n\nВыбери новый режим:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await show_main_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подробную справку с кнопкой возврата"""
    help_text = """📖 *Справка по калькулятору длины спицы*

*Формула расчёта:*
`SQRT((A²/4) + (B²/4) - (A/2)×B×COS(4π×кресты/спицы) + (C-F/2)²)`

*Параметры:*
1. **A** — Диаметр фланца втулки (мм)
   → Расстояние между центрами противоположных отверстий

2. **B** — Диаметр обода (мм)
   → Внутренний диаметр (место посадки ниппеля)

3. **C** — Вылет фланца (мм)
   → От центра втулки до фланца по оси

4. **D** — Количество спиц
   → Обычно 32 или 36

5. **E** — Количество крестов
   → 1, 2, 3 или 4 (как спицы перекрещиваются)

6. **F** — Смещение обода (мм)
   → 0 для симметричного обода

*Пример расчёта:* 
A=44, B=577, C=38, D=36, E=3, F=2
→ Результат: *281* мм

✅ *Точность:* совпадает с исходной таблицей до 6 знаков"""

    keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def example_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает пример расчёта с кнопкой возврата"""
    length = calculate_spoke_length(44, 577, 38, 36, 3, 2)
    rec = round_spoke_length(length)
    
    example_text = f"""🔧 *Пример расчёта*

📊 *Входные параметры:*
• Диаметр фланца: 44 мм
• Диаметр обода: 577 мм
• Вылет фланца: 38 мм
• Количество спиц: 36
• Количество крестов: 3
• Смещение обода: 2 мм

📏 *Результат:*
• Расчётная длина: `{length:.6f}` мм
• Рекомендуемые спицы: *{rec}* мм

✅ *Проверка:* 280.6033677631115 (таблица)
✅ *Погрешность:* {length - 280.6033677631115:.10f} мм

💡 *Совет:* Всегда округляйте длину вверх до 0.5 или целого мм"""

    keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            example_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            example_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # Обработка кнопки "Главное меню"
    if query.data == 'main_menu':
        if user_id in user_data:
            del user_data[user_id]
        await show_main_menu(update, context)
        return
    
    # Обработка кнопки "Справка"
    if query.data == 'help':
        await help_command(update, context)
        return
    
    # Обработка кнопки "Пример"
    if query.data == 'example':
        await example_command(update, context)
        return
    
    # Начало нового расчёта (очищаем старые данные)
    if query.data in ['symmetric', 'asymmetric']:
        if user_id in user_data:
            del user_data[user_id]
    
    # Симметричный расчёт
    if query.data == 'symmetric':
        user_data[user_id] = {'mode': 'symmetric', 'step': 'flange_diameter'}
        await query.edit_message_text(
            "📏 *Симметричный расчёт*\n\n"
            "Шаг 1 из 6\n\n"
            "Введите *диаметр фланца втулки* (мм):\n"
            "Пример: `44`\n\n"
            "💡 *Хочешь начать заново?* Напиши /start",
            parse_mode='Markdown'
        )
    
    # Асимметричный расчёт
    elif query.data == 'asymmetric':
        user_data[user_id] = {'mode': 'asymmetric', 'step': 'flange_diameter'}
        await query.edit_message_text(
            "🔄 *Расчёт для разных сторон*\n\n"
            "Шаг 1 из 7\n\n"
            "Введите *диаметр фланца втулки* (мм):\n"
            "Пример: `44`\n\n"
            "💡 *Хочешь начать заново?* Напиши /start",
            parse_mode='Markdown'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Команда /start обрабатывается отдельно
    if text == '/start':
        await start(update, context)
        return
    
    # Команда /help
    if text == '/help':
        await help_command(update, context)
        return
    
    # Если нет активного расчёта
    if user_id not in user_data:
        await update.message.reply_text(
            "❌ Нет активного расчёта.\n\n"
            "Нажми /start, чтобы начать новый расчёт"
        )
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
                await update.message.reply_text(
                    f"✅ Диаметр фланца: {value:.1f} мм\n\n"
                    "Введите *диаметр обода* (мм):\n"
                    "Пример: `577`\n\n"
                    "🔄 *Чтобы начать заново* — напиши /start\n"
                    "📖 *Для справки* — напиши /help",
                    parse_mode='Markdown'
                )
            elif step == 'rim_diameter':
                data['rim_diameter'] = value
                data['step'] = 'flange_offset'
                await update.message.reply_text(
                    f"✅ Диаметр обода: {value:.1f} мм\n\n"
                    "Введите *вылет фланца* (мм):\n"
                    "Пример: `38`\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
                    parse_mode='Markdown'
                )
            elif step == 'flange_offset':
                data['flange_offset'] = value
                data['step'] = 'spoke_count'
                await update.message.reply_text(
                    f"✅ Вылет фланца: {value:.1f} мм\n\n"
                    "Введите *количество спиц*:\n"
                    "Обычно 32 или 36\n"
                    "Пример: `36`\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
                    parse_mode='Markdown'
                )
            elif step == 'spoke_count':
                if value not in [28, 32, 36, 40, 48]:
                    await update.message.reply_text(
                        "⚠️ Обычно используют 28, 32, 36, 40 или 48 спиц.\n"
                        "Введите количество спиц заново:\n\n"
                        "🔄 /start — начать заново"
                    )
                    return
                data['spoke_count'] = int(value)
                data['step'] = 'crosses'
                await update.message.reply_text(
                    f"✅ Количество спиц: {int(value)}\n\n"
                    "Введите *количество крестов*:\n"
                    "1, 2, 3 или 4\n"
                    "Пример: `3`\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
                    parse_mode='Markdown'
                )
            elif step == 'crosses':
                if value not in [1, 2, 3, 4]:
                    await update.message.reply_text(
                        "⚠️ Количество крестов может быть 1, 2, 3 или 4.\n"
                        "Введите заново:\n\n"
                        "🔄 /start — начать заново"
                    )
                    return
                data['crosses'] = int(value)
                data['step'] = 'rim_offset'
                await update.message.reply_text(
                    f"✅ Количество крестов: {int(value)}\n\n"
                    "Введите *смещение обода* (мм):\n"
                    "0 если обод симметричный\n"
                    "Пример: `2` или `0`\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
                    parse_mode='Markdown'
                )
            elif step == 'rim_offset':
                data['rim_offset'] = value
                
                # Расчёт
                length = calculate_spoke_length(
                    data['flange_diameter'],
                    data['rim_diameter'],
                    data['flange_offset'],
                    data['spoke_count'],
                    data['crosses'],
                    data['rim_offset']
                )
                recommended = round_spoke_length(length)
                
                result_text = f"""✅ *Результат расчёта*

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
                
                # Проверка для тестовых данных
                if (data['flange_diameter'] == 44 and data['rim_diameter'] == 577 and 
                    data['flange_offset'] == 38 and data['spoke_count'] == 36 and 
                    data['crosses'] == 3 and data['rim_offset'] == 2):
                    table_value = 280.6033677631115
                    result_text += f"\n\n✅ *Совпадает с таблицей:* {table_value:.3f} мм"
                
                await update.message.reply_text(result_text, parse_mode='Markdown')
                
                # Очищаем данные пользователя
                del user_data[user_id]
                
                # Показываем меню для нового расчёта
                await show_new_calculation_menu(update, context)
        
        # АСИММЕТРИЧНЫЙ РЕЖИМ
        elif mode == 'asymmetric':
            if step == 'flange_diameter':
                data['flange_diameter'] = value
                data['step'] = 'rim_diameter'
                await update.message.reply_text(
                    f"✅ Диаметр фланца: {value:.1f} мм\n\n"
                    "Введите *диаметр обода* (мм):\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
                    parse_mode='Markdown'
                )
            elif step == 'rim_diameter':
                data['rim_diameter'] = value
                data['step'] = 'left_offset'
                await update.message.reply_text(
                    f"✅ Диаметр обода: {value:.1f} мм\n\n"
                    "Введите *левый вылет фланца* (мм):\n"
                    "Пример: `32`\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
                    parse_mode='Markdown'
                )
            elif step == 'left_offset':
                data['left_offset'] = value
                data['step'] = 'right_offset'
                await update.message.reply_text(
                    f"✅ Левый вылет: {value:.1f} мм\n\n"
                    "Введите *правый вылет фланца* (мм):\n"
                    "Пример: `45`\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
                    parse_mode='Markdown'
                )
            elif step == 'right_offset':
                data['right_offset'] = value
                data['step'] = 'spoke_count'
                await update.message.reply_text(
                    f"✅ Правый вылет: {value:.1f} мм\n\n"
                    "Введите *количество спиц*:\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
                    parse_mode='Markdown'
                )
            elif step == 'spoke_count':
                data['spoke_count'] = int(value)
                data['step'] = 'crosses'
                await update.message.reply_text(
                    f"✅ Количество спиц: {int(value)}\n\n"
                    "Введите *количество крестов*:\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
                    parse_mode='Markdown'
                )
            elif step == 'crosses':
                if value not in [1, 2, 3, 4]:
                    await update.message.reply_text(
                        "⚠️ Введите 1, 2, 3 или 4\n\n"
                        "🔄 /start — начать заново"
                    )
                    return
                data['crosses'] = int(value)
                data['step'] = 'rim_offset'
                await update.message.reply_text(
                    f"✅ Количество крестов: {int(value)}\n\n"
                    "Введите *смещение обода* (мм):\n"
                    "0 если симметричный\n\n"
                    "🔄 /start — начать заново\n"
                    "📖 /help — справка",
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
                
                result_text = f"""✅ *Результат расчёта (разные стороны)*

📊 *Ваши параметры:*
• Диаметр фланца: {data['flange_diameter']:.1f} мм
• Диаметр обода: {data['rim_diameter']:.1f} мм
• Левый вылет: {data['left_offset']:.1f} мм
• Правый вылет: {data['right_offset']:.1f} мм
• Спиц: {data['spoke_count']}, Крестов: {data['crosses']}
• Смещение: {data['rim_offset']:.1f} мм

📏 *Длина спиц:*
🔵 *Левая сторона:* {left_len:.3f} мм → *{left_rec}* мм
🔴 *Правая сторона:* {right_len:.3f} мм → *{right_rec}* мм

📊 *Разница:* {abs(left_len - right_len):.1f} мм
"""
                await update.message.reply_text(result_text, parse_mode='Markdown')
                del user_data[user_id]
                await show_new_calculation_menu(update, context)
    
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число (например: 44.5)\n\n"
            "🔄 /start — начать заново\n"
            "📖 /help — справка"
        )

def main():
    if not TOKEN:
        logger.error("Токен не найден! Установите переменную TELEGRAM_BOT_TOKEN")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Бот запущен с улучшенным меню!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
