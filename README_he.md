# Binance ↔ OpenAI iPhone Bridge (MVP)

פרויקט MVP שמחבר בין Binance Futures לבין OpenAI דרך שרת קטן בענן, כך שהאייפון משמש כממשק עבודה. זה לא חיבור "ישיר" מתוך אפליקציית ChatGPT; בפועל צריך רכיב שרת באמצע שמדבר גם עם OpenAI API וגם עם Binance API/WebSocket. OpenAI ממליצה להשתמש ב-Responses API עם function/tool calling עבור חיבור למערכות חיצוניות, ו-Binance Futures מספקים REST + WebSocket וכן user data streams עם `listenKey` שדורש חידוש תקופתי. citeturn972313search0turn972313search4turn972313search2turn972313search11turn972313search19

## מה כלול פה
- FastAPI backend
- חיבור ל-Binance USDⓈ-M Futures REST
- מאזין WebSocket למרקט דאטה
- יצירת `listenKey` וחידוש keepalive ל-user data stream
- שכבת OpenAI Agent עם tools פנימיים
- דף ווב פשוט שמתאים לאייפון
- Dockerfile + requirements + env template

## איך זה עובד
1. השרת נפתח בענן.
2. השרת שומר חיבור WebSocket למרקט דאטה של Binance Futures. בסיס ה-WebSocket למרקט סטרימס הוא `wss://fstream.binance.com`, וה-WebSocket API הכללי של USDⓈ-M Futures זמין גם ב-`wss://ws-fapi.binance.com/ws-fapi/v1`. Binance מציינים גם שחיבור WebSocket בודד תקף ל-24 שעות ושהשרת שולח ping כל 3 דקות. citeturn972313search10turn972313search2
3. עבור נתוני חשבון, השרת יוצר `listenKey` דרך `POST /fapi/v1/listenKey`, וצריך לחדש אותו בערך כל 60 דקות עם `PUT /fapi/v1/listenKey`, אחרת ה-stream נסגר. citeturn972313search19turn972313search11turn972313search3
4. ה-Agent משתמש ב-OpenAI Responses API ו-tool calling כדי לקרוא לכלים כמו `get_market_state`, `get_open_positions`, ו-`place_order`. OpenAI ממליצה על Responses API בפרויקטים חדשים. citeturn972313search0turn972313search4turn972313search8turn972313search12
5. אתה פותח מהאייפון את דף הווב של השרת או Shortcut של iOS ושולח פקודות/שאלות.

## חשוב על האייפון
יצירה ועריכה של GPTs מוגבלת לחוויית הווב; אפליקציות מובייל תומכות בשימוש ב-GPTs אבל לא בבנייה או עריכה שלהם. לכן בשביל מערכת כזאת לא בונים GPT מתוך האייפון עצמו; משתמשים ב-API ובשרת. citeturn972313search1turn972313search13

## מצב עבודה מומלץ
- **Advisory mode**: ה-Agent רק מציע סטאפים, סטופים ויעדים.
- **Semi-auto mode**: ה-Agent יכול להוציא פקודה רק אחרי `confirm=true`.
- **Read-only mode**: אין הרשאות מסחר, רק קריאת נתונים.

## אבטחה מינימלית שחובה להפעיל
- API Key נפרד ל-Binance Futures
- להתחיל ב-read only
- לעבור ל-trade רק אחרי בדיקה על testnet
- להגביל IP אם אתה משתמש ב-IP קבוע של השרת
- להגדיר max leverage / max order notional בתוך הקוד

## קבצי הפרויקט
- `app/main.py` – שרת FastAPI
- `app/binance_client.py` – REST ו-WebSocket ל-Binance
- `app/openai_agent.py` – אינטגרציית OpenAI
- `app/models.py` – סכמות נתונים
- `static/index.html` – UI בסיסי לאייפון
- `.env.example` – משתני סביבה
- `requirements.txt` – תלויות
- `Dockerfile` – דיפלוי לענן
- `IPHONE_SETUP.md` – שימוש מהאייפון

## דיפלוי מהיר
### אופציה 1: Render / Railway / Fly.io
- פותחים repo ב-GitHub
- מעלים את התיקייה
- מחברים שירות Web Service
- מוסיפים ENV vars
- בוחרים Dockerfile או `uvicorn app.main:app`

### אופציה 2: VPS
- Ubuntu קטן
- Docker compose / systemd

## משתני סביבה
ראה `.env.example`.

## בדיקה מקומית
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## אזהרה משפטית/מסחרית
הפרויקט הוא תשתית טכנית. לא מובטח רווח, ואין כאן הבטחה לביצועי מסחר. החלק האוטומטי כבוי כברירת מחדל.
