const { Telegraf, Markup } = require('telegraf');
const admin = require('firebase-admin');

// 1. ربط مفتاح الفايربيز (زي ما طلبت بالظبط)
const serviceAccount = require("./full-mark-giza-firebase-adminsdk-fbsvc-d3b5aa294c.json");

if (!admin.apps.length) {
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccount)
    });
}

const db = admin.firestore();

// 2. التوكن الصحيح بتاعك بعد تصحيح الحروف
const bot = new Telegraf('8296071930:AAGtL5Lr_zCc3DlKToMpRHc0citP7CX2x2s'); 

// 3. الـ ID الخاص بيك لفتح الصلاحيات
const OWNER_ID = 6188310641; 
let userState = {};

const generateCode = () => Math.floor(100000 + Math.random() * 900000).toString();

async function isAuthorized(userId) {
    if (userId === OWNER_ID) return true;
    const doc = await db.collection('admins').doc(userId.toString()).get();
    return doc.exists;
}

// دالة إنشاء القائمة الرئيسية
const getMainKeyboard = async (userId) => {
    let buttons = [
        [Markup.button.callback('✨ تفعيل طالب جديد', 'ask_name_month'), Markup.button.callback('🔄 تجديد الاشتراك', 'renew_init')],
        [Markup.button.callback('📱 تغيير الجهاز', 'reset_device_init'), Markup.button.callback('🆓 عمل تجربة مجانية', 'ask_name_trial')],
        [Markup.button.callback('📝 تحديث بيانات طالب', 'edit_student_init'), Markup.button.callback('👤 شوف بيانات الطالب', 'view_info_init')]
    ];
    if (userId === OWNER_ID) {
        buttons.push([Markup.button.callback('➕ إضافة موظف جديد', 'add_admin_init')]);
    }
    return Markup.inlineKeyboard(buttons);
};

// إعداد زرار "Menu" أو الـ "Start"
bot.telegram.setMyCommands([
    { command: 'start', description: '🚀 يلا بينا ابدأ التشغيل' }
]);

// --- القائمة الرئيسية ---
bot.start(async (ctx) => {
    const userId = ctx.from.id;
    if (!(await isAuthorized(userId))) return ctx.reply("⚠️ غير مصرح لك يا أحمد.");

    const keyboard = await getMainKeyboard(userId);
    ctx.reply(`✨ مـرحـبـاً بـك فـي لـوحـة تـحـكـم Full Mark 🚀\n\nاختر العملية المطلوبة من الأسفل:`, keyboard);
});

// زرار الرجوع للقائمة الرئيسية
const backButton = [Markup.button.callback('🔙 الرجوع للقائمة الرئيسية', 'main_menu')];

bot.action('main_menu', async (ctx) => {
    const userId = ctx.from.id;
    const keyboard = await getMainKeyboard(userId);
    ctx.editMessageText(`✨ مـرحـبـاً بـك فـي لـوحـة تـحـكـم Full Mark 🚀\n\nاختر العملية المطلوبة:`, keyboard);
    delete userState[userId];
});

// --- تعديل الردود لإضافة زرار الرجوع ---
bot.action('ask_name_month', (ctx) => {
    userState[ctx.from.id] = { step: 'waiting_for_name', type: 'monthly' };
    ctx.reply('\n✍️ ابـعث "اسـم الطـالب" الجديد:\n\n', Markup.inlineKeyboard([backButton]));
});

bot.action('ask_name_trial', (ctx) => {
    userState[ctx.from.id] = { step: 'waiting_for_name', type: 'trial' };
    ctx.reply('\n✍️ ابـعث "اسـم الطـالب" للتجربة المجانية:\n\n', Markup.inlineKeyboard([backButton]));
});

// إضافة زرار الرجوع في كل الـ actions
bot.action('add_admin_init', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userState[ctx.from.id] = { step: 'waiting_for_admin_id' };
    ctx.reply('\n👤 ابعت الـ ID الخاص بالموظف الجديد:', Markup.inlineKeyboard([backButton]));
});

// --- استقبال النصوص ---
bot.on('text', async (ctx) => {
    const userId = ctx.from.id;
    const state = userState[userId];
    if (!state) return;

    const text = ctx.text;

    if (state.step === 'waiting_for_admin_id' && userId === OWNER_ID) {
        await db.collection('admins').doc(text).set({ addedBy: OWNER_ID, createdAt: admin.firestore.FieldValue.serverTimestamp() });
        ctx.reply('✅ تم إضافة الموظف بنجاح.', Markup.inlineKeyboard([backButton]));
        delete userState[userId];
    } else if (state.step === 'waiting_for_name') {
        userState[userId].studentName = text;
        userState[userId].step = 'waiting_for_major';
        ctx.reply(`\nتـم تسجيل الاسم: ${text}\n\nاخـتار شـعبة الطـالـب:`, 
            Markup.inlineKeyboard([
                [Markup.button.callback('📚 أدبي', 'major_adabi'), Markup.button.callback('🧪 علمي علوم', 'major_oloom')],
                [Markup.button.callback('📐 علمي رياضة', 'major_رياضة')],
                backButton
            ])
        );
    }
});

// --- معالجة أزرار الشعبة ---
const mKeys = { 'major_adabi': 'أدبي', 'major_oloom': 'علمي علوم', 'major_رياضة': 'علمي رياضة' };
Object.keys(mKeys).forEach(k => {
    bot.action(k, async (ctx) => {
        const s = userState[ctx.from.id];
        if (!s) return;
        const code = generateCode();
        const data = { code, studentName: s.studentName, major: mKeys[k], type: s.type, isUsed: false, deviceId: null, createdAt: admin.firestore.FieldValue.serverTimestamp() };
        await db.collection('student_codes').doc(code).set(data);
        
        // إرسال الرسالة
        const title = s.type === 'trial' ? 'خلاص! اتعملت التجربة المجانية بنجاح' : 'خلاص! تم تفعيل اشتراك الشهر بنجاح';
        const message = `✅ ${title}\n\n━━━━━━━━━━━━━━━━━━━━\n👤 **الاسم:** ${data.studentName}\n📖 **الشعبة:** ${data.major}\n🎫 **الكود:** \`${data.code}\`\n━━━━━━━━━━━━━━━━━━━━`;
        
        ctx.replyWithMarkdown(message, Markup.inlineKeyboard([backButton]));
        delete userState[ctx.from.id];
    });
});

// --- معالجة الأزرار الفارغة عشان البوت ميهنجش ---
bot.action(['renew_init', 'reset_device_init', 'edit_student_init', 'view_info_init'], (ctx) => {
    ctx.reply('⚠️ هذه الميزة سيتم تفعيلها قريباً.', Markup.inlineKeyboard([backButton]));
});

// --- 4. التصدير الخاص بـ Vercel ---
module.exports = async (req, res) => {
    try {
        if (req.method === 'POST') {
            await bot.handleUpdate(req.body);
        }
        res.status(200).send('OK');
    } catch (err) {
        console.error(err);
        res.status(500).send('Error');
    }
};
