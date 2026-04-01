const { Telegraf, Markup } = require('telegraf');
const admin = require('firebase-admin');

// 1. ربط مفتاح الفايربيز (خليته زي ما هو لطلبك)
const serviceAccount = require("./full-mark-giza-firebase-adminsdk-fbsvc-d3b5aa294c.json");

if (!admin.apps.length) {
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccount)
    });
}

const db = admin.firestore();

// --- تعديل البيانات بناءً على صورك ---
const BOT_TOKEN = '8296071930:AAGtL5Lr_zCc3DlKToMpRHc0citP7CX2x2s'; // توكن بوتك الحقيقي
const OWNER_ID = 6188310641; // الـ ID بتاعك كمالك للبوت
const bot = new Telegraf(BOT_TOKEN);

let userState = {};

const generateCode = () => Math.floor(100000 + Math.random() * 900000).toString();

async function isAuthorized(userId) {
    if (userId === OWNER_ID) return true;
    const doc = await db.collection('admins').doc(userId.toString()).get();
    return doc.exists;
}

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

bot.telegram.setMyCommands([{ command: 'start', description: '🚀 يلا بينا ابدأ التشغيل' }]);

bot.start(async (ctx) => {
    const userId = ctx.from.id;
    if (!(await isAuthorized(userId))) return ctx.reply("⚠️ غير مصرح لك يا أحمد، تواصل مع المدير.");

    const keyboard = await getMainKeyboard(userId);
    ctx.reply(`✨ مـرحـبـاً بـك فـي لـوحـة تـحـكـم Full Mark 🚀\n\nأهلاً يا مبرمج Full Mark، اختر العملية:`, keyboard);
});

const backButton = Markup.button.callback('🔙 الرجوع للقائمة الرئيسية', 'main_menu');

bot.action('main_menu', async (ctx) => {
    const userId = ctx.from.id;
    const keyboard = await getMainKeyboard(userId);
    ctx.editMessageText(`✨ مـرحـبـاً بـك فـي لـوحـة تـحـكـم Full Mark 🚀`, keyboard);
    delete userState[userId];
});

bot.action('ask_name_month', (ctx) => {
    userState[ctx.from.id] = { step: 'waiting_for_name', type: 'monthly' };
    ctx.reply('✍️ ابـعث "اسـم الطـالب" الجديد:', Markup.inlineKeyboard([[backButton]]));
});

bot.action('ask_name_trial', (ctx) => {
    userState[ctx.from.id] = { step: 'waiting_for_name', type: 'trial' };
    ctx.reply('✍️ ابـعث "اسـم الطـالب" للتجربة المجانية:', Markup.inlineKeyboard([[backButton]]));
});

bot.on('text', async (ctx) => {
    const userId = ctx.from.id;
    const state = userState[userId];
    if (!state) return;

    const text = ctx.text;

    if (state.step === 'waiting_for_name') {
        userState[userId].studentName = text;
        userState[userId].step = 'waiting_for_major';
        ctx.reply(`تـم تسجيل الاسم: ${text}\n\nاخـتار شـعبة الطـالـب:`, 
            Markup.inlineKeyboard([
                [Markup.button.callback('📚 أدبي', 'major_adabi'), Markup.button.callback('🧪 علمي علوم', 'major_oloom')],
                [Markup.button.callback('📐 علمي رياضة', 'major_رياضة')],
                [backButton]
            ])
        );
    }
});

// تشغيل البوت بنظام الـ Webhook لـ Vercel
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
