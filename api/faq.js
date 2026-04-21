const { Telegraf } = require('telegraf');

const bot = new Telegraf('8296071930:AAGtL5Lr_zCc3DlKToMpRHc0citP7CX2x2s');

// ─────────────────────────────────────────
//  المحتوى
// ─────────────────────────────────────────
const WELCOME = `🎓 *أهلاً بك في Full Mark!*

🚀 الوحش رجع بتحديث مرعب.. منصة Full Mark في ثوبها الجديد!

عشان إحنا عارفين إن هدفك *"الدرجة النهائية"*، جمعنا لك صفوة مدرسي مصر في مكان واحد.

👇 اختار اللي عايز تعرفه:`;

const TEACHERS = `🌟 *قائمة عمالقة التدريس على المنصة:*

🔹 *اللغة العربية:*
أ. محمد صلاح | أ. رضا الفاروق

🔹 *اللغة الإنجليزية:*
م. وائل ميلاد | م. شريف المصري | م. عبدالحميد حامد | م. مي مجدي | م. انجلشاوي | م. عبقري لغة

🔹 *اللغة الفرنسية:*
م. هريدي | م. حسين الجبلاوي

🔹 *الأحياء:*
د. الجوهري | د. محمد أيمن | د. هوبا | د. أحمد قطب | د. سامح أحمد | جيو ماجد

🔹 *الكيمياء:*
م. خالد صقر | م. محمد عبدالجواد | د. جون | أ. عمرو الصيفي | د. عبدالله حبشي

🔹 *الفيزياء:*
أ. حسام خليل | د. كيرلس | أ. محمد عبدالمعبود | أ. محمود مجدي

🔹 *الجغرافيا:*
أ. أحمد زهران

🔹 *التاريخ:*
المؤرخ | الخديوي

🔹 *الإحصاء والرياضيات:*
م. أحمد عصام | م. أحمد الفواخري | م. لطفي زهران`;

const PRICE = `💰 *سعر الاشتراك:*

✅ *200 جنيه فقط!*

قيمة مقابل محتوى ملوش مثيل من صفوة مدرسي مصر.

🌐 سجل دلوقتي:
http://fullmark.online

_Full Mark.. طريقك للدرجة النهائية بدأ من هنا!_ 🎓✨`;

const CASH = `💳 *أرقام الكاش لدفع الاشتراك:*

📱 *فودافون كاش:*
\`01090747536\``;

const PAYMENT = `📋 *طريقة الدفع خطوة بخطوة:*

1️⃣ حول *200 جنيه* على الرقم ده:
   \`01090747536\`

2️⃣ بعد التحويل، ابعت للتواصل:
   👤 @elgizawy9
   👤 @DevAhmedmo

3️⃣ ابعت معاهم:
   📸 صورة التحويل

✅ وهيتواصلوا معاك في أقرب وقت!`;

const CONTACT = `📞 *للتواصل والاستفسار:*

👤 @elgizawy9
👤 @DevAhmedmo

_هيردوا عليك في أقرب وقت_ ⚡`;

// ─────────────────────────────────────────
//  الكيبورد الرئيسي
// ─────────────────────────────────────────
const mainKeyboard = {
  reply_markup: {
    inline_keyboard: [
      [{ text: '👨‍🏫 المدرسين على المنصة', callback_data: 'teachers' }],
      [{ text: '💰 سعر الاشتراك',          callback_data: 'price'    }],
      [{ text: '💳 أرقام الكاش',           callback_data: 'cash'     }],
      [{ text: '📋 طريقة الدفع',           callback_data: 'payment'  }],
      [{ text: '📞 تواصل معنا',            callback_data: 'contact'  }],
      [{ text: '🌐 الموقع الرسمي',          url: 'http://fullmark.online' }],
    ]
  }
};

const backKeyboard = {
  reply_markup: {
    inline_keyboard: [
      [{ text: '🔙 رجوع', callback_data: 'back' }]
    ]
  }
};

// ─────────────────────────────────────────
//  /start
// ─────────────────────────────────────────
bot.start(async (ctx) => {
  await ctx.reply(WELCOME, { parse_mode: 'Markdown', ...mainKeyboard });
});

// ─────────────────────────────────────────
//  Callbacks
// ─────────────────────────────────────────
bot.action('teachers', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(TEACHERS, { parse_mode: 'Markdown', ...backKeyboard });
});

bot.action('price', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(PRICE, { parse_mode: 'Markdown', ...backKeyboard });
});

bot.action('cash', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(CASH, { parse_mode: 'Markdown', ...backKeyboard });
});

bot.action('payment', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(PAYMENT, { parse_mode: 'Markdown', ...backKeyboard });
});

bot.action('contact', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(CONTACT, { parse_mode: 'Markdown', ...backKeyboard });
});

bot.action('back', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(WELCOME, { parse_mode: 'Markdown', ...mainKeyboard });
});

// ─────────────────────────────────────────
//  Vercel Handler
// ─────────────────────────────────────────
module.exports = async (req, res) => {
  try {
    res.setHeader('Access-Control-Allow-Origin', '*');
    if (req.method === 'OPTIONS') return res.status(200).end();
    if (req.method === 'POST') {
      await bot.handleUpdate(req.body);
      return res.status(200).send('OK');
    }
    res.status(200).send('🤖 FullMark FAQ Bot is running!');
  } catch (err) {
    console.error('FAQ Bot error:', err.message);
    res.status(200).send('OK');
  }
};
