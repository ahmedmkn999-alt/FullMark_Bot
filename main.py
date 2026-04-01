import telebot
import pyrebase
import random
import datetime
import os
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from keep_alive import keep_alive  # ← للاستخدام مع Replit فقط

# ============================================================
# البيانات الحساسة محمية بـ Environment Variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
OWNER_ID  = None

firebase_config = {
    "apiKey": os.environ.get('FIREBASE_API_KEY'),
    "authDomain": os.environ.get('FIREBASE_AUTH_DOMAIN'),
    "projectId": os.environ.get('FIREBASE_PROJECT_ID'),
    "storageBucket": os.environ.get('FIREBASE_STORAGE_BUCKET'),
    "messagingSenderId": os.environ.get('FIREBASE_MESSAGING_SENDER_ID'),
    "appId": os.environ.get('FIREBASE_APP_ID'),
    "databaseURL": os.environ.get('FIREBASE_DATABASE_URL')
}
# ============================================================

firebase = pyrebase.initialize_app(firebase_config)
db  = firebase.database()
bot = telebot.TeleBot(BOT_TOKEN)

user_state = {}
user_data  = {}


# ════════════════════════════════════════════════════════════
#  صلاحيات
# ════════════════════════════════════════════════════════════
def load_owner():
    global OWNER_ID
    try:
        val = db.child("settings").child("owner_id").get().val()
        if val:
            OWNER_ID = int(val)
    except:
        pass

def get_role(cid):
    load_owner()
    cid = str(cid)
    if OWNER_ID and cid == str(OWNER_ID):
        return "owner"
    try:
        emps = db.child("employees").get()
        if emps.val():
            for e in emps.each():
                if str(e.val().get("user_id", "")) == cid:
                    return "employee"
    except:
        pass
    return "none"

def is_allowed(cid):
    return get_role(cid) in ("owner", "employee")


# ════════════════════════════════════════════════════════════
#  لوحة التحكم
# ════════════════════════════════════════════════════════════
def main_menu(cid):
    role = get_role(cid)
    kb   = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✨ تفعيل طالب جديد", callback_data="new_student"),
        InlineKeyboardButton("🔄 تجديد الاشتراك",   callback_data="renew"),
    )
    kb.add(
        InlineKeyboardButton("🆓 تجربة ساعة",       callback_data="free_trial"),
        InlineKeyboardButton("📱 تغيير الجهاز",     callback_data="change_device"),
    )
    kb.add(
        InlineKeyboardButton("🔍 بحث عن طالب",      callback_data="search"),
        InlineKeyboardButton("👀 كل الطلاب",        callback_data="view_all"),
    )
    if role == "owner":
        kb.add(
            InlineKeyboardButton("🚫 حظر / فك حظر", callback_data="ban_menu"),
            InlineKeyboardButton("💰 كشف الحساب",   callback_data="account"),
        )
        kb.add(
            InlineKeyboardButton("📊 إحصائيات",     callback_data="stats"),
            InlineKeyboardButton("➕ إضافة موظف",   callback_data="add_employee"),
        )
        kb.add(InlineKeyboardButton("👮 الموظفين",  callback_data="view_employees"))
    return kb

def back_btn():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back"))
    return kb


# ════════════════════════════════════════════════════════════
#  /start
# ════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    user_state.pop(cid, None)
    user_data.pop(cid, None)

    load_owner()
    if OWNER_ID is None:
        global OWNER_ID
        OWNER_ID = cid
        db.child("settings").update({"owner_id": cid})

    if not is_allowed(cid):
        bot.send_message(cid, "⛔ مش مسموحلك. تواصل مع المدير.")
        return

    role  = get_role(cid)
    title = "👑 المدير" if role == "owner" else "👤 موظف"
    bot.send_message(
        cid,
        f"🚀 *لوحة تحكم Full Mark*\n{title} — أهلاً بيك!",
        reply_markup=main_menu(cid),
        parse_mode="Markdown"
    )


# ════════════════════════════════════════════════════════════
#  Callback Handler
# ════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)

    if not is_allowed(cid):
        bot.send_message(cid, "⛔ مش مسموحلك."); return

    role = get_role(cid)
    data = call.data

    if data == "new_student":
        user_state[cid] = "new_name"
        bot.send_message(cid, "👤 اكتب *اسم الطالب*:", parse_mode="Markdown")

    elif data == "renew":
        students = get_students_list()
        if not students:
            bot.send_message(cid, "📭 مافيش طلاب.", reply_markup=back_btn()); return
        kb = InlineKeyboardMarkup(row_width=1)
        for key, val in students:
            exp  = val.get("expires", "—")
            name = val.get("name", "—")
            code = val.get("activation_code", "—")
            kb.add(InlineKeyboardButton(
                f"🔄 {name} | 🔑{code} | 📅{exp}",
                callback_data=f"do_renew_{key}"
            ))
        kb.add(InlineKeyboardButton("🏠 رجوع", callback_data="back"))
        bot.send_message(cid, "اختار الطالب اللي عايز تجدد اشتراكه:", reply_markup=kb)

    elif data.startswith("do_renew_"):
        key = data.replace("do_renew_", "")
        val = db.child("students").child(key).get().val()
        if not val:
            bot.send_message(cid, "❌ مش لاقيه.", reply_markup=back_btn()); return
        code    = val.get("activation_code")
        new_exp = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        db.child("students").child(key).update({"expires": new_exp, "banned": False})
        bot.send_message(
            cid,
            f"✅ *تم التجديد!*\n\n"
            f"👤 {val.get('name')}\n"
            f"🔑 الكود: `{code}`\n"
            f"📅 ينتهي: {new_exp}",
            parse_mode="Markdown", reply_markup=back_btn()
        )

    elif data == "free_trial":
        user_state[cid] = "trial_name"
        bot.send_message(cid, "🆓 اكتب *اسم الطالب* للتجربة:", parse_mode="Markdown")

    elif data == "change_device":
        students = get_students_list()
        if not students:
            bot.send_message(cid, "📭 مافيش طلاب.", reply_markup=back_btn()); return
        kb = InlineKeyboardMarkup(row_width=1)
        for key, val in students:
            kb.add(InlineKeyboardButton(
                f"📱 {val.get('name','—')} | 🔑{val.get('activation_code','—')}",
                callback_data=f"do_device_{key}"
            ))
        kb.add(InlineKeyboardButton("🏠 رجوع", callback_data="back"))
        bot.send_message(cid, "اختار الطالب اللي هيغير جهازه:", reply_markup=kb)

    elif data.startswith("do_device_"):
        key = data.replace("do_device_", "")
        val = db.child("students").child(key).get().val()
        if not val:
            bot.send_message(cid, "❌ مش لاقيه.", reply_markup=back_btn()); return
        code = val.get("activation_code")
        db.child("students").child(key).update({"device_id": ""})
        bot.send_message(
            cid,
            f"📱 *تم تغيير الجهاز!*\n\n"
            f"👤 {val.get('name')}\n"
            f"🔑 الكود: `{code}`\n\n"
            f"الطالب يدخل نفس الكود على الجهاز الجديد.",
            parse_mode="Markdown", reply_markup=back_btn()
        )

    elif data == "search":
        user_state[cid] = "search_q"
        bot.send_message(cid, "🔍 اكتب اسم الطالب أو الكود:")

    elif data == "view_all":
        show_all(cid)

    elif data == "ban_menu":
        if role != "owner":
            bot.send_message(cid, "⛔ للمدير فقط."); return
        students = get_students_list()
        if not students:
            bot.send_message(cid, "📭 مافيش طلاب.", reply_markup=back_btn()); return
        kb = InlineKeyboardMarkup(row_width=1)
        for key, val in students:
            banned = val.get("banned", False)
            icon   = "✅ فك حظر" if banned else "🚫 حظر"
            name   = val.get("name", "—")
            kb.add(InlineKeyboardButton(
                f"{icon} | {name}",
                callback_data=f"toggle_ban_{key}"
            ))
        kb.add(InlineKeyboardButton("🏠 رجوع", callback_data="back"))
        bot.send_message(cid, "اختار الطالب:", reply_markup=kb)

    elif data.startswith("toggle_ban_"):
        if role != "owner": bot.send_message(cid, "⛔ للمدير فقط."); return
        key = data.replace("toggle_ban_", "")
        val = db.child("students").child(key).get().val()
        if not val:
            bot.send_message(cid, "❌ مش لاقيه.", reply_markup=back_btn()); return
        new_ban = not val.get("banned", False)
        db.child("students").child(key).update({"banned": new_ban})
        status = "🚫 محظور" if new_ban else "✅ نشط"
        bot.send_message(
            cid,
            f"{status} *{val.get('name')}*",
            parse_mode="Markdown", reply_markup=back_btn()
        )

    elif data == "account":
        if role != "owner": bot.send_message(cid, "⛔ للمدير فقط."); return
        show_account(cid)

    elif data == "stats":
        if role != "owner": bot.send_message(cid, "⛔ للمدير فقط."); return
        show_stats(cid)

    elif data == "add_employee":
        if role != "owner": bot.send_message(cid, "⛔ للمدير فقط."); return
        user_state[cid] = "waiting_employee"
        kb = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        kb.add(KeyboardButton("👤 اختار الموظف من جهات اتصالك", request_contact=True))
        bot.send_message(cid, "اضغط الزرار تحت عشان تختار الموظف:", reply_markup=kb)

    elif data == "view_employees":
        if role != "owner": bot.send_message(cid, "⛔ للمدير فقط."); return
        show_employees(cid)

    elif data.startswith("fire_"):
        if role != "owner": bot.send_message(cid, "⛔ للمدير فقط."); return
        key = data.replace("fire_", "")
        db.child("employees").child(key).remove()
        bot.send_message(cid, "✅ تم حذف الموظف.", reply_markup=back_btn())

    elif data == "back":
        user_state.pop(cid, None)
        user_data.pop(cid, None)
        bot.send_message(cid, "🏠 القائمة الرئيسية:", reply_markup=main_menu(cid))


# ════════════════════════════════════════════════════════════
#  Text Handler
# ════════════════════════════════════════════════════════════
@bot.message_handler(content_types=['text'])
def handle_text(message):
    cid   = message.chat.id
    text  = message.text.strip()
    state = user_state.get(cid)

    if not is_allowed(cid): return
    if not state: start(message); return

    if state == "new_name":
        user_data[cid] = {"name": text}
        user_state[cid] = "new_months"
        bot.send_message(cid, "📅 الاشتراك كام شهر؟ (اكتب رقم):")

    elif state == "new_months":
        try:
            months = int(text)
            if months <= 0: raise ValueError
        except:
            bot.send_message(cid, "❌ اكتب رقم صح."); return
        name    = user_data[cid]["name"]
        code    = gen_code()
        expires = (datetime.date.today() + datetime.timedelta(days=30*months)).strftime("%Y-%m-%d")
        db.child("students").push({
            "name": name, "activation_code": code,
            "type": "monthly", "banned": False,
            "expires": expires, "device_id": ""
        })
        bot.send_message(
            cid,
            f"✅ *تم التفعيل!*\n\n"
            f"👤 {name}\n"
            f"🔑 الكود: `{code}`\n"
            f"📅 ينتهي: {expires}",
            parse_mode="Markdown", reply_markup=back_btn()
        )
        user_state.pop(cid, None); user_data.pop(cid, None)

    elif state == "trial_name":
        code    = gen_code()
        expires = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        db.child("students").push({
            "name": text, "activation_code": code,
            "type": "trial", "banned": False,
            "expires": expires, "device_id": ""
        })
        bot.send_message(
            cid,
            f"🆓 *تجربة مجانية!*\n\n"
            f"👤 {text}\n"
            f"🔑 الكود: `{code}`\n"
            f"⏰ لمدة ساعة من دلوقتي",
            parse_mode="Markdown", reply_markup=back_btn()
        )
        user_state.pop(cid, None)

    elif state == "search_q":
        results = find_students(text)
        if results:
            for key, val in results:
                banned  = val.get("banned", False)
                status  = "🚫 محظور" if banned else "✅ نشط"
                bot.send_message(
                    cid,
                    f"👤 *{val.get('name','—')}*\n"
                    f"🔑 `{val.get('activation_code','—')}`\n"
                    f"📅 ينتهي: {val.get('expires','—')}\n"
                    f"الحالة: {status}",
                    parse_mode="Markdown"
                )
        else:
            bot.send_message(cid, "❌ مش لاقي نتايج.")
        user_state.pop(cid, None)
        bot.send_message(cid, "🏠 القائمة:", reply_markup=back_btn())

    else:
        start(message)


# ════════════════════════════════════════════════════════════
#  Contact Handler
# ════════════════════════════════════════════════════════════
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    cid = message.chat.id
    if user_state.get(cid) != "waiting_employee": return
    c    = message.contact
    name = f"{c.first_name} {c.last_name or ''}".strip()
    db.child("employees").push({
        "name": name, "phone": c.phone_number, "user_id": c.user_id or ""
    })
    bot.send_message(
        cid,
        f"✅ *تم إضافة الموظف!*\n👤 {name}\n📞 {c.phone_number}",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove()
    )
    bot.send_message(cid, "🏠 القائمة:", reply_markup=main_menu(cid))
    user_state.pop(cid, None)


# ════════════════════════════════════════════════════════════
#  دوال مساعدة
# ════════════════════════════════════════════════════════════
def gen_code():
    return "".join([str(random.randint(0, 9)) for _ in range(9)])

def get_students_list():
    try:
        all_s = db.child("students").get()
        if not all_s.val(): return []
        return [(s.key(), s.val()) for s in all_s.each()]
    except: return []

def find_students(query):
    return [
        (k, v) for k, v in get_students_list()
        if query.lower() in v.get("name","").lower()
        or query in v.get("activation_code","")
    ]

def show_all(cid):
    students = get_students_list()
    if not students:
        bot.send_message(cid, "📭 مافيش طلاب.", reply_markup=back_btn()); return
    text = "👥 *كل الطلاب:*\n\n"
    for _, val in students:
        icon  = "🚫" if val.get("banned") else "✅"
        text += f"{icon} *{val.get('name','—')}*\n🔑 `{val.get('activation_code','—')}` | 📅 {val.get('expires','—')}\n\n"
    bot.send_message(cid, text, parse_mode="Markdown", reply_markup=back_btn())

def show_account(cid):
    students = get_students_list()
    active   = sum(1 for _, v in students if not v.get("banned") and v.get("type")=="monthly")
    trial    = sum(1 for _, v in students if v.get("type")=="trial")
    today    = datetime.date.today().strftime("%Y-%m-%d")
    bot.send_message(
        cid,
        f"💰 *كشف الحساب*\n\n"
        f"👥 مشتركين نشطين: {active}\n"
        f"🆓 تجارب: {trial}\n"
        f"📋 الإجمالي: {len(students)}\n"
        f"📅 التاريخ: {today}",
        parse_mode="Markdown", reply_markup=back_btn()
    )

def show_stats(cid):
    students = get_students_list()
    total    = len(students)
    active   = sum(1 for _, v in students if not v.get("banned"))
    banned   = sum(1 for _, v in students if v.get("banned"))
    expiring = 0
    today    = datetime.date.today()
    for _, v in students:
        try:
            exp = datetime.datetime.strptime(v.get("expires",""), "%Y-%m-%d").date()
            if 0 <= (exp - today).days <= 7:
                expiring += 1
        except: pass
    bot.send_message(
        cid,
        f"📊 *الإحصائيات*\n\n"
        f"📋 إجمالي: {total}\n"
        f"✅ نشطين: {active}\n"
        f"🚫 محظورين: {banned}\n"
        f"⚠️ بينتهي خلال 7 أيام: {expiring}",
        parse_mode="Markdown", reply_markup=back_btn()
    )

def show_employees(cid):
    try:
        emps = db.child("employees").get()
    except: emps = None
    if not emps or not emps.val():
        bot.send_message(cid, "📭 مافيش موظفين.", reply_markup=back_btn()); return
    kb = InlineKeyboardMarkup(row_width=1)
    for e in emps.each():
        val = e.val()
        kb.add(InlineKeyboardButton(
            f"🗑 حذف | {val.get('name','—')} | {val.get('phone','')}",
            callback_data=f"fire_{e.key()}"
        ))
    kb.add(InlineKeyboardButton("🏠 رجوع", callback_data="back"))
    bot.send_message(cid, "👮 *الموظفين:*", parse_mode="Markdown", reply_markup=kb)


# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    keep_alive()  # ← يشغل سيرفر صغير لإبقاء Replit شغالاً
    print("✅ البوت شغّال!")
    bot.infinity_polling()
