import telebot
import pyrebase
import datetime
import os
from flask import Flask, request
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)

# ============================================================
# ⚙️ الإعدادات
# ============================================================
BOT_TOKEN = "8296071930:AAGtL5Lr_zCc3DlKToMpRHc0citP7CX2x2s"
OWNER_ID  = None

firebase_config = {
    "apiKey": "AIzaSyB3-X8J3zZ9_5_9_5_9_5_9_5_9_5_9_5",
    "authDomain": "tanawe-d33bd.firebaseapp.com",
    "projectId": "tanawe-d33bd",
    "storageBucket": "tanawe-d33bd.appspot.com",
    "messagingSenderId": "8296071930",
    "appId": "1:8296071930:web:7f6d5e4d3c2b1a",
    "databaseURL": "https://tanawe-d33bd-default-rtdb.firebaseio.com/"
}

firebase = pyrebase.initialize_app(firebase_config)
db  = firebase.database()
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

user_state = {}
user_data  = {}

# ════════════════════════════════════════════════════════════
# 🔐 نظام الصلاحيات
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
    cid_str = str(cid)
    if OWNER_ID and cid_str == str(OWNER_ID):
        return "owner"
    try:
        emps = db.child("employees").get()
        if emps and emps.val():
            for e in emps.each():
                if str(e.val().get("user_id", "")) == cid_str:
                    return "employee"
    except:
        pass
    return "none"

def is_allowed(cid):
    return get_role(cid) in ("owner", "employee")

# ════════════════════════════════════════════════════════════
# 🔑 توليد كود التفعيل
# ════════════════════════════════════════════════════════════
def generate_code():
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ════════════════════════════════════════════════════════════
# 📱 لوحة التحكم الرئيسية
# ════════════════════════════════════════════════════════════
def main_menu(cid):
    role = get_role(cid)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✨ تفعيل طالب جديد", callback_data="new_student"),
        InlineKeyboardButton("🔄 تجديد الاشتراك",  callback_data="renew"),
    )
    kb.add(
        InlineKeyboardButton("🆓 تجربة ساعة",      callback_data="free_trial"),
        InlineKeyboardButton("📱 تغيير الجهاز",    callback_data="change_device"),
    )
    kb.add(
        InlineKeyboardButton("🔍 بحث عن طالب",    callback_data="search"),
        InlineKeyboardButton("👀 كل الطلاب",       callback_data="view_all"),
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
    kb.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main"))
    return kb

def back_btn():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="main"))
    return kb

# ════════════════════════════════════════════════════════════
# 🚀 أمر /start
# ════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def start(message):
    global OWNER_ID
    cid = message.chat.id
    load_owner()
    if OWNER_ID is None:
        OWNER_ID = cid
        db.child("settings").update({"owner_id": cid})

    if not is_allowed(cid):
        bot.send_message(cid, "⛔ عذراً، أنت غير مسجل كمدير أو موظف.")
        return

    role_ar = "مدير" if get_role(cid) == "owner" else "موظف"
    bot.send_message(
        cid,
        f"🚀 أهلاً بك في لوحة تحكم *Full Mark*\nرتبتك: {role_ar}",
        parse_mode="Markdown",
        reply_markup=main_menu(cid)
    )

# ════════════════════════════════════════════════════════════
# 🎛️ معالج الأزرار الكاملة
# ════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    cid  = call.message.chat.id
    mid  = call.message.message_id
    data = call.data

    if not is_allowed(cid):
        bot.answer_callback_query(call.id, "⛔ غير مصرح لك!")
        return

    bot.answer_callback_query(call.id)

    # ── القائمة الرئيسية ──────────────────────────────────
    if data == "main":
        user_state.pop(cid, None)
        user_data.pop(cid, None)
        role_ar = "مدير" if get_role(cid) == "owner" else "موظف"
        bot.edit_message_text(
            f"🚀 لوحة تحكم *Full Mark* | رتبتك: {role_ar}",
            cid, mid,
            parse_mode="Markdown",
            reply_markup=main_menu(cid)
        )

    # ── تفعيل طالب جديد ──────────────────────────────────
    elif data == "new_student":
        user_state[cid] = "await_name"
        user_data[cid]  = {}
        bot.edit_message_text(
            "✨ *تفعيل طالب جديد*\n\n👤 أرسل اسم الطالب:",
            cid, mid,
            parse_mode="Markdown",
            reply_markup=back_btn()
        )

    # ── تجديد الاشتراك ───────────────────────────────────
    elif data == "renew":
        user_state[cid] = "renew_code"
        user_data[cid]  = {}
        bot.edit_message_text(
            "🔄 *تجديد الاشتراك*\n\n🔑 أرسل كود التفعيل الخاص بالطالب:",
            cid, mid,
            parse_mode="Markdown",
            reply_markup=back_btn()
        )

    # ── تجربة ساعة ───────────────────────────────────────
    elif data == "free_trial":
        user_state[cid] = "trial_name"
        user_data[cid]  = {}
        bot.edit_message_text(
            "🆓 *تجربة ساعة مجانية*\n\n👤 أرسل اسم الطالب:",
            cid, mid,
            parse_mode="Markdown",
            reply_markup=back_btn()
        )

    # ── تغيير الجهاز ─────────────────────────────────────
    elif data == "change_device":
        user_state[cid] = "change_device_code"
        user_data[cid]  = {}
        bot.edit_message_text(
            "📱 *تغيير الجهاز*\n\n🔑 أرسل كود التفعيل الخاص بالطالب:",
            cid, mid,
            parse_mode="Markdown",
            reply_markup=back_btn()
        )

    # ── بحث عن طالب ──────────────────────────────────────
    elif data == "search":
        user_state[cid] = "search_student"
        bot.edit_message_text(
            "🔍 *بحث عن طالب*\n\nأرسل اسم الطالب أو كود تفعيله:",
            cid, mid,
            parse_mode="Markdown",
            reply_markup=back_btn()
        )

    # ── كل الطلاب ────────────────────────────────────────
    elif data == "view_all":
        try:
            all_s = db.child("students").get()
            if all_s.val():
                msg = "👥 *قائمة الطلاب:*\n\n"
                count = 0
                for s in all_s.each():
                    v = s.val()
                    exp = v.get('expiry', '—')
                    banned = " 🚫" if v.get('banned') else ""
                    msg += f"• {v.get('name', '—')} | `{v.get('activation_code', '—')}` | {exp}{banned}\n"
                    count += 1
                msg += f"\n📊 الإجمالي: {count} طالب"
                bot.edit_message_text(msg, cid, mid, parse_mode="Markdown", reply_markup=back_btn())
            else:
                bot.edit_message_text("📭 لا يوجد طلاب مسجلين بعد.", cid, mid, reply_markup=back_btn())
        except Exception as e:
            bot.edit_message_text(f"❌ خطأ في الاتصال بقاعدة البيانات.\n`{e}`", cid, mid, parse_mode="Markdown", reply_markup=back_btn())

    # ── حظر / فك حظر (مدير فقط) ──────────────────────────
    elif data == "ban_menu":
        if get_role(cid) != "owner":
            bot.answer_callback_query(call.id, "⛔ للمدير فقط!")
            return
        user_state[cid] = "ban_code"
        bot.edit_message_text(
            "🚫 *حظر / فك حظر طالب*\n\n🔑 أرسل كود التفعيل الخاص بالطالب:",
            cid, mid,
            parse_mode="Markdown",
            reply_markup=back_btn()
        )

    # ── كشف الحساب (مدير فقط) ────────────────────────────
    elif data == "account":
        if get_role(cid) != "owner":
            return
        try:
            all_s = db.child("students").get()
            total = 0
            trial_count = 0
            active_count = 0
            if all_s.val():
                for s in all_s.each():
                    v = s.val()
                    if v.get('is_trial'):
                        trial_count += 1
                    else:
                        active_count += 1
                        total += float(v.get('paid', 0))
            msg = (
                f"💰 *كشف الحساب*\n\n"
                f"✅ طلاب مفعلين: {active_count}\n"
                f"🆓 تجارب مجانية: {trial_count}\n"
                f"💵 الإيرادات: {total:.0f} جنيه"
            )
            bot.edit_message_text(msg, cid, mid, parse_mode="Markdown", reply_markup=back_btn())
        except Exception as e:
            bot.edit_message_text(f"❌ خطأ: `{e}`", cid, mid, parse_mode="Markdown", reply_markup=back_btn())

    # ── إحصائيات (مدير فقط) ──────────────────────────────
    elif data == "stats":
        if get_role(cid) != "owner":
            return
        try:
            all_s = db.child("students").get()
            total = 0
            active = 0
            banned = 0
            expired = 0
            now = datetime.date.today()
            if all_s.val():
                for s in all_s.each():
                    v = s.val()
                    total += 1
                    if v.get('banned'):
                        banned += 1
                    else:
                        try:
                            exp = datetime.datetime.strptime(v.get('expiry', ''), "%Y-%m-%d").date()
                            if exp >= now:
                                active += 1
                            else:
                                expired += 1
                        except:
                            active += 1
            msg = (
                f"📊 *إحصائيات البوت*\n\n"
                f"👥 إجمالي الطلاب: {total}\n"
                f"✅ نشطين: {active}\n"
                f"⏰ منتهي الاشتراك: {expired}\n"
                f"🚫 محظورين: {banned}"
            )
            bot.edit_message_text(msg, cid, mid, parse_mode="Markdown", reply_markup=back_btn())
        except Exception as e:
            bot.edit_message_text(f"❌ خطأ: `{e}`", cid, mid, parse_mode="Markdown", reply_markup=back_btn())

    # ── إضافة موظف (مدير فقط) ────────────────────────────
    elif data == "add_employee":
        if get_role(cid) != "owner":
            return
        user_state[cid] = "add_emp_id"
        bot.edit_message_text(
            "➕ *إضافة موظف جديد*\n\n🆔 أرسل الـ Telegram ID الخاص بالموظف:",
            cid, mid,
            parse_mode="Markdown",
            reply_markup=back_btn()
        )

    # ── عرض الموظفين (مدير فقط) ──────────────────────────
    elif data == "view_employees":
        if get_role(cid) != "owner":
            return
        try:
            emps = db.child("employees").get()
            if emps.val():
                msg = "👮 *قائمة الموظفين:*\n\n"
                for e in emps.each():
                    v = e.val()
                    msg += f"• {v.get('name', 'بدون اسم')} | ID: `{v.get('user_id', '—')}`\n"
                bot.edit_message_text(msg, cid, mid, parse_mode="Markdown", reply_markup=back_btn())
            else:
                bot.edit_message_text("📭 لا يوجد موظفين مسجلين.", cid, mid, reply_markup=back_btn())
        except Exception as e:
            bot.edit_message_text(f"❌ خطأ: `{e}`", cid, mid, parse_mode="Markdown", reply_markup=back_btn())

    # ── تأكيد الحذف ──────────────────────────────────────
    elif data.startswith("confirm_ban_"):
        code = data.replace("confirm_ban_", "")
        try:
            all_s = db.child("students").get()
            for s in all_s.each():
                v = s.val()
                if v.get("activation_code") == code:
                    new_status = not bool(v.get("banned", False))
                    db.child("students").child(s.key()).update({"banned": new_status})
                    status_txt = "🚫 تم الحظر" if new_status else "✅ تم فك الحظر"
                    bot.edit_message_text(
                        f"{status_txt} للطالب: *{v.get('name')}*",
                        cid, mid,
                        parse_mode="Markdown",
                        reply_markup=back_btn()
                    )
                    return
            bot.edit_message_text("❌ الكود غير موجود.", cid, mid, reply_markup=back_btn())
        except Exception as e:
            bot.edit_message_text(f"❌ خطأ: `{e}`", cid, mid, parse_mode="Markdown", reply_markup=back_btn())

# ════════════════════════════════════════════════════════════
# 💬 معالج النصوص (حالات الإدخال)
# ════════════════════════════════════════════════════════════
@bot.message_handler(content_types=['text'])
def text_handler(message):
    cid  = message.chat.id
    text = message.text.strip()

    if not is_allowed(cid):
        return

    state = user_state.get(cid)

    # ── لا يوجد حالة ─────────────────────────────────────
    if not state:
        bot.send_message(cid, "استخدم /start للوصول للقائمة الرئيسية.")
        return

    # ══ تفعيل طالب جديد ══════════════════════════════════
    if state == "await_name":
        user_data[cid]['name'] = text
        user_state[cid] = "await_months"
        bot.send_message(cid, "📅 كم شهر الاشتراك؟ (أرسل رقم)")

    elif state == "await_months":
        if not text.isdigit():
            bot.send_message(cid, "❌ أرسل رقم صحيح فقط.")
            return
        user_data[cid]['months'] = int(text)
        user_state[cid] = "await_price"
        bot.send_message(cid, "💵 كم المبلغ المدفوع؟ (أرسل رقم)")

    elif state == "await_price":
        if not text.replace('.', '', 1).isdigit():
            bot.send_message(cid, "❌ أرسل رقم صحيح فقط.")
            return
        months = user_data[cid]['months']
        expiry = (datetime.date.today() + datetime.timedelta(days=30 * months)).strftime("%Y-%m-%d")
        code   = generate_code()
        student = {
            "name":            user_data[cid]['name'],
            "activation_code": code,
            "expiry":          expiry,
            "paid":            float(text),
            "is_trial":        False,
            "banned":          False,
            "added_by":        str(cid),
            "device_id":       ""
        }
        try:
            db.child("students").push(student)
            bot.send_message(
                cid,
                f"✅ *تم تفعيل الطالب بنجاح!*\n\n"
                f"👤 الاسم: {student['name']}\n"
                f"🔑 الكود: `{code}`\n"
                f"📅 تنتهي في: {expiry}\n"
                f"💵 المدفوع: {text} جنيه",
                parse_mode="Markdown",
                reply_markup=main_menu(cid)
            )
        except Exception as e:
            bot.send_message(cid, f"❌ خطأ في الحفظ: `{e}`", parse_mode="Markdown")
        user_state.pop(cid, None)
        user_data.pop(cid, None)

    # ══ تجديد الاشتراك ════════════════════════════════════
    elif state == "renew_code":
        try:
            all_s = db.child("students").get()
            found_key = None
            found_val = None
            if all_s.val():
                for s in all_s.each():
                    if s.val().get("activation_code") == text:
                        found_key = s.key()
                        found_val = s.val()
                        break
            if not found_key:
                bot.send_message(cid, "❌ الكود غير موجود.", reply_markup=back_btn())
                user_state.pop(cid, None)
                return
            user_data[cid]['key']  = found_key
            user_data[cid]['val']  = found_val
            user_data[cid]['code'] = text
            user_state[cid] = "renew_months"
            bot.send_message(cid, f"✅ تم إيجاد الطالب: *{found_val.get('name')}*\n📅 كم شهر تريد تجديده؟", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(cid, f"❌ خطأ: `{e}`", parse_mode="Markdown")
            user_state.pop(cid, None)

    elif state == "renew_months":
        if not text.isdigit():
            bot.send_message(cid, "❌ أرسل رقم صحيح فقط.")
            return
        months = int(text)
        old_expiry_str = user_data[cid]['val'].get('expiry', '')
        try:
            old_date = datetime.datetime.strptime(old_expiry_str, "%Y-%m-%d").date()
            base = max(old_date, datetime.date.today())
        except:
            base = datetime.date.today()
        new_expiry = (base + datetime.timedelta(days=30 * months)).strftime("%Y-%m-%d")
        db.child("students").child(user_data[cid]['key']).update({"expiry": new_expiry})
        bot.send_message(
            cid,
            f"🔄 *تم تجديد الاشتراك بنجاح!*\n\n"
            f"👤 {user_data[cid]['val'].get('name')}\n"
            f"📅 الانتهاء الجديد: {new_expiry}",
            parse_mode="Markdown",
            reply_markup=main_menu(cid)
        )
        user_state.pop(cid, None)
        user_data.pop(cid, None)

    # ══ تجربة ساعة ════════════════════════════════════════
    elif state == "trial_name":
        code   = generate_code()
        expiry = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        student = {
            "name":            text,
            "activation_code": code,
            "expiry":          expiry,
            "paid":            0,
            "is_trial":        True,
            "banned":          False,
            "added_by":        str(cid),
            "device_id":       ""
        }
        try:
            db.child("students").push(student)
            bot.send_message(
                cid,
                f"🆓 *تم إنشاء تجربة مجانية!*\n\n"
                f"👤 الاسم: {text}\n"
                f"🔑 الكود: `{code}`\n"
                f"⏰ صالحة لمدة ساعة حتى: {expiry}",
                parse_mode="Markdown",
                reply_markup=main_menu(cid)
            )
        except Exception as e:
            bot.send_message(cid, f"❌ خطأ: `{e}`", parse_mode="Markdown")
        user_state.pop(cid, None)
        user_data.pop(cid, None)

    # ══ تغيير الجهاز ══════════════════════════════════════
    elif state == "change_device_code":
        try:
            all_s = db.child("students").get()
            found_key = None
            found_val = None
            if all_s.val():
                for s in all_s.each():
                    if s.val().get("activation_code") == text:
                        found_key = s.key()
                        found_val = s.val()
                        break
            if not found_key:
                bot.send_message(cid, "❌ الكود غير موجود.", reply_markup=back_btn())
                user_state.pop(cid, None)
                return
            db.child("students").child(found_key).update({"device_id": ""})
            bot.send_message(
                cid,
                f"📱 *تم تغيير الجهاز بنجاح!*\n\n"
                f"👤 الطالب: {found_val.get('name')}\n"
                f"✅ يمكنه الآن تسجيل الدخول من جهاز جديد.",
                parse_mode="Markdown",
                reply_markup=main_menu(cid)
            )
        except Exception as e:
            bot.send_message(cid, f"❌ خطأ: `{e}`", parse_mode="Markdown")
        user_state.pop(cid, None)
        user_data.pop(cid, None)

    # ══ بحث عن طالب ═══════════════════════════════════════
    elif state == "search_student":
        try:
            all_s = db.child("students").get()
            results = []
            if all_s.val():
                for s in all_s.each():
                    v = s.val()
                    if text.lower() in v.get("name", "").lower() or text == v.get("activation_code", ""):
                        results.append(v)
            if results:
                msg = f"🔍 *نتائج البحث عن: {text}*\n\n"
                for v in results:
                    banned = " 🚫 محظور" if v.get("banned") else ""
                    trial  = " 🆓 تجربة" if v.get("is_trial") else ""
                    msg += (
                        f"👤 {v.get('name')}{banned}{trial}\n"
                        f"🔑 الكود: `{v.get('activation_code')}`\n"
                        f"📅 الانتهاء: {v.get('expiry', '—')}\n"
                        f"💵 المدفوع: {v.get('paid', 0)} جنيه\n\n"
                    )
                bot.send_message(cid, msg, parse_mode="Markdown", reply_markup=main_menu(cid))
            else:
                bot.send_message(cid, "❌ لم يتم العثور على أي طالب.", reply_markup=main_menu(cid))
        except Exception as e:
            bot.send_message(cid, f"❌ خطأ: `{e}`", parse_mode="Markdown")
        user_state.pop(cid, None)

    # ══ حظر / فك حظر ══════════════════════════════════════
    elif state == "ban_code":
        try:
            all_s = db.child("students").get()
            found_key = None
            found_val = None
            if all_s.val():
                for s in all_s.each():
                    if s.val().get("activation_code") == text:
                        found_key = s.key()
                        found_val = s.val()
                        break
            if not found_key:
                bot.send_message(cid, "❌ الكود غير موجود.", reply_markup=back_btn())
                user_state.pop(cid, None)
                return
            current = bool(found_val.get("banned", False))
            action  = "فك الحظر عن" if current else "حظر"
            emoji   = "✅" if current else "🚫"
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton(f"{emoji} تأكيد {action}", callback_data=f"confirm_ban_{text}"),
                InlineKeyboardButton("❌ إلغاء", callback_data="main")
            )
            bot.send_message(
                cid,
                f"هل تريد *{action}* الطالب: *{found_val.get('name')}*؟",
                parse_mode="Markdown",
                reply_markup=kb
            )
        except Exception as e:
            bot.send_message(cid, f"❌ خطأ: `{e}`", parse_mode="Markdown")
        user_state.pop(cid, None)

    # ══ إضافة موظف ════════════════════════════════════════
    elif state == "add_emp_id":
        if not text.isdigit():
            bot.send_message(cid, "❌ أرسل رقم ID صحيح فقط.")
            return
        user_data[cid]['emp_id'] = text
        user_state[cid] = "add_emp_name"
        bot.send_message(cid, "👤 أرسل اسم الموظف:")

    elif state == "add_emp_name":
        emp_id = user_data[cid]['emp_id']
        try:
            db.child("employees").push({"user_id": emp_id, "name": text})
            bot.send_message(
                cid,
                f"✅ *تم إضافة الموظف بنجاح!*\n\n"
                f"👤 الاسم: {text}\n"
                f"🆔 ID: `{emp_id}`",
                parse_mode="Markdown",
                reply_markup=main_menu(cid)
            )
        except Exception as e:
            bot.send_message(cid, f"❌ خطأ: `{e}`", parse_mode="Markdown")
        user_state.pop(cid, None)
        user_data.pop(cid, None)

# ════════════════════════════════════════════════════════════
# 🌐 Webhook (Vercel)
# ════════════════════════════════════════════════════════════
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    # bot.set_webhook(url='https://YOUR_APP_URL.vercel.app/' + BOT_TOKEN)
    return "<h1>Bot is active!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
