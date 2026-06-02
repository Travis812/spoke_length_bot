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
    """
    ТОЧНАЯ формула из вашей Excel-таблицы:
    SQRT((A2^2)/4 + (B2^2)/4 - (A2/2)*B2*COS((E2*4*PI())/D2) + (C2-F2/2)^2)
    """
    # (A2^2)/4
    term1 = (flange_diameter * flange_diameter) / 4.0
    
    # (B2^2)/4
    term2 = (rim_diameter * rim_diameter) / 4.0
    
    # (A2/2)*B2*COS((E2*4*PI())/D2)
    # Угол: (кресты * 4 * π) / спицы = (кресты * 720°) / спицы
    angle_radians = (crosses * 4 * math.pi) / spoke_count
    term3 = (flange_diameter / 2.0) * rim_diameter * math.cos(angle_radians)
    
    # (C2 - F2/2)^2  → ВАЖНО: МИНУС, а не плюс!
    axial_term = (flange_offset - rim_offset / 2.0)
    term4 = axial_term * axial_term
    
    # Полная сумма под корнем
    sum_squared = term1 + term2 - term3 + term4
    
    # Извлекаем квадратный корень
    spoke_length = math.sqrt(sum_squared)
    
    return spoke_length

def round_spoke_length(length):
    """Округление до 0.5 мм вверх"""
    rounded = math.ceil(length * 2) / 2
    return int(rounded) if rounded.is_integer() else rounded

def calculate_both_sides(flange_diameter, rim_diameter, left_offset, right_offset, spoke_count, crosses, rim_offset=0):
    """Расчёт для левой и правой стороны"""
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
        "🚴‍♂️ *Калькулятор длины спицы*\n\n"
        "🔧 *Точный расчёт по формуле из Excel*\n\n"
        "Выбери режим:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 *Справка*

*Формула расчёта:*
`SQRT((A²/4) + (B²/4) - (A/2)×B×COS(4π×кресты/спицы) + (C-F/2)²)`

*Параметры:*
1. **A** — Диаметр фланца (мм)
2. **B** — Диаметр обода (мм)
3. **C** — Вылет фланца (мм)
4. **D** — Количество спиц (32 или 36)
5. **E** — Количество крестов (1-4)
6. **F** — Смещение обода (мм)

*Пример:* A=44, B=577, C=38, D=36, E=3, F=2
→ Результат: *281* мм

✅ *Точность:* совпадает с исходной таблицей до 6 знаков"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def example_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    length = calculate_spoke_length(44, 577, 38, 36, 3, 2)
    rec = round_spoke_length(length)
    await update.message.reply_text(
        f"🔧 *Пример расчёта*\n\n"
        f"📊 *Параметры:*\n"
        f"• Фланец: 44 мм\n"
        f"• Обод: 577 мм\n"
        f"• Вылет: 38 мм\n"
        f"• Спицы: 36\n"
        f"• Кресты: 3\n"
        f"• Смещение: 2 мм\n\n"
        f"📏 *Результат:*\n"
        f"• Расчётная: `{length:.6f}` мм\n"
        f"• Рекомендуемые: *{rec}* мм\n\n"
        f"✅ *Проверка:* 280.6033677631115 (таблица)\n"
        f"✅ *Погрешность:* {length - 280.6033677631115:.10f} мм",
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if query.data == 'symmetric':
        user_data[user_id] = {'mode': 'symmetric', 'step': 'flange_diameter'}
        await query.edit_message_text(
            "📏 *Симметричный расчёт*\n\n"
            "Шаг 1 из 6\n\n"
            "Введите *диаметр фланца втулки* (мм):\n"
            "Пример: `44`",
            parse_mode='Markdown'
        )
    elif query.data == 'asymmetric':
        user_data[user_id] = {'mode': 'asymmetric', 'step': 'flange_diameter'}
        await query.edit_message_text(
            "🔄 *Расчёт для разных сторон*\n\n"
            "Шаг 1 из 7\n\n"
            "Введите *диаметр фланца втулки* (мм):\n"
            "Пример: `44`",
            parse_mode='Markdown'
        )
    elif query.data == 'help':
        await query.edit_message_text("📖 Отправь /help для справки", parse_mode='Markdown')
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
                await update.message.reply_text(
                    f"✅ Диаметр фланца: {value:.1f} мм\n\n"
                    "Введите *диаметр обода* (мм):\n"
                    "Пример: `577`",
                    parse_mode='Markdown'
                )
            elif step == 'rim_diameter':
                data['rim_diameter'] = value
                data['step'] = 'flange_offset'
                await update.message.reply_text(
                    f"✅ Диаметр обода: {value:.1f} мм\n\n"
                    "Введите *вылет фланца* (мм):\n"
                    "Пример: `38`",
                    parse_mode='Markdown'
                )
            elif step == 'flange_offset':
                data['flange_offset'] = value
                data['step'] = 'spoke_count'
                await update.message.reply_text(
                    f"✅ Вылет фланца: {value:.1f} мм\n\n"
                    "Введите *количество спиц*:\n"
                    "Обычно 32 или 36\n"
                    "Пример: `36`",
                    parse_mode='Markdown'
                )
            elif step == 'spoke_count':
                if value not in [32, 36, 28, 40, 48]:
                    await update.message.reply_text("⚠️ Введите 28, 32, 36, 40 или 48")
                    return
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
                    "0 если обод симметричный\n"
                    "Пример: `2` или `0`",
                    parse_mode='Markdown'
                )
            elif step == 'rim_offset':
                data['rim_offset'] = value
                
                # ТОЧНЫЙ РАСЧЁТ ПО ФОРМУЛЕ ИЗ EXCEL
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
                
                # Для тестовых данных показываем сверку с таблицей
                if (data['flange_diameter'] == 44 and data['rim_diameter'] == 577 and 
                    data['flange_offset'] == 38 and data['spoke_count'] == 36 and 
                    data['crosses'] == 3 and data['rim_offset'] == 2):
                    table_value = 280.6033677631115
                    diff = length - table_value
                    result_text += f"\n\n📊 *Сверка с таблицей:*\n• Таблица: {table_value:.6f} мм\n• Разница: {diff:.10f} мм"
                    if abs(diff) < 0.0001:
                        result_text += "\n✅ *Идеальное совпадение!*"
                
                await update.message.reply_text(result_text, parse_mode='Markdown')
                del user_data[user_id]
        
        # АСИММЕТРИЧНЫЙ РЕЖИМ
        elif mode == 'asymmetric':
            if step == 'flange_diameter':
                data['flange_diameter'] = value
                data['step'] = 'rim_diameter'
                await update.message.reply_text(
                    f"✅ Диаметр фланца: {value:.1f} мм\n\n"
                    "Введите *диаметр обода* (мм):",
                    parse_mode='Markdown'
                )
            elif step == 'rim_diameter':
                data['rim_diameter'] = value
                data['step'] = 'left_offset'
                await update.message.reply_text(
                    f"✅ Диаметр обода: {value:.1f} мм\n\n"
                    "Введите *левый вылет фланца* (мм):\n"
                    "Пример: `32`",
                    parse_mode='Markdown'
                )
            elif step == 'left_offset':
                data['left_offset'] = value
                data['step'] = 'right_offset'
                await update.message.reply_text(
                    f"✅ Левый вылет: {value:.1f} мм\n\n"
                    "Введите *правый вылет фланца* (мм):\n"
                    "Пример: `45`",
                    parse_mode='Markdown'
                )
            elif step == 'right_offset':
                data['right_offset'] = value
                data['step'] = 'spoke_count'
                await update.message.reply_text(
                    f"✅ Правый вылет: {value:.1f} мм\n\n"
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
                    "Введите *смещение обода* (мм):\n"
                    "0 если симметричный",
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
    
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число (например: 44.5)")

def main():
    if not TOKEN:
        logger.error("Токен не найден! Установите переменную TELEGRAM_BOT_TOKEN")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Бот запущен с ТОЧНОЙ формулой из Excel!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
