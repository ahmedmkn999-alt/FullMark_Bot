import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request
import os

# --- 1. إعداد الفايربيز ---
cred = credentials.Certificate("./full-mark-giza-firebase-adminsdk-fbsvc-d3b5aa294c.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- 2. إعداد البوت والـ Flask ---
TOKEN = '8296071930:AAGtL5Lr_zCc3DlKToMpRHc0citP7CX2x2s'
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

OWNER_ID = 6188310641
user_state = {}

# دالة التأكد من الرتبة
def get_role(uid):
    if uid == OWNER_ID: return "owner"
    if db.collection('admins').document(str(uid)).get().exists: return "admin"
    if db.collection('staff').document(str(uid)).get().exists: return "staff"
    return None

# --- 3. الكيبورد الرئيسي ---
def main_kb(uid):
    role = get_role(uid)
    markup = types.InlineKeyboardMarkup(row_width=2)
    # أزرار للكل (أدمن وموظفين)
    markup.add(
        types.InlineKeyboardButton("✨ تفعيل طالب", callback_data="act_std"),
        types.InlineKeyboardButton("🔄 تجديد الاشتراك", callback_data="renew"),
        types.InlineKeyboardButton("📱 تغيير جهاز", callback_data="chg_dev"),
        types.InlineKeyboardButton("🆓 تجربة ساعة", callback_data="trial"),
        types.InlineKeyboardButton("🔍 بحث عن طالب", callback_data="search")
    )
    # أزرار للأدمن والـ Owner
    if role in ["owner", "admin"]:
        markup.add(types.InlineKeyboardButton("📊 إحصائيات الموظفين", callback_data="stats"))
    # أزرار للـ Owner فقط
    if role == "owner":
        markup.add(types.InlineKeyboardButton("➕ إضافة (أدمن/موظف)", callback_data="add_mem"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    role = get_role(uid)
    if not role:
        bot.reply_to(message, "⚠️ الدخول للمصرح لهم فقط.")
        return
    # تسجيل البيانات لسهولة الإضافة باليوزرنيم لاحقاً
    if message.from_user.username:
        db.collection('users_map').document(message.from_user.username.lower()).set({
            'user_id': uid, 'username': message.from_user.username
        })
    bot.send_message(message.chat.id, f"🚀 لوحة تحكم Full Mark\nالرتبة الحالية: {role}", reply_markup=main_kb(uid))

# --- 4. منطق الإضافة باليوزرنيم ---
@bot.callback_query_handler(func=lambda c: c.data == "add_mem")
def add_init(call):
    user_state[call.from_user.id] = {'step': 'wait_un'}
    bot.edit_message_text("ارسل يوزرنيم الشخص (بدون @):", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get('step') == 'wait_un')
def add_process(message):
    un = message.text.lower().replace("@", "")
    user_data = db.collection('users_map').document(un).get()
    if not user_data.exists:
        bot.reply_to(message, "❌ المستخدم لم يفعل البوت. اطلب منه الضغط على /start أولاً.")
        return
    target_id = user_data.to_dict()['user_id']
    user_state[message.from_user.id].update({'step': 'wait_role', 't_id': target_id, 't_un': un})
    kb = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("أدمن", callback_data="set_admin"),
        types.InlineKeyboardButton("موظف", callback_data="set_staff")
    )
    bot.send_message(message.chat.id, f"تم العثور على @{un}. اختر الرتبة:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ["set_admin", "set_staff"])
def add_final(call):
    st = user_state.get(call.from_user.id)
    col = "admins" if "admin" in call.data else "staff"
    db.collection(col).document(str(st['t_id'])).set({'username': st['t_un'], 'codes_count': 0})
    bot.edit_message_text(f"✅ تمت إضافة @{st['t_un']} بنجاح!", call.message.chat.id, call.message.message_id)
    user_state.pop(call.from_user.id)

# --- 5. عرض الإحصائيات وتتبع الأكواد ---
@bot.callback_query_handler(func=lambda c: c.data == "stats")
def show_stats(call):
    staff = db.collection('staff').stream()
    msg = "📊 إنتاجية الموظفين:\n" + "".join([f"👤 @{s.to_dict().get('username')}: {s.to_dict().get('codes_count', 0)} كود\n" for s in staff])
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=main_kb(call.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data == "act_std")
def handle_act(call):
    if get_role(call.from_user.id) == "staff":
        db.collection('staff').document(str(call.from_user.id)).update({'codes_count': firestore.Increment(1)})
    bot.answer_callback_query(call.id, "جاري تفعيل الطالب...")

# --- 6. إعدادات Vercel و الـ Webhook ---
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route("/")
def webhook():
    return "Full Mark Bot is Online!", 200
    
