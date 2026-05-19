import os
import sqlite3
from datetime import datetime

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

# PRODUCTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    category TEXT,
    expiration_date TEXT,
    min_quantity INTEGER DEFAULT 1
)
""")

# AUTO SHOPPING LIST
cursor.execute("""
CREATE TABLE IF NOT EXISTS shopping_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
""")

# FAMILY SHOPPING LIST
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
    ADD_EXPIRATION,
    ADD_MIN_QUANTITY,

    REMOVE_PRODUCT,
    REMOVE_QUANTITY,

    FAMILY_SHOPPING_NAME,
    FAMILY_SHOPPING_USER,

) = range(9)

# =========================================
# MAIN KEYBOARD
# =========================================

main_keyboard = ReplyKeyboardMarkup(
    [
        ["➕ Добавить продукт"],
        ["📦 Список продуктов"],
        ["❌ Удалить продукт"],

        ["📝 Добавить в покупки"],
        ["🛒 Общий список покупок"],

        ["📜 История"],
        ["⚠️ Проверить уведомления"],
    ],
    resize_keyboard=True
)

# =========================================
# HISTORY
# =========================================

def add_history(action):

    cursor.execute(
        """
        INSERT INTO history
        (action, created_at)
        VALUES (?, ?)
        """,
        (
            action,
            datetime.now().strftime("%d.%m.%Y %H:%M")
        )
    )

    conn.commit()

# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🏠 Семейный бот учета продуктов",
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

    context.user_data["name"] = update.message.text.strip()

    await update.message.reply_text(
        "Введите количество:"
    )

    return ADD_QUANTITY

async def add_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        quantity = int(update.message.text)

        if quantity <= 0:
            raise ValueError

        context.user_data["quantity"] = quantity

        await update.message.reply_text(
            "Введите категорию:\n\n"
            "Например:\n"
            "🥛 Молочка\n"
            "🥩 Мясо\n"
            "🥦 Овощи"
        )

        return ADD_CATEGORY

    except:
        await update.message.reply_text(
            "Введите число."
        )

        return ADD_QUANTITY

async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["category"] = update.message.text.strip()

    await update.message.reply_text(
        "Введите срок годности:\n"
        "ДД.ММ.ГГГГ\n\n"
        "Пример:\n"
        "25.12.2026"
    )

    return ADD_EXPIRATION

async def add_expiration(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        expiration = update.message.text.strip()

        datetime.strptime(expiration, "%d.%m.%Y")

        context.user_data["expiration"] = expiration

        await update.message.reply_text(
            "Введите минимальный остаток:"
        )

        return ADD_MIN_QUANTITY

    except:
        await update.message.reply_text(
            "Неверный формат даты."
        )

        return ADD_EXPIRATION

async def add_min_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        min_quantity = int(update.message.text)

        if min_quantity < 0:
            raise ValueError

        name = context.user_data["name"]
        quantity = context.user_data["quantity"]
        category = context.user_data["category"]
        expiration = context.user_data["expiration"]

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
                expiration_date = ?,
                min_quantity = ?
            WHERE id = ?
            """,
            (
                new_quantity,
                category,
                expiration,
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
                expiration_date,
                min_quantity
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                quantity,
                category,
                expiration,
                min_quantity
            ))

        conn.commit()

        add_history(f"➕ Добавлено: {name} x{quantity}")

        await update.message.reply_text(
            f"✅ Добавлено:\n{name} — {quantity}",
            reply_markup=main_keyboard
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

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("""
    SELECT
        name,
        quantity,
        category,
        expiration_date
    FROM products
    ORDER BY category, name
    """)

    products = cursor.fetchall()

    if not products:

        await update.message.reply_text(
            "📭 Список пуст",
            reply_markup=main_keyboard
        )

        return

    text = "📦 Продукты:\n\n"

    current_category = None

    for name, quantity, category, expiration in products:

        if current_category != category:
            current_category = category
            text += f"\n{category}\n"

        text += (
            f"• {name} — {quantity}\n"
            f"  ⏰ До: {expiration}\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard
    )

# =========================================
# REMOVE START
# =========================================

async def remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("""
    SELECT id, name, quantity
    FROM products
    ORDER BY name
    """)

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
# REMOVE PRODUCT
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

    cursor.execute("""
    SELECT name
    FROM products
    WHERE id = ?
    """, (product_id,))

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
            raise ValueError

        product_id = context.user_data["remove_product_id"]

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
                reply_markup=main_keyboard
            )

            return ConversationHandler.END

        name, current_quantity, min_quantity = result

        if remove_count > current_quantity:

            await update.message.reply_text(
                f"❌ У тебя только {current_quantity} шт.",
                reply_markup=main_keyboard
            )

            return ConversationHandler.END

        new_quantity = current_quantity - remove_count

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
            """, (new_quantity, product_id))

            message = f"✅ Теперь {name}: {new_quantity}"

        conn.commit()

        add_history(f"➖ Удалено: {name} x{remove_count}")

        # AUTO SHOPPING LIST
        if new_quantity <= min_quantity and new_quantity > 0:

            cursor.execute("""
            SELECT id
            FROM shopping_list
            WHERE name = ?
            """, (name,))

            exists = cursor.fetchone()

            if not exists:

                cursor.execute("""
                INSERT INTO shopping_list (name)
                VALUES (?)
                """, (name,))

                conn.commit()

            message += (
                f"\n\n⚠️ {name} заканчивается "
                f"и добавлен в список покупок"
            )

        await update.message.reply_text(
            message,
            reply_markup=main_keyboard
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

async def family_shopping_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "Что нужно купить?",
        reply_markup=ReplyKeyboardRemove()
    )

    return FAMILY_SHOPPING_NAME

# =========================================
# FAMILY SHOPPING NAME
# =========================================

async def family_shopping_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["family_product"] = (
        update.message.text.strip()
    )

    await update.message.reply_text(
        "Кто добавляет?\n\n"
        "Например:\n"
        "Мама"
    )

    return FAMILY_SHOPPING_USER

# =========================================
# FAMILY SHOPPING USER
# =========================================

async def family_shopping_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_name = update.message.text.strip()

    product_name = context.user_data["family_product"]

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
        datetime.now().strftime("%d.%m.%Y %H:%M")
    ))

    conn.commit()

    add_history(
        f"🛒 В покупки добавлено: "
        f"{product_name} ({user_name})"
    )

    await update.message.reply_text(
        f"✅ Добавлено в общий список:\n"
        f"{product_name}",
        reply_markup=main_keyboard
    )

    return ConversationHandler.END

# =========================================
# SHOW FAMILY SHOPPING
# =========================================

async def show_family_shopping(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

        await update.message.reply_text(
            "🛒 Общий список покупок пуст",
            reply_markup=main_keyboard
        )

        return

    text = "🛒 Общий список покупок:\n\n"

    for product_name, added_by, created_at in items:

        text += (
            f"• {product_name}\n"
            f"  👤 {added_by}\n"
            f"  🕒 {created_at}\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard
    )

# =========================================
# HISTORY
# =========================================

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("""
    SELECT action, created_at
    FROM history
    ORDER BY id DESC
    LIMIT 20
    """)

    items = cursor.fetchall()

    if not items:

        await update.message.reply_text(
            "📜 История пуста",
            reply_markup=main_keyboard
        )

        return

    text = "📜 Последние действия:\n\n"

    for action, created_at in items:
        text += f"{created_at} — {action}\n"

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard
    )

# =========================================
# CHECK WARNINGS
# =========================================

async def check_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("""
    SELECT
        name,
        quantity,
        expiration_date,
        min_quantity
    FROM products
    """)

    products = cursor.fetchall()

    text = ""

    now = datetime.now()

    for name, quantity, expiration, min_quantity in products:

        expiration_date = datetime.strptime(
            expiration,
            "%d.%m.%Y"
        )

        days_left = (
            expiration_date - now
        ).days

        if days_left <= 3:

            text += (
                f"⚠️ Скоро испортится:\n"
                f"{name} — через {days_left} дн.\n\n"
            )

        if quantity <= min_quantity:

            text += (
                f"⚠️ Заканчивается:\n"
                f"{name} — осталось {quantity}\n\n"
            )

    if text == "":
        text = "✅ Всё в порядке"

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard
    )

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
            filters.TEXT &
            filters.Regex("^➕ Добавить продукт$"),
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

        ADD_CATEGORY: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                add_category
            )
        ],

        ADD_EXPIRATION: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                add_expiration
            )
        ],

        ADD_MIN_QUANTITY: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                add_min_quantity
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
            filters.TEXT &
            filters.Regex("^❌ Удалить продукт$"),
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
# FAMILY SHOPPING HANDLER
# =========================================

family_shopping_handler = ConversationHandler(

    entry_points=[
        MessageHandler(
            filters.TEXT &
            filters.Regex("^📝 Добавить в покупки$"),
            family_shopping_start
        )
    ],

    states={

        FAMILY_SHOPPING_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                family_shopping_name
            )
        ],

        FAMILY_SHOPPING_USER: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                family_shopping_user
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

app.add_handler(remove_handler)

app.add_handler(family_shopping_handler)

app.add_handler(
    MessageHandler(
        filters.TEXT &
        filters.Regex("^📦 Список продуктов$"),
        show_products
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT &
        filters.Regex("^🛒 Общий список покупок$"),
        show_family_shopping
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT &
        filters.Regex("^📜 История$"),
        show_history
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT &
        filters.Regex("^⚠️ Проверить уведомления$"),
        check_warnings
    )
)

# =========================================
# START BOT
# =========================================

print("Бот запущен...")

app.run_polling()