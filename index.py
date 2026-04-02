import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request
import os, json, random, datetime

# ═══════════════════════════════════════════════════════════
#  1. Firebase
# ═══════════════════════════════════════════════════════════
if not firebase_admin._apps:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_path  = os.path.join(base_dir, "firebase-key.json")
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ═══════════════════════════════════════════════════════════
#  2. إعدادات البوت
# ═══════════════════════════════════════════════════════════
TOKEN    = os.environ.get("BOT_TOKEN", "8296071930:AAGtL5Lr_zCc3DlKToMpRHc0citP7CX2x2s")
OWNER_ID = int(os.environ.get("OWNER_ID", "6188310641"))

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

user_state = {}   # { uid: { 'step': '...', ...data } }


# ═══════════════════════════════════════════════════════════
#  3. دوال مساعدة
# ═══════════════════════════════════════════════════════════
def get_role(uid):
    if uid == OWNER_ID: return "owner"
    if db.collection('admins').document(str(uid)).get().exists: return "admin"
    if db.collection('staff').document(str(uid)).get().exists:  return "staff"
    return None

def gen_code():
    return "".join([str(random.randint(0, 9)) for _ in range(9)])

def back_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="home"))
    return kb

def get_all_students():
    return [(d.id, d.to_dict()) for d in db.collection('students').stream()]

def inc_staff_count(uid):
    if get_role(uid) == "staff":
        db.collection('staff').document(str(uid)).update(
            {'codes_count': firestore.Increment(1)}
        )

# ═══════════════════════════════════════════════════════════
#  4. لوحة التحكم
# ═══════════════════════════════════════════════════════════
def main_kb(uid):
    role   = get_role(uid)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✨ تفعيل طالب",       callback_data="act_std"),
        types.InlineKeyboardButton("🔄 تجديد الاشتراك",   callback_data="renew"),
        types.InlineKeyboardButton("📱 تغيير جهاز",       callback_data="chg_dev"),
        types.InlineKeyboardButton("🆓 تجربة ساعة",       callback_data="trial"),
        types.InlineKeyboardButton("🔍 بحث عن طالب",      callback_data="search"),
        types.InlineKeyboardButton("🚫 حظر / فك حظر",     callback_data="ban_menu"),
    )
    if role in ["owner", "admin"]:
        markup.add(types.InlineKeyboardButton("📊 إحصائيات الموظفين", callback_data="stats"))
    if role == "owner":
        markup.add(
            types.InlineKeyboardButton("➕ إضافة أدمن/موظف", callback_data="add_mem"),
            types.InlineKeyboardButton("👮 عرض الأعضاء",     callback_data="view_members"),
        )
    return markup

# ═══════════════════════════════════════════════════════════
#  5. /start
# ═══════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def start(message):
    uid  = message.from_user.id
    role = get_role(uid)
    if not role:
        bot.reply_to(message, "⚠️ الدخول للمصرح لهم فقط."); return
    if message.from_user.username:
        db.collection('users_map').document(
            message.from_user.username.lower()
        ).set({'user_id': uid, 'username': message.from_user.username})
    user_state.pop(uid, None)
    bot.send_message(
        message.chat.id,
        f"🚀 *لوحة تحكم Full Mark*\nالرتبة: *{role}*",
        reply_markup=main_kb(uid), parse_mode="Markdown"
    )

# ═══════════════════════════════════════════════════════════
#  6. Callback Handler
# ═══════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: True)
def handle_all_callbacks(call):
    uid  = call.from_user.id
    cid  = call.message.chat.id
    mid  = call.message.message_id
    data = call.data
    role = get_role(uid)

    bot.answer_callback_query(call.id)  # ← يمنع التعليق دايماً

    if not role:
        bot.send_message(cid, "⚠️ غير مصرح لك."); return

    # ── رجوع ──────────────────────────────────────────────
    if data == "home":
        user_state.pop(uid, None)
        bot.edit_message_text(
            f"🚀 *لوحة تحكم Full Mark*\nالرتبة: *{role}*",
            cid, mid, reply_markup=main_kb(uid), parse_mode="Markdown"
        )

    # ── تفعيل طالب جديد ───────────────────────────────────
    elif data == "act_std":
        user_state[uid] = {'step': 'act_name'}
        bot.edit_message_text("👤 اكتب *اسم الطالب*:", cid, mid, parse_mode="Markdown")

    # ── تجديد: كل الطلاب + زرار جنب كل واحد ──────────────
    elif data == "renew":
        students = get_all_students()
        if not students:
            bot.edit_message_text("📭 مافيش طلاب.", cid, mid, reply_markup=back_kb()); return
        kb = types.InlineKeyboardMarkup(row_width=1)
        for doc_id, val in students:
            kb.add(types.InlineKeyboardButton(
                f"🔄 {val.get('name','—')} | 🔑{val.get('activation_code','—')} | 📅{val.get('expires','—')}",
                callback_data=f"do_renew_{doc_id}"
            ))
        kb.add(types.InlineKeyboardButton("🏠 رجوع", callback_data="home"))
        bot.edit_message_text("اختار الطالب اللي عايز تجدده:", cid, mid, reply_markup=kb)

    elif data.startswith("do_renew_"):
        doc_id = data.replace("do_renew_", "")
        ref    = db.collection('students').document(doc_id)
        val    = ref.get().to_dict()
        if not val:
            bot.edit_message_text("❌ مش لاقيه.", cid, mid, reply_markup=back_kb()); return
        code    = val.get("activation_code")   # نفس الكود
        new_exp = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        ref.update({"expires": new_exp, "banned": False})
        bot.edit_message_text(
            f"✅ *تم التجديد!*\n\n👤 {val.get('name')}\n🔑 `{code}`\n📅 ينتهي: {new_exp}",
            cid, mid, parse_mode="Markdown", reply_markup=back_kb()
        )

    # ── تغيير الجهاز: كل الطلاب + زرار ───────────────────
    elif data == "chg_dev":
        students = get_all_students()
        if not students:
            bot.edit_message_text("📭 مافيش طلاب.", cid, mid, reply_markup=back_kb()); return
        kb = types.InlineKeyboardMarkup(row_width=1)
        for doc_id, val in students:
            kb.add(types.InlineKeyboardButton(
                f"📱 {val.get('name','—')} | 🔑{val.get('activation_code','—')}",
                callback_data=f"do_dev_{doc_id}"
            ))
        kb.add(types.InlineKeyboardButton("🏠 رجوع", callback_data="home"))
        bot.edit_message_text("اختار الطالب اللي هيغير جهازه:", cid, mid, reply_markup=kb)

    elif data.startswith("do_dev_"):
        doc_id = data.replace("do_dev_", "")
        ref    = db.collection('students').document(doc_id)
        val    = ref.get().to_dict()
        if not val:
            bot.edit_message_text("❌ مش لاقيه.", cid, mid, reply_markup=back_kb()); return
        code = val.get("activation_code")   # نفس الكود - reset الجهاز بس
        ref.update({"device_id": ""})
        bot.edit_message_text(
            f"📱 *تم Reset الجهاز!*\n\n👤 {val.get('name')}\n🔑 `{code}`\n\n"
            f"الطالب يدخل نفس الكود على الجهاز الجديد.",
            cid, mid, parse_mode="Markdown", reply_markup=back_kb()
        )

    # ── تجربة مجانية ──────────────────────────────────────
    elif data == "trial":
        user_state[uid] = {'step': 'trial_name'}
        bot.edit_message_text("🆓 اكتب *اسم الطالب* للتجربة:", cid, mid, parse_mode="Markdown")

    # ── بحث ───────────────────────────────────────────────
    elif data == "search":
        user_state[uid] = {'step': 'search_q'}
        bot.edit_message_text("🔍 اكتب اسم الطالب أو الكود:", cid, mid)

    # ── حظر / فك حظر ──────────────────────────────────────
    elif data == "ban_menu":
        students = get_all_students()
        if not students:
            bot.edit_message_text("📭 مافيش طلاب.", cid, mid, reply_markup=back_kb()); return
        kb = types.InlineKeyboardMarkup(row_width=1)
        for doc_id, val in students:
            banned = val.get("banned", False)
            icon   = "✅ فك الحظر" if banned else "🚫 حظر"
            kb.add(types.InlineKeyboardButton(
                f"{icon} | {val.get('name','—')} | 🔑{val.get('activation_code','—')}",
                callback_data=f"toggle_ban_{doc_id}"
            ))
        kb.add(types.InlineKeyboardButton("🏠 رجوع", callback_data="home"))
        bot.edit_message_text("اختار الطالب:", cid, mid, reply_markup=kb)

    elif data.startswith("toggle_ban_"):
        doc_id = data.replace("toggle_ban_", "")
        ref    = db.collection('students').document(doc_id)
        val    = ref.get().to_dict()
        if not val:
            bot.edit_message_text("❌ مش لاقيه.", cid, mid, reply_markup=back_kb()); return
        banned = val.get("banned", False)
        ref.update({"banned": not banned})
        action = "✅ تم فك الحظر عن" if banned else "🚫 تم حظر"
        bot.edit_message_text(
            f"{action} *{val.get('name')}*",
            cid, mid, parse_mode="Markdown", reply_markup=back_kb()
        )

    # ── إحصائيات ──────────────────────────────────────────
    elif data == "stats":
        if role not in ["owner", "admin"]:
            bot.send_message(cid, "⛔ للأدمن فقط."); return
        staff_docs = db.collection('staff').stream()
        lines = [f"👤 @{d.to_dict().get('username','—')}: {d.to_dict().get('codes_count', 0)} كود" for d in staff_docs]
        msg   = "📊 *إنتاجية الموظفين:*\n\n" + "\n".join(lines) if lines else "📭 مافيش موظفين."
        bot.edit_message_text(msg, cid, mid, parse_mode="Markdown", reply_markup=back_kb())

    # ── إضافة عضو ─────────────────────────────────────────
    elif data == "add_mem":
        if role != "owner": bot.send_message(cid, "⛔ للمالك فقط."); return
        user_state[uid] = {'step': 'wait_un'}
        bot.edit_message_text(
            "أرسل *يوزرنيم* الشخص (بدون @):\n\n_ملاحظة: لازم يكون ضغط /start في البوت الأول._",
            cid, mid, parse_mode="Markdown"
        )

    elif data in ["set_admin", "set_staff"]:
        if role != "owner": return
        st  = user_state.get(uid, {})
        col = "admins" if "admin" in data else "staff"
        db.collection(col).document(str(st['t_id'])).set({'username': st['t_un'], 'codes_count': 0})
        label = "أدمن" if "admin" in data else "موظف"
        bot.edit_message_text(
            f"✅ تمت إضافة @{st['t_un']} كـ {label}!",
            cid, mid, reply_markup=back_kb()
        )
        user_state.pop(uid, None)

    # ── عرض الأعضاء ───────────────────────────────────────
    elif data == "view_members":
        if role != "owner": return
        admins = [d.to_dict() for d in db.collection('admins').stream()]
        staff  = [d.to_dict() for d in db.collection('staff').stream()]
        msg    = "👮 *الأعضاء:*\n\n"
        msg   += "*الأدمن:*\n" + ("".join([f"• @{v.get('username','—')}\n" for v in admins]) or "لا يوجد\n")
        msg   += "\n*الموظفون:*\n" + ("".join([f"• @{v.get('username','—')}: {v.get('codes_count',0)} كود\n" for v in staff]) or "لا يوجد")
        bot.edit_message_text(msg, cid, mid, parse_mode="Markdown", reply_markup=back_kb())

# ═══════════════════════════════════════════════════════════
#  7. Text Handler
# ═══════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid   = message.from_user.id
    cid   = message.chat.id
    text  = message.text.strip() if message.text else ""
    role  = get_role(uid)
    state = user_state.get(uid, {}).get('step')

    if not role:
        bot.reply_to(message, "⚠️ غير مصرح لك."); return

    # تفعيل - الاسم
    if state == 'act_name':
        user_state[uid] = {'step': 'act_months', 'name': text}
        bot.send_message(cid, "📅 الاشتراك كام شهر؟ (اكتب رقم):")

    # تفعيل - الشهور
    elif state == 'act_months':
        try:
            months = int(text)
            if months <= 0: raise ValueError
        except:
            bot.send_message(cid, "❌ اكتب رقم صح."); return
        name    = user_state[uid]['name']
        code    = gen_code()
        expires = (datetime.date.today() + datetime.timedelta(days=30 * months)).strftime("%Y-%m-%d")
        db.collection('students').add({
            "name": name, "activation_code": code,
            "type": "monthly", "banned": False,
            "expires": expires, "device_id": "", "created_by": uid
        })
        inc_staff_count(uid)
        bot.send_message(
            cid,
            f"✅ *تم التفعيل!*\n\n👤 {name}\n🔑 `{code}`\n📅 ينتهي: {expires}",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        user_state.pop(uid, None)

    # تجربة
    elif state == 'trial_name':
        code    = gen_code()
        expires = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        db.collection('students').add({
            "name": text, "activation_code": code,
            "type": "trial", "banned": False,
            "expires": expires, "device_id": "", "created_by": uid
        })
        inc_staff_count(uid)
        bot.send_message(
            cid,
            f"🆓 *تجربة مجانية (ساعة)!*\n\n👤 {text}\n🔑 `{code}`\n⏰ من دلوقتي لمدة ساعة",
            parse_mode="Markdown", reply_markup=back_kb()
        )
        user_state.pop(uid, None)

    # بحث
    elif state == 'search_q':
        query   = text.lower()
        results = [(did, val) for did, val in get_all_students()
                   if query in val.get("name","").lower() or query in val.get("activation_code","")]
        if results:
            for _, val in results:
                status = "🚫 محظور" if val.get("banned") else "✅ نشط"
                bot.send_message(
                    cid,
                    f"👤 *{val.get('name','—')}*\n🔑 `{val.get('activation_code','—')}`\n"
                    f"📅 ينتهي: {val.get('expires','—')}\nالحالة: {status}",
                    parse_mode="Markdown"
                )
        else:
            bot.send_message(cid, "❌ مش لاقي نتايج.")
        user_state.pop(uid, None)
        bot.send_message(cid, "🏠", reply_markup=back_kb())

    # إضافة عضو - اليوزرنيم
    elif state == 'wait_un':
        un       = text.lower().replace("@", "")
        user_doc = db.collection('users_map').document(un).get()
        if not user_doc.exists:
            bot.reply_to(message, "❌ المستخدم لم يفعل البوت بعد. اطلب منه الضغط على /start أولاً.")
            return
        target_id = user_doc.to_dict()['user_id']
        user_state[uid] = {'step': 'wait_role', 't_id': target_id, 't_un': un}
        kb = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("👑 أدمن",  callback_data="set_admin"),
            types.InlineKeyboardButton("👤 موظف", callback_data="set_staff")
        )
        bot.send_message(cid, f"تم العثور على @{un}. اختر الرتبة:", reply_markup=kb)

    else:
        bot.send_message(cid, "🏠 القائمة:", reply_markup=main_kb(uid))

# ═══════════════════════════════════════════════════════════
#  8. Webhook (Vercel)
# ═══════════════════════════════════════════════════════════
@app.route('/' + TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([
        telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    ])
    return "!", 200

@app.route("/")
def index():
    return "✅ Full Mark Bot is Online!", 200

if __name__ == "__main__":
    print("✅ البوت شغّال محلياً!")
    bot.remove_webhook()
    bot.infinity_polling()
