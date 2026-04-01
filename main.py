const { Telegraf, Markup } = require('telegraf');
const admin = require('firebase-admin');

// 1. ربط الفايربيز (تأكد من وجود الملف بنفس الاسم في المشروع)
const serviceAccount = require("./full-mark-giza-firebase-adminsdk-fbsvc-d3b5aa294c.json");

if (!admin.apps.length) {
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccount)
    });
}

const db = admin.firestore();
const bot = new Telegraf('8296071930:AAGtL5Lr_zCc3DlKToMpRHc0citP7CX2x2s'); // التوكن الحقيقي

const OWNER_ID = 6188310641; // الـ ID بتاعك
let userState = {};

// دالة توليد الأكواد
const generateCode = () => Math.floor(100000 + Math.random() * 900000).toString();

// التحقق من الصلاحيات
async function isAuthorized(userId) {
    if (userId === OWNER_ID) return true;
    const doc = await db.collection('admins').doc(userId.toString()).get();
    return doc.exists;
}

// القائمة الرئيسية
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

bot.start(async (ctx) => {
    const userId = ctx.from.id;
    if (!(await isAuthorized(userId))) return ctx.reply("⚠️ غير مصرح لك.");
    const keyboard = await getMainKeyboard(userId);
    ctx.reply(`✨ مـرحـبـاً بـك فـي لـوحـة تـحـكـم Full Mark 🚀`, keyboard);
});

const backButton = [Markup.button.callback('🔙 الرجوع للقائمة الرئيسية', 'main_menu')];

bot.action('main_menu', async (ctx) => {
    const userId = ctx.from.id;
    const keyboard = await getMainKeyboard(userId);
    ctx.editMessageText(`✨ مـرحـبـاً بـك فـي لـوحـة تـحـكـم Full Mark 🚀`, keyboard);
    delete userState[userId];
});

// --- 1. تفعيل طالب جديد ---
bot.action(['ask_name_month', 'ask_name_trial'], (ctx) => {
    userState[ctx.from.id] = { step: 'waiting_for_name', type: ctx.match === 'ask_name_trial' ? 'trial' : 'monthly' };
    ctx.reply('✍️ ابـعث "اسـم الطـالب":', Markup.inlineKeyboard([backButton]));
});

// --- 2. تجديد الاشتراك ---
bot.action('renew_init', (ctx) => {
    userState[ctx.from.id] = { step: 'waiting_for_code_renew' };
    ctx.reply('🔄 ابعت "كود الطالب" اللي عايز تجدد له الاشتراك:', Markup.inlineKeyboard([backButton]));
});

// --- 3. تغيير الجهاز ---
bot.action('reset_device_init', (ctx) => {
    userState[ctx.from.id] = { step: 'waiting_for_code_reset' };
    ctx.reply('📱 ابعت "كود الطالب" لإعادة تعيين الجهاز:', Markup.inlineKeyboard([backButton]));
});

// --- 4. عرض بيانات الطالب ---
bot.action('view_info_init', (ctx) => {
    userState[ctx.from.id] = { step: 'waiting_for_code_info' };
    ctx.reply('👤 ابعت "كود الطالب" لعرض بياناته:', Markup.inlineKeyboard([backButton]));
});

// --- 5. إضافة موظف ---
bot.action('add_admin_init', (ctx) => {
    if (ctx.from.id !== OWNER_ID) return;
    userState[ctx.from.id] = { step: 'waiting_for_admin_id' };
    ctx.reply('👤 ابعت الـ ID الخاص بالموظف الجديد:', Markup.inlineKeyboard([backButton]));
});

// --- استقبال النصوص والمعالجة ---
bot.on('text', async (ctx) => {
    const userId = ctx.from.id;
    const state = userState[userId];
    if (!state) return;
    const text = ctx.text.trim();

    // إضافة موظف
    if (state.step === 'waiting_for_admin_id' && userId === OWNER_ID) {
        await db.collection('admins').doc(text).set({ addedBy: OWNER_ID, date: new Date() });
        ctx.reply('✅ تم إضافة الموظف بنجاح.', Markup.inlineKeyboard([backButton]));
        delete userState[userId];
    }
    // اسم الطالب الجديد
    else if (state.step === 'waiting_for_name') {
        userState[userId].studentName = text;
        userState[userId].step = 'waiting_for_major';
        ctx.reply(`تـم تسجيل الاسم: ${text}\nاخـتار شـعبة الطـالـب:`, 
            Markup.inlineKeyboard([
                [Markup.button.callback('📚 أدبي', 'major_adabi'), Markup.button.callback('🧪 علمي علوم', 'major_oloom')],
                [Markup.button.callback('📐 علمي رياضة', 'major_رياضة')],
                backButton
            ])
        );
    }
    // تجديد الاشتراك
    else if (state.step === 'waiting_for_code_renew') {
        const doc = await db.collection('student_codes').doc(text).get();
        if (!doc.exists) return ctx.reply('❌ الكود غير صحيح.', Markup.inlineKeyboard([backButton]));
        await db.collection('student_codes').doc(text).update({ createdAt: admin.firestore.FieldValue.serverTimestamp() });
        ctx.reply('✅ تم تجديد الاشتراك بنجاح.', Markup.inlineKeyboard([backButton]));
        delete userState[userId];
    }
    // ريست جهاز
    else if (state.step === 'waiting_for_code_reset') {
        const doc = await db.collection('student_codes').doc(text).get();
        if (!doc.exists) return ctx.reply('❌ الكود غير صحيح.', Markup.inlineKeyboard([backButton]));
        await db.collection('student_codes').doc(text).update({ deviceId: null, isUsed: false });
        ctx.reply('📱 تم فك ارتباط الجهاز بنجاح. يمكن للطالب الدخول من جهاز جديد.', Markup.inlineKeyboard([backButton]));
        delete userState[userId];
    }
    // عرض بيانات
    else if (state.step === 'waiting_for_code_info') {
        const doc = await db.collection('student_codes').doc(text).get();
        if (!doc.exists) return ctx.reply('❌ الكود غير صحيح.', Markup.inlineKeyboard([backButton]));
        const d = doc.data();
        ctx.reply(`👤 الاسم: ${d.studentName}\n📖 الشعبة: ${d.major}\n📱 حالة الجهاز: ${d.deviceId ? 'مرتبط' : 'غير مرتبط'}`, Markup.inlineKeyboard([backButton]));
        delete userState[userId];
    }
});

// معالجة الشعبة
const mKeys = { 'major_adabi': 'أدبي', 'major_oloom': 'علمي علوم', 'major_رياضة': 'علمي رياضة' };
Object.keys(mKeys).forEach(k => {
    bot.action(k, async (ctx) => {
        const s = userState[ctx.from.id];
        if (!s) return;
        const code = generateCode();
        await db.collection('student_codes').doc(code).set({
            code, studentName: s.studentName, major: mKeys[k], type: s.type, isUsed: false, deviceId: null, createdAt: admin.firestore.FieldValue.serverTimestamp()
        });
        ctx.replyWithMarkdown(`✅ تم التفعيل\n👤 **الاسم:** ${s.studentName}\n🎫 **الكود:** \`${code}\``, Markup.inlineKeyboard([backButton]));
        delete userState[ctx.from.id];
    });
});

// التصدير لـ Vercel
module.exports = async (req, res) => {
    if (req.method === 'POST') {
        await bot.handleUpdate(req.body);
        res.status(200).send('OK');
    } else {
        res.status(200).send('<h1>Full Mark Bot is Running!</h1>');
    }
};
