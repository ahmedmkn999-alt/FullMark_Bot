const admin = require('firebase-admin');

// ─────────────────────────────────────────
//  Firebase Init
// ─────────────────────────────────────────
admin.initializeApp({
  credential: admin.credential.cert({
    type: "service_account",
    project_id: "fullmark-neweddition",
    private_key_id: "8e6bea610e1b4d1af3d27c27e137bd34e6636a4e",
    private_key: "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCj593kaisD2UBo\noiWS25EmmBDCer1zV9LTsjtkh0Si7iEkZHA9wknRV71bAdhnBYB9ZVYSN5mjlnSf\nNhkO/CJ5gUtP9v0XPXk1SwFnx2qXq+WS3Cu+P87k43s/n7GhU3upFRGH5mi01Wq1\nBdW86TgTbwwSROXCnJ7N/8f3CvLj8rfuVO9C8Q57OLPVLZJxLqcRH52Fl/d0I+uv\n87pUl8+TjUOkkUEi94q/Wnv4+RG99hMuZxTY8K+zVs7nrkYVMszGnLV7Ww7chN9L\nql4Ws9m3Xk8DfN0qsl2Mm3Zlkyx5Kn21Z8uf1MvK5gj6e8FThg5rtvMNGuBkdLv6\nIfVcz9yDAgMBAAECgf9Z6EM8MseoBDMlycvShSyZwV5mpOPCI8Si/C+hkZsP/XMd\nmwQJhy+E9jhoM11M/6lj8Aegqq+g9J/LOlgJQ8m4ToSKxaA+SfCy1IAbhNqsYWo8\nFoAhD/I5M1+vBr93W1iRfqx5MAHqJlaDSx0d5nFJG0a4ARx49Kl891FVZgYraxLU\nlLwK00kJbQaZ7cltFw76puOfwces1Zjyfa7csLUUnABO/4GkjN5JIbMGjGFetCNM\n1xN0kT8FhTTf/o1IP0YDVuPNgosYGanfQrKtWlBdw6CbeIxb06lDjW20glAD97Bd\nTIm6DsiNl9HS5bot2qOYekEbNfzPqweEinN6Da0CgYEA1sMr+DjgQB3QqCyHrFRg\nnfovm4uQFb6bVVgmOQHb9MCn5BjQQgsF6gvTrxpp69p0ALKJJCdk1trI9N7i+qwv\nz8eAf4ytHLFJMEyo9XJJmDu3i8EOACYuCyWzwCwbY/ckAc6FsZiMgAmIaSoNFpjH\nlNvyON5gGKgWJvPA4t6Ik1UCgYEAw2DK5K+DoieUbT4MzMl5U5syJZi0iPox5tpb\n+FL2+f8vbZq+mWOHosGA0YL9ejwCCoJ01exulNOlTdGI2o28u+fyoH0ozt54yqDR\ntqxbfDsPzQOYiwWn+Du1VEHAZuXH9az5PHM9ggqc/KuCONHbMsIG1RI7eFOQzawu\nJuLF4HcCgYEAtk3W9U7SjZrBlQC36sF1gqTt5MwD83FpyniZearqXEluO2IU5vsU\neiiv+OQjJeK6thzX7ajDIN931uWdJ80iiO6BVcTE7qZPyoBIrJHnhyKqHCg1Ckte\nqnfGrkrCtYkFN8NoGem02rs84Iihs5zdTq+mXj/mswd8RnSEOBFPPkECgYAk5rEr\nhCLei48zGtccDqmFqvhLtY3TmT23lmJsgm73RMVWdDWvjubdTKLh71WkspTIG1+p\nz+AK5/Z+viaU8NRGwUZIHZuJhudVjg5N7DvTOOyBEj7LcyQIdG6JHWoThS7BLgxc\n6H8jgpGn/1S3GpvF+HOF5s2oqk/dKLoGyioJfQKBgQDQc2sWkR7raz1Z8v92hEE8\nkOE/FPLvDdlH5psghq05ZU0yxbBPCjJ6QmV1LLy1F+Ya+XeLjp5AE0jTpgorUlLB\nZIc4wYipK2x0PypqgJD7+L3evqAwuXZEvtWiZPB2N+ueXsE00T4m35N4w9VNadI4\ndDfLoOIsWbfGCuvOA0SmZQ==\n-----END PRIVATE KEY-----\n",
    client_email: "firebase-adminsdk-fbsvc@fullmark-neweddition.iam.gserviceaccount.com",
    client_id: "103917924440939464168"
  }),
  databaseURL: "https://fullmark-neweddition-default-rtdb.europe-west1.firebasedatabase.app"
});

const db = admin.database();

async function setup() {
  console.log('🔄 بدء الإعداد...\n');

  // 1. مسح كل الموظفين
  console.log('🗑️  مسح الموظفين...');
  await db.ref('staff').remove();
  console.log('✅ تم مسح الموظفين\n');

  // 2. مسح كل الطلاب
  console.log('🗑️  مسح الطلاب...');
  await db.ref('students').remove();
  console.log('✅ تم مسح الطلاب\n');

  // 3. مسح المستخدمين القديمين
  console.log('🗑️  مسح المستخدمين القدام...');
  await db.ref('users').remove();
  console.log('✅ تم مسح المستخدمين\n');

  // 4. تسجيل الأونرز
  console.log('👑 تسجيل الأونرز...');
  await db.ref('users/1778665778').set({
    name: 'احمد محمد',
    role: 'OWNER',
    registeredAt: Date.now()
  });
  console.log('✅ احمد محمد (1778665778)');

  await db.ref('users/6188310641').set({
    name: 'الجيزاوي',
    role: 'OWNER',
    registeredAt: Date.now()
  });
  console.log('✅ الجيزاوي (6188310641)\n');

  console.log('🎉 كل حاجة اتعملت! البوت جاهز.');
  console.log('   👑 احمد محمد  → 1778665778');
  console.log('   👑 الجيزاوي   → 6188310641');
  process.exit(0);
}

setup().catch(err => {
  console.error('❌ خطأ:', err.message);
  process.exit(1);
});
