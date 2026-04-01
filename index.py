import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request
import os

# 1. إعداد الفايربيز
cred = credentials.Certificate("./full-mark-giza-firebase-adminsdk-fbsvc-d3b5aa294c.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. إعداد البوت والـ Flask
TOKEN = '8296071930:AAGtL5Lr_zCc3DlKToMpRHc0citP7CX2x2s'
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

OWNER_ID = 6188310641 # الـ ID بتاعك
user_state = {}

# --- دالة التحقق من الرتبة ---
def get_user_role(user_id):
    if user_id == OWNER_ID: return "owner"
    admin_doc = db.collection('admins').document(str(user_id)).get()
    if admin_doc.exists: return "admin"
    staff_doc = db.collection('staff').document(str(user_id)).get()
    if staff_doc.exists: return "staff"
    return None

# --- الكيبورد الرئيسي (حسب الصورة) ---
def main_keyboard(user_id):
    role = get_user_role(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # أزرار الموظفين والأدمن
    btn1 = types.InlineKeyboardButton("✨ تفعيل طالب جديد", callback_data="activate_student")
    btn2 = types.InlineKeyboardButton("🔄 تجديد الاشتراك", callback_data="renew_sub")
    btn3 = types.InlineKeyboardButton("📱 تغيير الجهاز", callback_data="change_device")
    btn4 = types.InlineKeyboardButton("🆓 تجربة ساعة", callback_data="free_trial")
    btn5 = types.InlineKeyboardButton("👀 كل الطلاب", callback_data="all_students")
    btn6 = types.InlineKeyboardButton("🔍 بحث عن طالب", callback_data="search_student")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)

    # أزرار للأدمن والـ Owner فقط
    if role in ["owner", "admin"]:
        markup.add(types.InlineKeyboardButton("💰 كشف الحساب", callback_data="account_report"),
                   types.InlineKeyboardButton("🚫 حظر / فك حظر", callback_data="block_unblock"))
        markup.add(types.InlineKeyboardButton("📊 إحصائيات", callback_data="stats"))

    # أزرار للـ Owner فقط
    if role == "owner":
        markup.add(types.InlineKeyboardButton("➕ إضافة (أدمن/موظف)", callback_data="add_member_init"))
    
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    role = get_user_role(message.from_user.id)
    if not role:
        bot.reply_to(message, "⚠️ عذراً، أنت غير مسجل في النظام.")
        return
    # حفظ اليوزرنيم في قاعدة البيانات لتسهيل الإضافة لاحقاً
    db.collection('users_map').document(message.from_user.username.lower() if message.from_user.username else "none").set({
        'user_id': message.from_user.id,
        'username': message.from_user.username
    })
    bot.send_message(message.chat.id, f"أهلاً بك في لوحة تحكم Full Mark\nرتبتك: {role}", reply_markup=main_keyboard(message.from_user.id))

# --- منطق الإضافة بالـ Username ---
@bot.callback_query_handler(func=lambda call: call.data == "add_member_init")
def add_member_start(call):
    user_state[call.from_user.id] = {'step': 'wait_member_username'}
    bot.edit_message_text("ارسل الـ Username الخاص بالشخص (بدون @):", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get('step') == 'wait_member_username')
def process_username(message):
    target_username = message.text.lower().replace("@", "")
    # البحث عن الـ ID من خلال اليوزرنيم (لازم الشخص يكون كلم البوت مرة قبل كدة)
    user_data = db.collection('users_map').document(target_username).get()
    
    if not user_data.exists:
        bot.reply_to(message, "❌ لم أجد هذا المستخدم. اطلب منه أن يرسل /start للبوت أولاً.")
        return

    target_id = user_data.to_dict()['user_id']
    user_state[message.from_user.id] = {'step': 'wait_member_role', 'target_id': target_id, 'target_user': target_username}
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("مدير (Admin)", callback_data="role_admin"),
               types.InlineKeyboardButton("موظف (Staff)", callback_data="role_staff"))
    bot.send_message(message.chat.id, f"تم العثور على {target_username}. اختر الرتبة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("role_"))
def finalize_role(call):
    state = user_state.get(call.from_user.id)
    role_type = "admins" if "admin" in call.data else "staff"
    
    db.collection(role_type).document(str(state['target_id'])).set({
        'username': state['target_user'],
        'codes_count': 0,
        'added_by': call.from_user.id
    })
    bot.edit_message_text(f"✅ تمت إضافة {state['target_user']} بنجاح كـ {role_type[:-1]}!", call.message.chat.id, call.message.message_id)
    user_state.pop(call.from_user.id)

# --- تتبع الأكواد في الإحصائيات ---
@bot.callback_query_handler(func=lambda call: call.data == "stats")
def show_stats(call):
    staff_members = db.collection('staff').stream()
    report = "📊 إنتاجية الموظفين:\n"
    for member in staff_members:
        data = member.to_dict()
        report += f"👤 @{data.get('username')}: {data.get('codes_count', 0)} كود\n"
    
    back = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    bot.edit_message_text(report, call.message.chat.id, call.message.message_id, reply_markup=back)

# --- تفعيل الطالب (مثال لتحديث العداد) ---
@bot.callback_query_handler(func=lambda call: call.data == "activate_student")
def activate_logic(call):
    # بعد إتمام عملية التفعيل بنجاح، نحدث عداد الموظف
    role = get_user_role(call.from_user.id)
    if role == "staff":
        staff_ref = db.collection('staff').document(str(call.from_user.id))
        staff_ref.update({'codes_count': firestore.Increment(1)})
    
    bot.answer_callback_query(call.id, "جاري تفعيل الطالب...")

# --- مسار الـ Webhook (مهم جداً لفيرسال) ---
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    # هنا تحط رابط المشروع بتاعك بعد الرفـع
    # bot.set_webhook(url="https://your-project.vercel.app/" + TOKEN)
    return "Full Mark Bot is Running!", 200
