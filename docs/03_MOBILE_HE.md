# ONE CAREER — הוצאה למובייל

## החלוקה: Phaser למגרש, DOM לתפריטים

בגרסה קודמת נכתב כאן "למה לא Phaser". **ההחלטה הזאת השתנתה, והמסמך מתוקן בהתאם** — הטיעון המקורי היה נכון לגבי *התפריטים* והוחל בטעות גם על *המשחקיות*.

| שכבה | מה מריץ אותה | למה |
|---|---|---|
| תפריטים, טבלאות, סיטואציות, דוחות | **DOM/CSS** | מנוע הטיפוגרפיה של הדפדפן: עברית RTL, גלישה, `bdi`, נגישות, בחירת טקסט. קנבס היה מחייב לממש את כל זה ביד באיכות נמוכה יותר |
| מגרש, כדור, שוער, חומה, חלקיקים, פיזיקה | **Phaser 3.80.1** | לופ, tweens, easing, קלט, particles וקאמרה — בדיוק מה שמנוע משחק נותן, ובדיוק מה שכתיבה ביד עולה בה יקר |

**Phaser מקובע בריפו** ב-`game/vendor/phaser.min.js` (1.18MB, MIT). `game/index.html` טוען אותו ב-`<script src>`; `tools/build_standalone.py` מייצר את `game/one-career.html` עם המנוע מוטמע — קובץ אחד לשחק בו בלי שום דבר נוסף.

**נפילה חיננית:** אם המנוע לא נטען (רשת חסומה, קובץ חסר), `MINI.ok()` מחזיר false והמשחק חוזר למד הביצוע הישן. שום מצב לא נשבר.

### ארבעת המיני־משחקים

| סצנה | קלט | מה מכריע |
|---|---|---|
| `ShotScene` | כוונת סורקת → עוצמה | פינות, רצועת עוצמה, פיזור לפי סיום/האצה, שוער שקורא אותך |
| `PassScene` | חץ מסתובב → משקל | מרחק מהרץ מול טולרנס (ראיית משחק ומסירה קצרה), חיתוך של מגן בנתיב |
| `DribbleScene` | קריאה של הצד + תזמון | חלון תגובה מ-drb/agi מול מוניטין היריבה; לאיזה צד הוא נשבר |
| `FreeKickScene` | כוונת → סיבוב → עוצמה | חומה, עקומת בזייה, טווח השוער |

כולן מדווחות באותו מבנה — `{grade, forced}` — כך שמנוע הדירוג, גיליון הביצועים והסטורילטים לא יודעים שהכדור זז על קנבס.

## המסגרת: במה 1100×520

המשחק מצוייר פעם אחת לבמה לוגית של **1100×520** (2.115:1, קרוב לפרופורציה של טלפון לרוחב) ואז מוקטן או מוגדל לגודל המכשיר:

```js
k  = min(vw/1100, vh/520)
app.style.transform = translate(dx, dy) scale(k)
```

- `transform-origin:0 0` עם `translate` מחושב — לא `place-items:center`, כדי שזה יתנהג זהה ב-RTL וב-LTR.
- `env(safe-area-inset-*)` נחסר מהחישוב, כך שה-notch והפס התחתון לא אוכלים את הבמה.
- מכיוון ש-`#app` נושא `transform`, הוא הופך ל-containing block לכל ה-overlays עם `position:fixed` — המשחק, הרגעים, עמודי המועדון — ולכן כולם מוקטנים איתו. משום כך כל ה-overlays מוזרקים ל-`#layers` שבתוך `#app`, ולא ל-`document.body`.

## אפס גלילה

אין גלילה בשום מסך. אחרי כל `render()` הפונקציה `layoutBoards()`:

1. אוספת את כל הפאנלים (`.p`) בסדר הקריאה.
2. **מחלנת טבלאות ארוכות** — טבלה עם יותר שורות ממה שנכנס מקבלת pager משלה (`◀ 12–24 מתוך 30 ▶`).
3. מודדת כל פאנל ברוחב העמודה האמיתי (בתוך probe מחוץ למסך, בגובה חופשי — אחרת grid מותח את הפאנל והמדידה משקרת).
4. אורזת לעמודות בסדר קריאה, ומעמודה שנגמרה עוברת לעמודה הבאה ואז לדף הבא.
5. מציירת pager: חצים, נקודות, ומספר דף.

ניווט בין דפים: חצים, נקודות, **החלקה** (swipe), או מקשי החצים.

## נעילת landscape

- **PWA:** `manifest.webmanifest` עם `"orientation": "landscape"` ו-`"display": "fullscreen"`.
- **דפדפן:** בלחיצה הראשונה על מכשיר קטן — `requestFullscreen()` ואז `screen.orientation.lock("landscape")`. שני אלה דורשים ג׳סטה של המשתמש, ולכן הם רצים על ה-click הראשון.
- **portrait בטלפון:** מסך `#rotate` מבקש לסובב. הוא מופיע רק כשהמכשיר קטן (`min(vw,vh) < 520`) — טאבלט או דסקטופ בפורטרייט פשוט מקבלים במה מוקטנת.
- **אפליקציה נטיבית:** נעילה אמיתית ב-`AndroidManifest.xml` / `Info.plist` (למטה).

## אריזה עם Capacitor

```bash
npm init -y
npm i @capacitor/core @capacitor/cli
npm i @capacitor/android @capacitor/ios
npx cap init "ONE CAREER" com.onecareer.game --web-dir=game
# capacitor.config.json כבר בריפו — הוא מצביע על game/
npx cap add android
npx cap add ios
npx cap sync
npx cap open android     # או ios
```

### נעילת orientation נטיבית

**Android** — `android/app/src/main/AndroidManifest.xml`, בתוך ה-`<activity>`:

```xml
android:screenOrientation="sensorLandscape"
android:configChanges="orientation|keyboardHidden|keyboard|screenSize|locale|smallestScreenSize|screenLayout|uiMode"
```

**iOS** — `ios/App/App/Info.plist`:

```xml
<key>UISupportedInterfaceOrientations</key>
<array>
  <string>UIInterfaceOrientationLandscapeLeft</string>
  <string>UIInterfaceOrientationLandscapeRight</string>
</array>
<key>UIRequiresFullScreen</key>
<true/>
```

### אייקונים ומסכי פתיחה

`game/icon.svg` הוא המקור. לחנויות נדרשים PNG:

```bash
# 1024 לחנות, 512 ל-PWA, 192 ל-Android
npx @capacitor/assets generate --iconBackgroundColor '#17150F' --splashBackgroundColor '#17150F'
```

## מה שנשאר לפני שחרור מסחרי

1. **שמות מועדונים אמיתיים הם סימני מסחר.** ראו `docs/02_DATA_AND_LICENSING_HE.md` — ההפרדה בין `ClubIdentity` ל-`ClubSimulation` נבנתה כדי שהחלפה לשמות גנריים תהיה בעלות אפס.
2. **אייקוני PNG** בכל הגדלים.
3. **בדיקה על מכשירים אמיתיים** — במיוחד iPhone עם notch ב-landscape, ומכשירי אנדרואיד עם aspect 20:9.
