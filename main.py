import os
import psycopg2
from psycopg2.extras import RealDictCursor
import telebot
from telebot import types
from flask import Flask
from threading import Thread

# ----------------- SOZLAMALAR -----------------

TOKEN = "9129009190:AAGaLxN2NBPeoNoBMqjDY-UARIwv2vU4Ch4"
KANAL_ID = "@tensei_verse"
ADMIN_ID = 8042634468

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


# ----------------- DATABASE -----------------

def get_db():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL Environment Variable topilmadi!")

    return psycopg2.connect(database_url)


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Animelar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS animes (
            code TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            photo TEXT NOT NULL,
            episodes_count INTEGER NOT NULL,
            country TEXT,
            language TEXT,
            year TEXT,
            genre TEXT,
            views TEXT,
            channel_link TEXT
        )
    """)

    # Qismlar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id SERIAL PRIMARY KEY,
            anime_code TEXT NOT NULL,
            episode_number INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            UNIQUE(anime_code, episode_number)
        )
    """)

    cursor.execute("""
        ALTER TABLE animes
        ADD COLUMN IF NOT EXISTS season TEXT DEFAULT '1'
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ PostgreSQL database tayyor!")


# ----------------- INLINE TUGMALAR -----------------

def get_episodes_grid(anime_code, total_episodes):
    markup = types.InlineKeyboardMarkup()
    row = []

    for i in range(1, total_episodes + 1):
        row.append(
            types.InlineKeyboardButton(
                text=str(i),
                callback_data=f"ep_{anime_code}_{i}"
            )
        )

        if len(row) == 5:
            markup.row(*row)
            row = []

    if row:
        markup.row(*row)

    return markup


# ----------------- YUKLANGAN QISMLAR SONINI ANIQLASH -----------------

def get_uploaded_episodes_count(anime_code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM episodes
        WHERE anime_code = %s
        """,
        (anime_code,)
    )

    count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return count


# ----------------- MAJBURIY OBUNANI TEKSHIRISH -----------------

def check_sub(user_id):
    try:
        member = bot.get_chat_member(KANAL_ID, user_id)

        return member.status in [
            "member",
            "creator",
            "administrator"
        ]

    except Exception as e:
        print("Obunani tekshirish xatosi:", e)
        return False


# ----------------- START KOMANDASI -----------------

@bot.message_handler(commands=["start"])
def start_command(message):

    user_id = message.from_user.id

    start_parameter = ""

    if len(message.text.split()) > 1:
        start_parameter = message.text.split()[1]

    anime_code = None

    if start_parameter.startswith("anime"):
        anime_code = start_parameter.replace("anime", "", 1)

    start_text = (
        "Assalomu alaykum bizning botimizga xush kelibsiz!!! "
        "Tomosha qilish uchun Kodni... yozing... ✔️\n\n"
        "Murojat va takliflar uchun:\n\n"
        "@An1verseuzb✔️\n\n"
        "Botdan to'liq foydalanish uchun homiy kanalga azo bo'ling!! ✔️"
    )

    bot.send_message(
        user_id,
        start_text
    )

    # Majburiy obuna tekshiriladi
    if check_sub(user_id):

        if anime_code:
            open_anime_after_subscription(
                user_id,
                anime_code
            )
        else:
            show_search_menu(user_id)

    else:

        markup = types.InlineKeyboardMarkup()

        username_clean = KANAL_ID.replace("@", "")

        markup.add(
            types.InlineKeyboardButton(
                text="An1Verse",
                url=f"tg://resolve?domain={username_clean}"
            )
        )

        if anime_code:
            check_data = f"check_subscription_{anime_code}"
        else:
            check_data = "check_subscription"

        markup.add(
            types.InlineKeyboardButton(
                text="✅ Tekshirish",
                callback_data=check_data
            )
        )

        bot.send_message(
            user_id,
            "🛑 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=markup
        )


# ----------------- MAJBURIY OBUNANI QAYTA TEKSHIRISH -----------------

@bot.callback_query_handler(
    func=lambda call:
        call.data == "check_subscription"
        or call.data.startswith("check_subscription_")
)
def check_callback(call):

    user_id = call.from_user.id

    anime_code = None

    if call.data.startswith("check_subscription_"):

        anime_code = call.data.replace(
            "check_subscription_",
            "",
            1
        )

    if check_sub(user_id):

        try:
            bot.delete_message(
                call.message.chat.id,
                call.message.message_id
            )
        except Exception:
            pass

        if anime_code:

            open_anime_after_subscription(
                user_id,
                anime_code
            )

        else:

            show_search_menu(user_id)

        bot.answer_callback_query(
            call.id,
            "✅ Obuna tasdiqlandi!"
        )

    else:

        bot.answer_callback_query(
            call.id,
            "❌ Siz hali kanalga a'zo bo'lmagansiz!",
            show_alert=True
        )


# ----------------- ANIMENI KOD BO'YICHA OCHISH -----------------

def open_anime_after_subscription(
    user_id,
    anime_code
):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM animes
        WHERE code = %s
        """,
        (anime_code,)
    )

    anime = cursor.fetchone()

    cursor.close()
    conn.close()

    if not anime:

        bot.send_message(
            user_id,
            "❌ Bunday kodli anime topilmadi."
        )

        return

    # Bazaga yuklangan qismlar sonini olish
    uploaded_episodes = get_uploaded_episodes_count(anime_code)

    caption = (
    f"🎬 **Nomi:** {anime[1]}\n\n"
    f"🥷 **Qismi:** {uploaded_episodes}/{anime[3]}\n"
    f"🎞 **Tili:** {anime[4]}\n"
    f"📅 **Yili:** {anime[5]}\n"
    f"🎭 **Janri:** {anime[6]}\n\n"
    f"🍿 {anime[7]}"
    )

    markup = get_episodes_grid(
        anime_code,
        anime[3]
    )

    bot.send_photo(
        chat_id=user_id,
        photo=anime[2],
        caption=caption,
        parse_mode="Markdown",
        reply_markup=markup
    )


# ----------------- QIDIRUV MENYUSI -----------------

def show_search_menu(user_id):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.add(
        types.KeyboardButton(
            "🔍 Anime qidirish"
        )
    )

    bot.send_message(
        user_id,
        "Pastdagi tugmani bosib anime qidirishingiz mumkin 👇",
        reply_markup=markup
    )


# ----------------- KANALGA ANIME POST YUBORISH -----------------

@bot.message_handler(commands=["addanime"])
def admin_add_anime_to_channel(message):

    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()

    anime_id = (
        args[1]
        if len(args) > 1
        else "1"
    )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM animes
        WHERE code = %s
        """,
        (anime_id,)
    )

    anime = cursor.fetchone()

    cursor.close()
    conn.close()

    if anime:

        bot_info = bot.get_me()

        # Bazaga yuklangan qismlar sonini olish
        uploaded_episodes = get_uploaded_episodes_count(anime_id)

        channel_caption = (
        f"⟢⟢⟢ {anime[1]} ⟢⟢⟢\n"
        f"╭─ 🎞️ Qism  ─ {uploaded_episodes}/{anime[3]}\n"
        f"├─ 🇺🇿 Til   ─ {anime[5]}\n"
        f"├─ 🎭 Janr  ─ {anime[7]}\n"
        f"╰─ 📢 Kanal ─ @an1verseuz"
        )

        channel_markup = types.InlineKeyboardMarkup()

        bot_link = (
            f"tg://resolve?domain="
            f"{bot_info.username}"
            f"&start=anime{anime_id}"
        )

        btn_go_bot = types.InlineKeyboardButton(
            text="✨YUKLAB OLISH✨",
            url=bot_link
        )

        channel_markup.add(
            btn_go_bot
        )

        bot.send_photo(
            chat_id=KANAL_ID,
            photo=anime[2],
            caption=channel_caption,
            parse_mode="Markdown",
            reply_markup=channel_markup
        )

        bot.reply_to(
            message,
            "✅ Post kanalingizga muvaffaqiyatli yuborildi!"
        )

    else:

        bot.reply_to(
            message,
            f"❌ Kod {anime_id} bo'yicha anime bazada topilmadi!"
        )

# ----------------- ANIMELAR RO'YXATI -----------------

@bot.message_handler(commands=["listanime"])
def list_animes(message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT code, title
        FROM animes
        ORDER BY CAST(code AS INTEGER) ASC
        """
    )

    animes = cursor.fetchall()

    cursor.close()
    conn.close()

    if not animes:
        bot.reply_to(
            message,
            "📚 Hozircha bazada anime mavjud emas."
        )
        return

    text = "📚 ANIMELAR RO‘YXATI\n\n"

    for code, title in animes:
        text += f"{code} — {title}\n"

    bot.reply_to(
        message,
        text
)

# ----------------- EPIZOD QO'SHISH -----------------

@bot.message_handler(commands=["addep"])
def admin_add_episode(message):

    if message.from_user.id != ADMIN_ID:
        return

    if (
        not message.reply_to_message
        or not message.reply_to_message.video
    ):

        bot.reply_to(
            message,
            "⚠️ Xato: Avval videoga reply qilib, keyin buyruqni yozing!"
        )

        return

    try:

        args = message.text.split()

        if len(args) < 3:

            bot.reply_to(
                message,
                "⚠️ Format:\n/addep KOD QISM\n\nMasalan:\n/addep 1 1"
            )

            return

        anime_code = args[1]
        ep_num = int(args[2])

        video_id = (
            message.reply_to_message.video.file_id
        )

        # ----------------- QISMNI BAZAGA SAQLASH -----------------

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO episodes
            (
                anime_code,
                episode_number,
                video_id
            )
            VALUES (%s, %s, %s)

            ON CONFLICT
            (
                anime_code,
                episode_number
            )

            DO UPDATE SET
                video_id = EXCLUDED.video_id
            """,
            (
                anime_code,
                ep_num,
                video_id
            )
        )

        conn.commit()

        cursor.close()
        conn.close()


        # ----------------- ANIME MA'LUMOTLARINI OLISH -----------------

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM animes
            WHERE code = %s
            """,
            (anime_code,)
        )

        anime = cursor.fetchone()

        cursor.close()
        conn.close()


        # ----------------- KANALGA YANGI POST YUBORISH -----------------

        if anime and int(anime_code) >= 100:

            uploaded_episodes = get_uploaded_episodes_count(
                anime_code
            )

            channel_caption = (
                f"⟢⟢⟢ {anime[1]} ⟢⟢⟢\n"
                f"╭─ 🎞️ Qism  ─ {uploaded_episodes}/{anime[3]}\n"
                f"├─ 🇺🇿 Til   ─ {anime[5]}\n"
                f"├─ 🎭 Janr  ─ {anime[7]}\n"
                f"╰─ 📢 Kanal ─ @an1verseuz"
            )

            bot_info = bot.get_me()

            bot_link = (
                f"tg://resolve?domain="
                f"{bot_info.username}"
                f"&start=anime{anime_code}"
            )

            channel_markup = types.InlineKeyboardMarkup()

            btn_go_bot = types.InlineKeyboardButton(
                text="✨ YUKLAB OLISH ✨",
                url=bot_link
            )

            channel_markup.add(
                btn_go_bot
            )

            bot.send_photo(
                chat_id=KANAL_ID,
                photo=anime[2],
                caption=channel_caption,
                parse_mode="Markdown",
                reply_markup=channel_markup
            )


        # ----------------- ADMIN'GA XABAR -----------------

        bot.reply_to(
            message,
            f"✅ Kod {anime_code}: "
            f"{ep_num}-qism bazaga saqlandi!\n\n"
            f"📢 Kanalga yangi post yuborildi!"
        )


    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Xato yuz berdi:\n{e}"
)


# ----------------- ANIME MA'LUMOTLARINI TAHRIRLASH -----------------

@bot.message_handler(commands=["editanime"])
def edit_anime(message):

    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()

    if len(args) < 2:
        bot.reply_to(
            message,
            "⚠️ Format:\n\n"
            "/editanime KOD\n\n"
            "Masalan:\n"
            "/editanime 101"
        )
        return

    anime_code = args[1]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM animes
        WHERE code = %s
        """,
        (anime_code,)
    )

    anime = cursor.fetchone()

    cursor.close()
    conn.close()

    if not anime:
        bot.reply_to(
            message,
            f"❌ {anime_code} kodli anime topilmadi!"
        )
        return

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "🎬 Nomi",
            callback_data=f"edit_title_{anime_code}"
        ),
        types.InlineKeyboardButton(
            "🎞 Qism soni",
            callback_data=f"edit_eps_{anime_code}"
        ),
        types.InlineKeyboardButton(
            "🌐 Tili",
            callback_data=f"edit_lang_{anime_code}"
        ),
        types.InlineKeyboardButton(
            "📅 Yili",
            callback_data=f"edit_year_{anime_code}"
        ),
        types.InlineKeyboardButton(
            "🎭 Janri",
            callback_data=f"edit_genre_{anime_code}"
        ),
        types.InlineKeyboardButton(
            "📚 Fasli",
            callback_data=f"edit_season_{anime_code}"
        ),
        types.InlineKeyboardButton(
            "🔗 Kanal linki",
            callback_data=f"edit_channel_{anime_code}"
        ),
        types.InlineKeyboardButton(
            "🖼 Rasm",
            callback_data=f"edit_photo_{anime_code}"
        )
    )

    bot.reply_to(
        message,
        f"✏️ {anime[1]}\n\n"
        f"Qaysi ma'lumotni o'zgartirmoqchisiz?",
        reply_markup=markup
    )


# ----------------- EDIT ANIME CALLBACK -----------------

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("edit_")
)
def edit_anime_callback(call):

    if call.from_user.id != ADMIN_ID:
        return

    parts = call.data.split("_")

    field = parts[1]
    anime_code = "_".join(parts[2:])

    messages = {
        "title": "🎬 Yangi anime nomini yuboring:",
        "eps": "🎞 Yangi qism sonini yuboring:",
        "lang": "🌐 Yangi tilni yuboring:",
        "year": "📅 Yangi yilni yuboring:",
        "genre": "🎭 Yangi janrni yuboring:",
        "season": "📚 Yangi faslni yuboring:\n\nMasalan: 3",
        "channel": "🔗 Yangi kanal linkini yuboring:",
        "photo": "🖼 Yangi rasmni yuboring:"
    }

    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        messages.get(
            field,
            "Yangi ma'lumotni yuboring:"
        )
    )

    bot.register_next_step_handler(
        call.message,
        save_edited_anime,
        anime_code,
        field
    )


# ----------------- O'ZGARTIRILGAN MA'LUMOTNI SAQLASH -----------------

def save_edited_anime(
    message,
    anime_code,
    field
):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        field_map = {
            "title": "title",
            "eps": "episodes_count",
            "lang": "language",
            "year": "year",
            "genre": "genre",
            "season": "season",
            "channel": "channel_link"
        }

        # ----------------- RASM -----------------

        if field == "photo":

            if not message.photo:

                bot.reply_to(
                    message,
                    "❌ Iltimos, rasm yuboring!"
                )

                return

            new_value = message.photo[-1].file_id
            db_field = "photo"

        # ----------------- MATN -----------------

        else:

            if not message.text:

                bot.reply_to(
                    message,
                    "❌ Iltimos, matn yuboring!"
                )

                return

            new_value = message.text.strip()

            db_field = field_map.get(field)

            if not db_field:

                bot.reply_to(
                    message,
                    "❌ Noma'lum ma'lumot!"
                )

                return

            # Qism soni raqam bo'lishi kerak
            if field == "eps":

                new_value = int(new_value)

                if new_value < 1:

                    bot.reply_to(
                        message,
                        "❌ Qism soni 1 yoki undan katta bo'lishi kerak!"
                    )

                    return

        # ----------------- BAZANI YANGILASH -----------------

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            f"""
            UPDATE animes
            SET {db_field} = %s
            WHERE code = %s
            """,
            (
                new_value,
                anime_code
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        bot.reply_to(
            message,
            f"✅ {anime_code} kodli anime "
            f"ma'lumoti muvaffaqiyatli o'zgartirildi!"
        )

    except ValueError:

        bot.reply_to(
            message,
            "❌ Qism soni raqam bo'lishi kerak!\n\n"
            "Masalan: 12"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Ma'lumotni o'zgartirishda xatolik:\n\n"
            f"{e}"
        )

# ----------------- BIR NECHTA EPIZODNI BIRDAN QO'SHISH -----------------

bulk_sessions = {}


@bot.message_handler(commands=["addbulk"])
def admin_add_bulk(message):

    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()

    if len(args) < 2:
        bot.reply_to(
            message,
            "⚠️ Format:\n\n"
            "/addbulk KOD\n\n"
            "Masalan:\n"
            "/addbulk 101\n\n"
            "Keyin videolarni ketma-ket yuboring."
        )
        return

    anime_code = args[1]

    # Anime mavjudligini tekshirish
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT code, title, episodes_count
        FROM animes
        WHERE code = %s
        """,
        (anime_code,)
    )

    anime = cursor.fetchone()

    cursor.close()
    conn.close()

    if not anime:
        bot.reply_to(
            message,
            f"❌ {anime_code} kodli anime topilmadi!"
        )
        return

    # Bulk rejimini boshlash
    bulk_sessions[message.from_user.id] = {
        "anime_code": anime_code,
        "episode": 1
    }

    bot.reply_to(
        message,
        f"✅ Bulk qo'shish boshlandi!\n\n"
        f"🎬 Anime: {anime[1]}\n"
        f"🎞 Jami qism: {anime[2]}\n\n"
        f"📥 Endi videolarni ketma-ket yuboring.\n"
        f"1-video → 1-qism\n"
        f"2-video → 2-qism\n"
        f"3-video → 3-qism\n\n"
        f"🛑 Tugatish uchun /stopbulk yozing.\n\n"
        f"📢 Videolar kanalga yuborilmaydi!"
    )


@bot.message_handler(commands=["stopbulk"])
def admin_stop_bulk(message):

    if message.from_user.id != ADMIN_ID:
        return

    if message.from_user.id not in bulk_sessions:
        bot.reply_to(
            message,
            "⚠️ Hozir bulk qo'shish rejimi yoqilmagan."
        )
        return

    session = bulk_sessions.pop(message.from_user.id)

    next_episode = session["episode"]

    bot.reply_to(
        message,
        f"✅ Bulk qo'shish tugatildi!\n\n"
        f"📌 Kod: {session['anime_code']}\n"
        f"🎞 Qo'shilgan qismlar: {next_episode - 1}"
    )


@bot.message_handler(content_types=["video"])
def admin_bulk_video(message):

    if message.from_user.id != ADMIN_ID:
        return

    # Bulk rejimi yoqilmagan bo'lsa, hech narsa qilmaydi
    if message.from_user.id not in bulk_sessions:
        return

    session = bulk_sessions[message.from_user.id]

    anime_code = session["anime_code"]
    ep_num = session["episode"]

    video_id = message.video.file_id

    try:

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO episodes
            (
                anime_code,
                episode_number,
                video_id
            )
            VALUES (%s, %s, %s)

            ON CONFLICT
            (
                anime_code,
                episode_number
            )

            DO UPDATE SET
                video_id = EXCLUDED.video_id
            """,
            (
                anime_code,
                ep_num,
                video_id
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        # Keyingi qism raqami
        session["episode"] += 1

        bot.reply_to(
            message,
            f"✅ {ep_num}-qism saqlandi!\n\n"
            f"📌 Kod: {anime_code}\n"
            f"➡️ Keyingi video → {ep_num + 1}-qism\n\n"
            f"📢 Kanalga yuborilmadi."
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ {ep_num}-qismni saqlashda xatolik:\n\n"
            f"{e}"
        )
    
# ----------------- EPIZODNI O'CHIRISH -----------------

@bot.message_handler(commands=["deleteanime"])
def admin_delete_episode(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        args = message.text.split()

        if len(args) < 3:

            bot.reply_to(
                message,
                "⚠️ Format:\n"
                "/deleteanime KOD QISM\n\n"
                "Masalan:\n"
                "/deleteanime 2 5"
            )

            return

        anime_code = args[1]
        ep_num = int(args[2])

        conn = get_db()
        cursor = conn.cursor()

        # Avval shu qism mavjudligini tekshirish

        cursor.execute(
            """
            SELECT id
            FROM episodes
            WHERE anime_code = %s
            AND episode_number = %s
            """,
            (
                anime_code,
                ep_num
            )
        )

        episode = cursor.fetchone()

        if not episode:

            cursor.close()
            conn.close()

            bot.reply_to(
                message,
                f"❌ {anime_code}-kodli animening "
                f"{ep_num}-qismi bazada topilmadi!"
            )

            return

        # Qismni o'chirish

        cursor.execute(
            """
            DELETE FROM episodes
            WHERE anime_code = %s
            AND episode_number = %s
            """,
            (
                anime_code,
                ep_num
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        bot.reply_to(
            message,
            f"✅ {anime_code}-kodli animening "
            f"{ep_num}-qismi muvaffaqiyatli o'chirildi!"
        )

    except ValueError:

        bot.reply_to(
            message,
            "❌ Qism raqami raqam bo'lishi kerak!\n\n"
            "Masalan:\n"
            "/deleteanime 2 5"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Qismni o'chirishda xatolik yuz berdi:\n\n"
            f"{e}"
        )

# ----------------- YANGI ANIME QO'SHISH -----------------

@bot.message_handler(content_types=["photo"])
def add_anime_to_database(message):

    if message.from_user.id != ADMIN_ID:
        return

    if (
        not message.caption
        or not message.caption.startswith(
            "/addanime_db"
        )
    ):
        return

    try:

        data = message.caption.replace(
            "/addanime_db",
            "",
            1
        ).strip()

        parts = [
            x.strip()
            for x in data.split("|")
        ]

        # Yangi format:
        # KOD | NOMI | QISMLAR SONI | TILI | YILI | JANRI | KANAL LINKI | TA'RIF

        if len(parts) < 8:

            bot.reply_to(
                message,
                "❌ Format xato!\n\n"
                "To'g'ri format:\n\n"
                "/addanime_db KOD | NOMI | QISMLAR SONI | TILI | YILI | JANRI | KANAL LINKI | TA'RIF"
            )

            return

        code = parts[0]
        title = parts[1]

        episodes_count = int(
            parts[2]
        )

        language = parts[3]
        year = parts[4]
        genre = parts[5]
        channel_link = parts[6]

        description = "|".join(
            parts[7:]
        )

        # Davlati va ko'rishlar soni endi ishlatilmaydi
        country = ""
        views = ""

        photo_id = (
            message.photo[-1].file_id
        )

        conn = get_db()
        cursor = conn.cursor()

        # Kod mavjudligini tekshirish

        cursor.execute(
            """
            SELECT code
            FROM animes
            WHERE code = %s
            """,
            (code,)
        )

        if cursor.fetchone():

            cursor.close()
            conn.close()

            bot.reply_to(
                message,
                f"⚠️ {code} kodi bilan anime "
                f"allaqachon bazada mavjud!"
            )

            return

        # Anime qo'shish

        cursor.execute(
            """
            INSERT INTO animes
            (
                code,
                title,
                photo,
                episodes_count,
                country,
                language,
                year,
                genre,
                views,
                channel_link
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                code,
                title,
                photo_id,
                episodes_count,
                country,
                language,
                year,
                genre,
                views,
                channel_link
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        bot.reply_to(
            message,
            f"✅ Anime bazaga muvaffaqiyatli qo'shildi!\n\n"
            f"🔑 Kod: {code}\n"
            f"🎬 Nomi: {title}\n"
            f"🎞 Qismlar: {episodes_count}\n"
            f"🎞 Tili: {language}\n"
            f"📅 Yili: {year}\n"
            f"🎭 Janri: {genre}\n"
            f"📢 Kanal: {channel_link}\n\n"
            f"📝 Ta'rif qabul qilindi."
        )

    except ValueError:

        bot.reply_to(
            message,
            "❌ Xatolik: Qismlar soni raqam "
            "bo'lishi kerak!\n\n"
            "Masalan: 12"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Anime qo'shishda xatolik yuz berdi:\n\n"
            f"{e}"
        )


# ----------------- QIDIRUV -----------------

@bot.message_handler(
    func=lambda message: True
)
def handle_messages(message):

    user_id = message.from_user.id

    if not check_sub(user_id):

        bot.send_message(
            user_id,
            "🛑 Kanalga a'zolikdan chiqib ketgansiz! "
            "Qayta start bosing: /start"
        )

        return

    if message.text == "🔍 Anime qidirish":

        bot.send_message(
            user_id,
            "Anime kodini kiriting (Masalan: 1):"
        )

        return

    code = message.text.strip()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM animes
        WHERE code = %s
        """,
        (code,)
    )

    anime = cursor.fetchone()

    cursor.close()
    conn.close()

    if anime:

        # Bazaga yuklangan qismlar sonini olish
        uploaded_episodes = get_uploaded_episodes_count(code)

        caption = (
            f"🎬 **Nomi:** {anime[1]}\n\n"
            f"🥷 **Qismi:** {uploaded_episodes}/{anime[3]}\n"
            f"🌍 **Davlati:** {anime[4]}\n"
            f"🎞 **Tili:** {anime[5]}\n"
            f"📅 **Yili:** {anime[6]}\n"
            f"🎭 **Janri:** {anime[7]}\n\n"
            f"🔍 **Qidirishlar soni:** {anime[8]}\n\n"
            f"🍿 {anime[9]}"
        )

        markup = get_episodes_grid(
            code,
            anime[3]
        )

        bot.send_photo(
            chat_id=user_id,
            photo=anime[2],
            caption=caption,
            parse_mode="Markdown",
            reply_markup=markup
        )

    else:

        bot.send_message(
            user_id,
            "❌ Bunday kodli anime topilmadi. "
            "Qayta urinib ko'ring."
        )


# ----------------- EPIZODNI YUBORISH -----------------

@bot.callback_query_handler(
    func=lambda call:
        call.data.startswith("ep_")
)
def send_episode_callback(call):

    try:

        _, anime_code, ep_num = (
            call.data.split("_")
        )

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT video_id
            FROM episodes
            WHERE anime_code = %s
            AND episode_number = %s
            """,
            (
                anime_code,
                int(ep_num)
            )
        )

        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if row:

            bot.send_video(
                chat_id=call.message.chat.id,
                video=row[0],
                caption=f"{ep_num}-qism"
            )

            bot.answer_callback_query(
                call.id
            )

        else:

            bot.answer_callback_query(
                call.id,
                "⚠️ Bu qism videosi hali serverga yuklanmagan!",
                show_alert=True
            )

    except Exception as e:

        print(
            "Episode yuborish xatosi:",
            e
        )

        bot.answer_callback_query(
            call.id,
            "❌ Videoni yuborishda xatolik yuz berdi!",
            show_alert=True
        )


# ----------------- FLASK -----------------

@app.route("/")
def home():

    return "Bot is running!"


def run():

    port = int(
        os.environ.get(
            "PORT",
            8080
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )


# ----------------- RUN -----------------

if __name__ == "__main__":

    init_db()

    t = Thread(
        target=run
    )

    t.start()

    print(
        "Bot muvaffaqiyatli ishga tushdi..."
    )

    bot.infinity_polling()
