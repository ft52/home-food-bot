import os
import sqlite3
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# =========================================
# TOKEN
# =========================================

TOKEN = os.getenv("TOKEN")

# =========================================
# DATABASE
# =========================================

conn = sqlite3.connect(
    "database.db",
    check_same_thread=False
)

cursor = conn.cursor()

# PRODUCTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    category TEXT,
    min_quantity INTEGER DEFAULT 1
)
""")

# FAMILY SHOPPING
cursor.execute("""
CREATE TABLE IF NOT EXISTS family_shopping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    added_by TEXT NOT NULL,
    created_at TEXT
)
""")

# HISTORY
cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT,
    created_at TEXT
)
""")

conn.commit()

# =========================================
# STATES
# =========================================

(
    ADD_NAME,
    ADD_QUANTITY,
    ADD_CATEGORY,
    ADD_MIN_QUANTITY,

    REMOVE_SELECT,
    REMOVE_QUANTITY,

    FAMILY_PRODUCT,
    FAMILY_USER,

) = range(8)

# =========================================
# MAIN MENU
# =========================================

def get_main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "➕ Добавить продукт",
                callback_data="add_product"
            )
        ],

        [
            InlineKeyboardButton(
                "📦 Список продуктов",
                callback_data="show_products"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ Удалить продукт",
                callback_data="remove_product"
            )
        ],

        [
            InlineKeyboardButton(
                "📝 Добавить в покупки",
                callback_data="family_add"
            )
        ],

        [
            InlineKeyboardButton(
                "🛒 Общий список покупок",
                callback_data="family_show"
            )
        ],

        [
            InlineKeyboardButton(
                "🗑 Удалить из покупок",
                callback_data="family_remove"
            )
        ],

        [
            InlineKeyboardButton(
                "📜 История",
                callback_data="history"
            )
        ],

        [
            InlineKeyboardButton(
                "⚠️ Проверить уведомления",
                callback_data="warnings"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)

# =========================================
# HISTORY
# =========================================

def add_history(action):

    cursor.execute("""
    INSERT INTO history
    (action, created_at)
    VALUES (?, ?)
    """,
    (
        action,
        datetime.now().strftime("%d.%m.%Y %H:%M")
    ))

    conn.commit()

# =========================================
# START
# =========================================

async def start(update: Update, context):

    await update.message.reply_text(
        "🏠 Семейный бот учета продуктов",
        reply_markup=get_main_menu()
    )

# =========================================
# ADD PRODUCT
# =========================================

async def add_start(update: Update, context):

    query = update.callback_query

    await query.answer()

    await query.message.reply_text(
        "Введите название продукта:"
    )

    return ADD_NAME

async def add_name(update: Update, context):

    context.user_data["name"] = (
        update.message.text.strip()
    )

    await update.message.reply_text(
        "Введите количество:"
    )

    return ADD_QUANTITY

async def add_quantity(update: Update, context):

    try:

        quantity = int(update.message.text)

        if quantity <= 0:
            raise ValueError

        context.user_data["quantity"] = quantity

        await update.message.reply_text(
            "Введите категорию:"
        )

        return ADD_CATEGORY

    except:

        await update.message.reply_text(
            "Введите число."
        )

        return ADD_QUANTITY

async def add_category(update: Update, context):

    context.user_data["category"] = (
        update.message.text.strip()
    )

    await update.message.reply_text(
        "Введите минимальный остаток:"
    )

    return ADD_MIN_QUANTITY

async def add_min_quantity(update: Update, context):

    try:

        min_quantity = int(update.message.text)

        name = context.user_data["name"]
        quantity = context.user_data["quantity"]
        category = context.user_data["category"]

        cursor.execute("""
        SELECT id, quantity
        FROM products
        WHERE name = ?
        """, (name,))

        result = cursor.fetchone()

        if result:

            product_id, current_quantity = result

            new_quantity = current_quantity + quantity

            cursor.execute("""
            UPDATE products
            SET quantity = ?,
                category = ?,
                min_quantity = ?
            WHERE id = ?
            """,
            (
                new_quantity,
                category,
                min_quantity,
                product_id
            ))

        else:

            cursor.execute("""
            INSERT INTO products
            (
                name,
                quantity,
                category,
                min_quantity
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                quantity,
                category,
                min_quantity
            ))

        conn.commit()

        add_history(
            f"➕ Добавлено: {name} x{quantity}"
        )

        await update.message.reply_text(
            f"✅ Добавлено:\n{name} — {quantity}",
            reply_markup=get_main_menu()
        )

        return ConversationHandler.END

    except:

        await update.message.reply_text(
            "Введите число."
        )

        return ADD_MIN_QUANTITY

# =========================================
# SHOW PRODUCTS
# =========================================

async def show_products(update: Update, context):

    query = update.callback_query

    await query.answer()

    cursor.execute("""
    SELECT
        name,
        quantity,
        category
    FROM products
    ORDER BY category, name
    """)

    products = cursor.fetchall()

    if not products:

        await query.message.reply_text(
            "📭 Список пуст",
            reply_markup=get_main_menu()
        )

        return

    text = "📦 Продукты:\n\n"

    current_category = None

    for name, quantity, category in products:

        if current_category != category:

            current_category = category

            text += f"\n{category}\n"

        text += f"• {name} — {quantity}\n"

    await query.message.reply_text(
        text,
        reply_markup=get_main_menu()
    )

# =========================================
# REMOVE PRODUCT START
# =========================================

async def remove_start(update: Update, context):

    query = update.callback_query

    await query.answer()

    cursor.execute("""
    SELECT id, name, quantity
    FROM products
    ORDER BY name
    """)

    products = cursor.fetchall()

    if not products:

        await query.message.reply_text(
            "📭 Список пуст",
            reply_markup=get_main_menu()
        )

        return ConversationHandler.END

    keyboard = []

    for product_id, name, quantity in products:

        keyboard.append([
            InlineKeyboardButton(
                f"{name} ({quantity})",
                callback_data=f"delete_{product_id}"
            )
        ])

    await query.message.reply_text(
        "Выберите продукт:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return REMOVE_SELECT

# =========================================
# SELECT REMOVE PRODUCT
# =========================================

async def select_remove_product(update: Update, context):

    query = update.callback_query

    await query.answer()

    product_id = int(
        query.data.replace("delete_", "")
    )

    context.user_data["remove_product_id"] = product_id

    cursor.execute("""
    SELECT name
    FROM products
    WHERE id = ?
    """, (product_id,))

    result = cursor.fetchone()

    if not result:

        await query.message.reply_text(
            "❌ Продукт не найден",
            reply_markup=get_main_menu()
        )

        return ConversationHandler.END

    name = result[0]

    await query.message.reply_text(
        f"Сколько удалить у продукта:\n{name}?"
    )

    return REMOVE_QUANTITY

# =========================================
# REMOVE QUANTITY
# =========================================

async def remove_quantity(update: Update, context):

    try:

        remove_count = int(update.message.text)

        if remove_count <= 0:
            raise ValueError

        product_id = context.user_data[
            "remove_product_id"
        ]

        cursor.execute("""
        SELECT
            name,
            quantity,
            min_quantity
        FROM products
        WHERE id = ?
        """, (product_id,))

        result = cursor.fetchone()

        if not result:

            await update.message.reply_text(
                "❌ Продукт не найден",
                reply_markup=get_main_menu()
            )

            return ConversationHandler.END

        name, quantity, min_quantity = result

        if remove_count > quantity:

            await update.message.reply_text(
                f"❌ У тебя только {quantity} шт.",
                reply_markup=get_main_menu()
            )

            return ConversationHandler.END

        new_quantity = quantity - remove_count

        if new_quantity == 0:

            cursor.execute("""
            DELETE FROM products
            WHERE id = ?
            """, (product_id,))

            message = f"❌ {name} полностью удалён"

        else:

            cursor.execute("""
            UPDATE products
            SET quantity = ?
            WHERE id = ?
            """,
            (
                new_quantity,
                product_id
            ))

            message = (
                f"✅ Теперь {name}: "
                f"{new_quantity}"
            )

        conn.commit()

        add_history(
            f"➖ Удалено: {name} x{remove_count}"
        )

        if (
            new_quantity <= min_quantity
            and new_quantity > 0
        ):

            message += (
                f"\n\n⚠️ Заканчивается"
            )

        await update.message.reply_text(
            message,
            reply_markup=get_main_menu()
        )

        return ConversationHandler.END

    except:

        await update.message.reply_text(
            "Введите число."
        )

        return REMOVE_QUANTITY

# =========================================
# FAMILY SHOPPING START
# =========================================

async def family_shopping_start(update: Update, context):

    query = update.callback_query

    await query.answer()

    await query.message.reply_text(
        "Что нужно купить?"
    )

    return FAMILY_PRODUCT

# =========================================
# FAMILY PRODUCT
# =========================================

async def family_product(update: Update, context):

    context.user_data["family_product"] = (
        update.message.text.strip()
    )

    await update.message.reply_text(
        "Кто добавляет?"
    )

    return FAMILY_USER

# =========================================
# FAMILY USER
# =========================================

async def family_user(update: Update, context):

    user_name = update.message.text.strip()

    product_name = context.user_data[
        "family_product"
    ]

    cursor.execute("""
    INSERT INTO family_shopping
    (
        product_name,
        added_by,
        created_at
    )
    VALUES (?, ?, ?)
    """,
    (
        product_name,
        user_name,
        datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        )
    ))

    conn.commit()

    add_history(
        f"🛒 В покупки добавлено: "
        f"{product_name} ({user_name})"
    )

    await update.message.reply_text(
        f"✅ Добавлено:\n{product_name}",
        reply_markup=get_main_menu()
    )

    return ConversationHandler.END

# =========================================
# SHOW FAMILY SHOPPING
# =========================================

async def show_family_shopping(update: Update, context):

    query = update.callback_query

    await query.answer()

    cursor.execute("""
    SELECT
        product_name,
        added_by,
        created_at
    FROM family_shopping
    ORDER BY id DESC
    """)

    items = cursor.fetchall()

    if not items:

        await query.message.reply_text(
            "🛒 Список покупок пуст",
            reply_markup=get_main_menu()
        )

        return

    text = "🛒 Общий список покупок:\n\n"

    for product_name, added_by, created_at in items:

        text += (
            f"• {product_name}\n"
            f"👤 {added_by}\n"
            f"🕒 {created_at}\n\n"
        )

    await query.message.reply_text(
        text,
        reply_markup=get_main_menu()
    )

# =========================================
# REMOVE FAMILY SHOPPING
# =========================================

async def remove_family_start(update: Update, context):

    query = update.callback_query

    await query.answer()

    cursor.execute("""
    SELECT
        id,
        product_name,
        added_by
    FROM family_shopping
    ORDER BY id DESC
    """)

    items = cursor.fetchall()

    if not items:

        await query.message.reply_text(
            "🛒 Список покупок пуст",
            reply_markup=get_main_menu()
        )

        return

    keyboard = []

    for item_id, product_name, added_by in items:

        keyboard.append([
            InlineKeyboardButton(
                f"{product_name} ({added_by})",
                callback_data=f"remove_family_{item_id}"
            )
        ])

    await query.message.reply_text(
        "Что удалить из списка покупок?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def remove_family_item(update: Update, context):

    query = update.callback_query

    await query.answer()

    item_id = int(
        query.data.replace(
            "remove_family_",
            ""
        )
    )

    cursor.execute("""
    SELECT
        product_name,
        added_by
    FROM family_shopping
    WHERE id = ?
    """, (item_id,))

    result = cursor.fetchone()

    if not result:

        await query.message.reply_text(
            "❌ Элемент не найден",
            reply_markup=get_main_menu()
        )

        return

    product_name, added_by = result

    cursor.execute("""
    DELETE FROM family_shopping
    WHERE id = ?
    """, (item_id,))

    conn.commit()

    add_history(
        f"🗑 Удалено из покупок: "
        f"{product_name} ({added_by})"
    )

    await query.message.reply_text(
        f"✅ Удалено:\n{product_name}",
        reply_markup=get_main_menu()
    )

# =========================================
# HISTORY
# =========================================

async def show_history(update: Update, context):

    query = update.callback_query

    await query.answer()

    cursor.execute("""
    SELECT action, created_at
    FROM history
    ORDER BY id DESC
    LIMIT 20
    """)

    items = cursor.fetchall()

    if not items:

        await query.message.reply_text(
            "📜 История пуста",
            reply_markup=get_main_menu()
        )

        return

    text = "📜 Последние действия:\n\n"

    for action, created_at in items:

        text += f"{created_at} — {action}\n"

    await query.message.reply_text(
        text,
        reply_markup=get_main_menu()
    )

# =========================================
# WARNINGS
# =========================================

async def check_warnings(update: Update, context):

    query = update.callback_query

    await query.answer()

    cursor.execute("""
    SELECT
        name,
        quantity,
        min_quantity
    FROM products
    """)

    products = cursor.fetchall()

    text = ""

    for name, quantity, min_quantity in products:

        if quantity <= min_quantity:

            text += (
                f"⚠️ {name} "
                f"заканчивается "
                f"(осталось {quantity})\n\n"
            )

    if text == "":

        text = "✅ Всё в порядке"

    await query.message.reply_text(
        text,
        reply_markup=get_main_menu()
    )

# =========================================
# CANCEL
# =========================================

async def cancel(update: Update, context):

    await update.message.reply_text(
        "Действие отменено",
        reply_markup=get_main_menu()
    )

    return ConversationHandler.END

# =========================================
# APP
# =========================================

app = (
    ApplicationBuilder()
    .token(TOKEN)
    .build()
)

# =========================================
# ADD HANDLER
# =========================================

add_handler = ConversationHandler(

    entry_points=[
        CallbackQueryHandler(
            add_start,
            pattern="^add_product$"
        )
    ],

    states={

        ADD_NAME: [
            MessageHandler(
                filters.TEXT &
                ~filters.COMMAND,
                add_name
            )
        ],

        ADD_QUANTITY: [
            MessageHandler(
                filters.TEXT &
                ~filters.COMMAND,
                add_quantity
            )
        ],

        ADD_CATEGORY: [
            MessageHandler(
                filters.TEXT &
                ~filters.COMMAND,
                add_category
            )
        ],

        ADD_MIN_QUANTITY: [
            MessageHandler(
                filters.TEXT &
                ~filters.COMMAND,
                add_min_quantity
            )
        ],
    },

    fallbacks=[
        CommandHandler(
            "cancel",
            cancel
        )
    ],
)

# =========================================
# REMOVE HANDLER
# =========================================

remove_handler = ConversationHandler(

    entry_points=[
        CallbackQueryHandler(
            remove_start,
            pattern="^remove_product$"
        )
    ],

    states={

        REMOVE_SELECT: [

            CallbackQueryHandler(
                select_remove_product,
                pattern="^delete_"
            )
        ],

        REMOVE_QUANTITY: [

            MessageHandler(
                filters.TEXT &
                ~filters.COMMAND,
                remove_quantity
            )
        ],
    },

    fallbacks=[
        CommandHandler(
            "cancel",
            cancel
        )
    ],

    per_message=False
)

# =========================================
# FAMILY HANDLER
# =========================================

family_handler = ConversationHandler(

    entry_points=[
        CallbackQueryHandler(
            family_shopping_start,
            pattern="^family_add$"
        )
    ],

    states={

        FAMILY_PRODUCT: [
            MessageHandler(
                filters.TEXT &
                ~filters.COMMAND,
                family_product
            )
        ],

        FAMILY_USER: [
            MessageHandler(
                filters.TEXT &
                ~filters.COMMAND,
                family_user
            )
        ],
    },

    fallbacks=[
        CommandHandler(
            "cancel",
            cancel
        )
    ],
)

# =========================================
# REGISTER HANDLERS
# =========================================

app.add_handler(
    CommandHandler(
        "start",
        start
    )
)

app.add_handler(add_handler)

app.add_handler(remove_handler)

app.add_handler(family_handler)

app.add_handler(
    CallbackQueryHandler(
        show_products,
        pattern="^show_products$"
    )
)

app.add_handler(
    CallbackQueryHandler(
        show_family_shopping,
        pattern="^family_show$"
    )
)

app.add_handler(
    CallbackQueryHandler(
        remove_family_start,
        pattern="^family_remove$"
    )
)

app.add_handler(
    CallbackQueryHandler(
        remove_family_item,
        pattern="^remove_family_"
    )
)

app.add_handler(
    CallbackQueryHandler(
        show_history,
        pattern="^history$"
    )
)

app.add_handler(
    CallbackQueryHandler(
        check_warnings,
        pattern="^warnings$"
    )
)

# =========================================
# START BOT
# =========================================

print("Бот запущен...")

app.run_polling()