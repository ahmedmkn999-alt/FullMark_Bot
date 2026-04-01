import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request
import os

# إعداد الفايربيز
cred = credentials.Certificate("./full-mark-giza-firebase-adminsdk-fbsvc-d3b5aa294c.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# إعداد البوت والـ Flask
TOKEN = '8296071930:AAGtL5Lr_zCc3DlKToMpRHc0citP7CX2x2s'
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

OWNER_ID = 6188310641
user_state = {}

def get_user_role(user_id):
    if user_id == OWNER_ID: return "owner"
    if db.collection('admins').document(str(user_id)).get().exists: return "admin"
    if db.collection('staff').document(str(user_id)).get().exists: return "staff"
    return None

def main_keyboard(user_id):
    role = get_user_role(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    # أزرار العمليات الأساسية
    buttons = [
        types.InlineKeyboardButton("✨ تفعيل طالب", callback_data="act_std"),
        types.InlineKeyboardButton("🔄 تجديد", callback_data="renew"),
        types.InlineKeyboardButton("📱 تغيير جهاز", callback_data="chg_dev"),
        types.InlineKeyboardButton("🆓 تجربة", callback_data="trial")
    ]
    markup.add(*buttons)
    
    if role in ["owner", "admin"]:
        markup.add(types.InlineKeyboardButton("📊 إحصائيات الموظفين", callback_data="view_stats"))
    
    if role == "owner":
        markup.add(types.InlineKeyboardButton("➕ إضافة (أدمن/موظف)", callback_data="add_mem"))
    
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    role = get_user_role(message.from_user.id)
    if not role:
        bot.reply_to(message, "⚠️ الدخول للمصرح لهم فقط.")
        return
    # تسجيل اليوزرنيم لسهولة الإضافة لاحقاً
    if message.from_user.username:
        db.collection('users_map').document(message.from_user.username.lower()).set({
            'user_id': message.from_user.id,
            'username': message.from_user.username
        })
    bot.send_message(message.chat.id, f"🚀 لوحة تحكم Full Mark\nالرتبة: {role}", reply_markup=main_keyboard(message.from_user.id))

# --- إضافة عضو جديد باليوزرنيم ---
@bot.callback_query_handler(func=lambda call: call.data == "add_mem")
def add_mem_step1(call):
    user_state[call.from_user.id] = {'step': 'wait_username'}
    bot.edit_message_text("ارسل يوزرنيم الشخص (بدون @):", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get('step') == 'wait_username')
def add_mem_step2(message):
    target_un = message.text.lower().replace("@", "")
    user_data = db.collection('users_map').document(target_un).get()
    
    if not user_data.exists:
        bot.reply_to(message, "❌ المستخدم لم يقم بتفعيل البوت (ارسل له رابط البوت ليضغط start أولاً).")
        return

    target_id = user_data.to_dict()['user_id']
    user_state[message.from_user.id] = {'step': 'wait_role', 't_id': target_id, 't_un': target_un}
    
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("أدمن", callback_data="set_admin"),
        types.InlineKeyboardButton("موظف", callback_data="set_staff")
    )
    bot.send_message(message.chat.id, f"تم العثور على @{target_un}. اختر الرتبة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["set_admin", "set_staff"])
def add_mem_final(call):
    state = user_state.get(call.from_user.id)
    col = "admins" if "admin" in call.data else "staff"
    db.collection(col).document(str(state['t_id'])).set({
        'username': state['t_un'],
        'codes_count': 0
    })
    bot.edit_message_text(f"✅ تمت إضافة @{state['t_un']} بنجاح!", call.message.chat.id, call.message.message_id)
    user_state.pop(call.from_user.id)

# --- عرض الإحصائيات ---
@bot.callback_query_handler(func=lambda call: call.data == "view_stats")
def show_stats(call):
    staff = db.collection('staff').stream()
    msg = "📊 إنتاجية الموظفين:\n"
    for s in staff:
        d = s.to_dict()
        msg += f"👤 @{d.get('username')}: {d.get('codes_count', 0)} كود\n"
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=main_keyboard(call.from_user.id))

# --- تتبع الأكواد ---
@bot.callback_query_handler(func=lambda call: call.data == "act_std")
def track_code(call):
    # مثال: عند ضغط الموظف على تفعيل طالب، يزيد عداده
    if get_user_role(call.from_user.id) == "staff":
        db.collection('staff').document(str(call.from_user.id)).update({'codes_count': firestore.Increment(1)})
    bot.answer_callback_query(call.id, "جاري التفعيل...")

# --- جزء الـ Webhook الضروري لـ Vercel ---
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    # هذا الرابط سيظهر لك حالة البوت عند فتحه في المتصفح
    return "Full Mark Bot is Online!", 200
    
