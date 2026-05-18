import os
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

# =========================================
# TOKEN
# =========================================

TOKEN = os.getenv("TOKEN")

# =========================================
# DATABASE
# =========================================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL
)
""")

conn.commit()

# =========================================
# STATES
# =========================================

ADD_NAME, ADD_QUANTITY, REMOVE_PRODUCT, REMOVE_QUANTITY = range(4)

# =========================================
# MAIN KEYBOARD
# =========================================

main_keyboard = ReplyKeyboardMarkup(
    [
        ["➕ Добавить продукт"],
        ["📦 Список продуктов"],
        ["❌ Удалить продукт"],
    ],
    resize_keyboard=True
)

# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 Бот учета продуктов\n\nВыберите действие:",
        reply_markup=main_keyboard
    )

# =========================================
# ADD PRODUCT
# =========================================

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите название продукта:",
        reply_markup=ReplyKeyboardRemove()
    )

    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()

    context.user_data["product_name"] = name

    await update.message.reply_text(
        "Введите количество:"
    )

    return ADD_QUANTITY

async def add_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        quantity = int(update.message.text)

        if quantity <= 0:
            await update.message.reply_text(
                "Введите число больше 0."
            )

            return ADD_QUANTITY

        name = context.user_data["product_name"]

        # Проверяем, есть ли уже продукт
        cursor.execute(
            "SELECT id, quantity FROM products WHERE name = ?",
            (name,)
        )

        result = cursor.fetchone()

        # Если есть — увеличиваем количество
        if result:
            product_id, current_quantity = result

            new_quantity = current_quantity + quantity

            cursor.execute(
                "UPDATE products SET quantity = ? WHERE id = ?",
                (new_quantity, product_id)
            )

        # Если нет — создаем новый
        else:
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

# =========================================
# SHOW PRODUCTS
# =========================================

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute(
        "SELECT name, quantity FROM products ORDER BY name"
    )

    products = cursor.fetchall()

    if not products:
        await update.message.reply_text(
            "📭 Список пуст",
            reply_markup=main_keyboard
        )

        return

    text = "📦 Продукты дома:\n\n"

    for name, quantity in products:
        text += f"• {name} — {quantity}\n"

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard
    )

# =========================================
# REMOVE START
# =========================================

async def remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute(
        "SELECT id, name, quantity FROM products ORDER BY name"
    )

    products = cursor.fetchall()

    if not products:
        await update.message.reply_text(
            "📭 Список пуст",
            reply_markup=main_keyboard
        )

        return ConversationHandler.END

    buttons = []
    product_map = {}

    for product_id, name, quantity in products:
        button_text = f"{name} ({quantity})"

        buttons.append([button_text])

        product_map[button_text] = product_id

    context.user_data["product_map"] = product_map

    keyboard = ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Выберите продукт:",
        reply_markup=keyboard
    )

    return REMOVE_PRODUCT

# =========================================
# REMOVE PRODUCT SELECT
# =========================================

async def remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button_text = update.message.text

    product_map = context.user_data.get("product_map", {})

    product_id = product_map.get(button_text)

    if not product_id:
        await update.message.reply_text(
            "❌ Продукт не найден",
            reply_markup=main_keyboard
        )

        return ConversationHandler.END

    context.user_data["remove_product_id"] = product_id

    cursor.execute(
        "SELECT name FROM products WHERE id = ?",
        (product_id,)
    )

    result = cursor.fetchone()

    if not result:
        await update.message.reply_text(
            "❌ Продукт не найден",
            reply_markup=main_keyboard
        )

        return ConversationHandler.END

    name = result[0]

    await update.message.reply_text(
        f"Сколько удалить у продукта:\n{name}?",
        reply_markup=ReplyKeyboardRemove()
    )

    return REMOVE_QUANTITY

# =========================================
# REMOVE QUANTITY
# =========================================

async def remove_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        remove_count = int(update.message.text)

        if remove_count <= 0:
            await update.message.reply_text(
                "Введите число больше 0."
            )

            return REMOVE_QUANTITY

        product_id = context.user_data["remove_product_id"]

        cursor.execute(
            "SELECT name, quantity FROM products WHERE id = ?",
            (product_id,)
        )

        result = cursor.fetchone()

        if not result:
            await update.message.reply_text(
                "❌ Продукт не найден",
                reply_markup=main_keyboard
            )

            return ConversationHandler.END

        name, current_quantity = result

        # Проверка
        if remove_count > current_quantity:
            await update.message.reply_text(
                f"❌ У тебя только {current_quantity} шт.",
                reply_markup=main_keyboard
            )

            return ConversationHandler.END

        new_quantity = current_quantity - remove_count

        # Если стало 0 — удалить запись
        if new_quantity == 0:
            cursor.execute(
                "DELETE FROM products WHERE id = ?",
                (product_id,)
            )

            conn.commit()

            await update.message.reply_text(
                f"❌ {name} полностью удалён",
                reply_markup=main_keyboard
            )

        # Иначе обновляем количество
        else:
            cursor.execute(
                "UPDATE products SET quantity = ? WHERE id = ?",
                (new_quantity, product_id)
            )

            conn.commit()

            await update.message.reply_text(
                f"✅ Теперь {name}: {new_quantity}",
                reply_markup=main_keyboard
            )

        return ConversationHandler.END

    except:
        await update.message.reply_text(
            "Введите число."
        )

        return REMOVE_QUANTITY

# =========================================
# CANCEL
# =========================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Действие отменено",
        reply_markup=main_keyboard
    )

    return ConversationHandler.END

# =========================================
# APP
# =========================================

app = ApplicationBuilder().token(TOKEN).build()

# =========================================
# ADD HANDLER
# =========================================

add_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.TEXT & filters.Regex("^➕ Добавить продукт$"),
            add_start
        )
    ],

    states={
        ADD_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                add_name
            )
        ],

        ADD_QUANTITY: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                add_quantity
            )
        ],
    },

    fallbacks=[
        CommandHandler("cancel", cancel)
    ],
)

# =========================================
# REMOVE HANDLER
# =========================================

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
        ],

        REMOVE_QUANTITY: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                remove_quantity
            )
        ]
    },

    fallbacks=[
        CommandHandler("cancel", cancel)
    ],
)

# =========================================
# REGISTER HANDLERS
# =========================================

app.add_handler(CommandHandler("start", start))

app.add_handler(add_handler)

app.add_handler(
    MessageHandler(
        filters.TEXT & filters.Regex("^📦 Список продуктов$"),
        show_products
    )
)

app.add_handler(remove_handler)

# =========================================
# START BOT
# =========================================

print("Бот запущен...")

app.run_polling()