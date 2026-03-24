# שימוש מהאייפון

## דרך 1 — Safari Web App
1. פותחים את כתובת השרת ב-Safari.
2. לוחצים Share.
3. בוחרים Add to Home Screen.
4. מתקבל אייקון כמו אפליקציה.

## דרך 2 — iOS Shortcut
אפשר ליצור Shortcut ששולח POST ל-`/chat` או ל-`/trade/confirm`.

### דוגמה ל-Shortcut
- פעולה: Get Contents of URL
- URL: `https://YOUR-SERVER/chat`
- Method: POST
- Headers:
  - `Content-Type: application/json`
  - `X-Bridge-Token: YOUR_BRIDGE_TOKEN`
- Body:
```json
{
  "message": "Analyze SIRENUSDT and tell me if short setup is valid",
  "symbol": "SIRENUSDT"
}
```

## מצב מומלץ להתחלה
- לעבוד עם `/chat` + `/market/{symbol}` + `/positions`
- להשאיר `/trade/*` נעול עד בדיקה מוצלחת
