import sqlite3

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

TOKEN = "8451360741:AAHYSCi1gkWuGYiIvIsbCaFWK8UQXjyNFbM"

# ===== БАЗА ДАННЫХ =====

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    quantity INTEGER
)
""")

conn.commit()

# ===== СОСТОЯНИЯ =====

ADD_NAME, ADD_QUANTITY, REMOVE_PRODUCT = range(3)

# ===== КЛАВИАТУРА =====

main_keyboard = ReplyKeyboardMarkup(
    [
        ["➕ Добавить продукт"],
        ["📦 Список продуктов"],
        ["❌ Удалить продукт"],
    ],
    resize_keyboard=True
)

# ===== СТАРТ =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 Бот учета продуктов\n\nВыбери действие:",
        reply_markup=main_keyboard
    )

# ===== ДОБАВЛЕНИЕ =====

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите название продукта:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["product_name"] = update.message.text

    await update.message.reply_text(
        "Введите количество:"
    )

    return ADD_QUANTITY

async def add_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        quantity = int(update.message.text)
        name = context.user_data["product_name"]

        cursor.execute(
            "INSERT INTO products (name, quantity) VALUES (?, ?)",
            (name, quantity)
        )

        conn.commit()

        await update.message.reply_text(
            f"✅ Добавлено:\n{name} — {quantity}",
            reply_markup=main_keyboard
        )

        return ConversationHandler.END

    except:
        await update.message.reply_text(
            "Введите число."
        )

        return ADD_QUANTITY

# ===== СПИСОК =====

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT name, quantity FROM products")
    products = cursor.fetchall()

    if not products:
        await update.message.reply_text(
            "📭 Список пуст",
            reply_markup=main_keyboard
        )
        return

    text = "📦 Продукты дома:\n\n"

    for product in products:
        text += f"• {product[0]} — {product[1]}\n"

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard
    )

# ===== УДАЛЕНИЕ =====

async def remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT name FROM products")
    products = cursor.fetchall()

    if not products:
        await update.message.reply_text(
            "📭 Список пуст",
            reply_markup=main_keyboard
        )
        return ConversationHandler.END

    buttons = [[p[0]] for p in products]

    keyboard = ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Выберите продукт для удаления:",
        reply_markup=keyboard
    )

    return REMOVE_PRODUCT

async def remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text

    cursor.execute(
        "DELETE FROM products WHERE name = ?",
        (name,)
    )

    conn.commit()

    await update.message.reply_text(
        f"❌ Удалено: {name}",
        reply_markup=main_keyboard
    )

    return ConversationHandler.END

# ===== ОТМЕНА =====

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Действие отменено",
        reply_markup=main_keyboard
    )

    return ConversationHandler.END

# ===== ЗАПУСК =====

app = ApplicationBuilder().token(TOKEN).build()

# Добавление
add_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.TEXT & filters.Regex("^➕ Добавить продукт$"),
            add_start
        )
    ],
    states={
        ADD_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)
        ],
        ADD_QUANTITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_quantity)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ],
)

# Удаление
remove_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.TEXT & filters.Regex("^❌ Удалить продукт$"),
            remove_start
        )
    ],
    states={
        REMOVE_PRODUCT: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                remove_product
            )
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ],
)

app.add_handler(CommandHandler("start", start))

app.add_handler(add_handler)

app.add_handler(
    MessageHandler(
        filters.TEXT & filters.Regex("^📦 Список продуктов$"),
        show_products
    )
)

app.add_handler(remove_handler)

print("Бот запущен...")

app.run_polling()