# 新希望浸信會陽光堂 — 崇拜出席記錄系統

A simple, mobile-friendly attendance tracking website for **新希望浸信會陽光堂**. Built with Flask + Tailwind. Designed for deployment on Render with GitHub.

## 功能 / Features

### 會員模式 (Member Mode)
- ✅ 透過姓名、編號或英文名搜尋並一鍵簽到
- 📱 QR Code 簽到（每位會員專屬連結）
- 🌱 新朋友 / 訪客登記（支援不記名）
- ⏰ 自動判斷準時 / 遲到
- ✨ 簡潔友善的中文介面

### Admin 模式 (Admin Mode)
- 📊 即時總覽：本日出席、成人/兒童準時/遲到統計
- 👥 會員管理：新增、編輯、停用
- ✅ 出席記錄管理：手動補登、修正狀態、刪除
- 🌱 新朋友清單管理
- 📈 全年出席報表（每週總覽 + 會員明細視覺化）
- 📥 一鍵匯出 Excel（格式相容原 Google Form 樣式）
- 🔲 自動產生會員 QR Code（可列印）
- ⚙ 自訂崇拜開始時間（準時/遲到分界）

## 快速開始 (本地開發)

```bash
# 1. Clone repo
git clone <your-repo-url>
cd church-attendance

# 2. Setup Python env
python -m venv venv
source venv/bin/activate    # Mac/Linux
# venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure (copy and edit)
cp .env.example .env
# Edit .env, set ADMIN_PASSWORD

# 5. Initialize database (and optionally seed from Excel)
python scripts/init_db.py \
  --seed-history /path/to/Chong-Bai-Chu-Xi-Ji-Lu-2025-2026.xlsx \
  --seed-members /path/to/Shou-Dong-Chong-Bai-Dian-Ming.xlsx

# 6. Run
python wsgi.py
# Visit http://localhost:5000
```

預設管理員密碼存於 `.env` 檔的 `ADMIN_PASSWORD`。

## 部署到 Render (透過 GitHub)

詳見 [DEPLOY.md](DEPLOY.md)

簡要步驟：

1. 將整個 `church-attendance/` 目錄推到自己的 GitHub Repository
2. 登入 [render.com](https://render.com)，連接 GitHub
3. New → Web Service → 選擇 Repository
4. Render 會自動偵測 `render.yaml`，按下 Apply
5. 在 Environment 設定 `ADMIN_PASSWORD`
6. 部署完成後，第一次需要在 Shell 執行 seed script 匯入會員資料

## 專案結構

```
church-attendance/
├── app/
│   ├── __init__.py        # Flask app factory
│   ├── models.py          # 資料庫模型 (Member, Attendance, Visitor, Setting)
│   ├── routes.py          # 會員前台路由
│   ├── admin.py           # 管理員後台路由
│   ├── api.py             # JSON API
│   ├── utils.py           # 工具函式（時間判斷等）
│   └── templates/         # Jinja2 模板
├── scripts/
│   └── init_db.py         # 資料庫初始化 / Excel 匯入
├── instance/              # SQLite 檔案位置（自動生成）
├── requirements.txt
├── render.yaml            # Render 部署設定
├── wsgi.py                # Production entry point
├── .env.example
└── README.md
```

## 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `ADMIN_PASSWORD` | 管理員登入密碼 | `admin`（請務必修改） |
| `SECRET_KEY` | Flask session 密鑰 | （自動生成） |
| `DATABASE_URL` | 資料庫連線字串 | SQLite 檔案 |
| `SERVICE_START_TIME` | 預設崇拜開始時間 | `10:00` |

## Excel 資料相容性

匯入腳本相容原系統的兩個 Excel 檔案：

1. **崇拜出席記錄 2025-2026.xlsx**：從「全年總表」工作表匯入會員清單與全年出席記錄。表格中的數字解讀為：
   - `1` = 成人準時、`2` = 成人遲到
   - `3` = 兒童準時、`4` = 兒童遲到
2. **手動崇拜點名.xlsx**：從「點名用」工作表補充英文名、兒童標記等資料。

匯出的 Excel 格式與原檔案結構相符，可繼續沿用既有工作流程。

## 技術棧

- **Backend**: Python 3.11 + Flask + SQLAlchemy
- **Database**: SQLite (default) or PostgreSQL (recommended for Render)
- **Frontend**: Jinja2 templates + Tailwind CSS (CDN) + 原生 JavaScript
- **Deployment**: Render (Gunicorn)
- **Fonts**: Noto Sans TC (繁體中文)

## 授權 / License

僅供新希望浸信會陽光堂內部使用。
