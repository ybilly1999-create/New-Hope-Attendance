# 部署到 Render 完整指南

本指南會帶您將崇拜出席系統部署到 Render，免費版可長期使用。

---

## 第一部分：把程式上傳到 GitHub

### 1.1 建立 GitHub 帳號和 Repository
1. 前往 [github.com](https://github.com) 註冊或登入
2. 點右上角 `+` → `New repository`
3. 名稱輸入例如 `sunshine-attendance`
4. 設為 **Private**（私人，因為含教會資料）
5. 不要勾選 "Initialize with README"
6. 按 `Create repository`

### 1.2 上傳程式
打開 Terminal / 命令提示字元，進入 `church-attendance` 資料夾：

```bash
cd church-attendance

# 初始化 git
git init
git add .
git commit -m "Initial commit"

# 連接到您的 GitHub repo（換成您的 URL）
git remote add origin https://github.com/YOUR_USERNAME/sunshine-attendance.git
git branch -M main
git push -u origin main
```

> 💡 若是第一次使用 git，可能會要求登入。可以裝 [GitHub Desktop](https://desktop.github.com/) 來用圖形介面操作。

---

## 第二部分：在 Render 部署

### 2.1 註冊 Render
1. 前往 [render.com](https://render.com)
2. 用 GitHub 帳號登入（選 "Sign in with GitHub"）
3. 授權 Render 讀取 repository

### 2.2 建立 Web Service

**方式 A：使用 render.yaml（推薦，最簡單）**

1. Dashboard → 右上 `New` → **`Blueprint`**
2. 選擇您剛剛建立的 repository
3. Render 會自動讀取 `render.yaml` 設定
4. 在 `ADMIN_PASSWORD` 欄填入您要的密碼（記下來！）
5. 按 `Apply` → 等待 3-5 分鐘部署完成

**方式 B：手動建立 Web Service**

1. Dashboard → `New` → **`Web Service`**
2. 選擇 repository
3. 設定：
   - **Name**: `sunshine-attendance`（或您喜歡的名稱）
   - **Region**: Singapore（離香港最近）
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && python scripts/init_db.py`
   - **Start Command**: `gunicorn wsgi:app`
   - **Plan**: Free
4. 在 **Environment Variables** 加入：
   | Key | Value |
   |---|---|
   | `ADMIN_PASSWORD` | （您要的密碼） |
   | `SECRET_KEY` | （點 "Generate" 自動生成） |
   | `SERVICE_START_TIME` | `10:00` |
   | `PYTHON_VERSION` | `3.11.9` |
5. 按 `Create Web Service`

### 2.3 加入持久化磁碟（重要！）

Render 免費版的檔案會在每次 deploy 重置，需要掛載一個 disk 保留資料庫：

1. Service 頁面 → 左側 `Disks` → `Add Disk`
2. 設定：
   - **Name**: `data`
   - **Mount Path**: `/opt/render/project/src/instance`
   - **Size**: `1 GB`
3. `Save`

> ⚠ 注意：Render 免費 Web Service 不支援 disk。若要使用 disk，需升級到 Starter 方案（USD $7/月）。
>
> **替代方案**：使用 Render 免費的 PostgreSQL（見 2.4）。

### 2.4 替代方案：使用免費 PostgreSQL（推薦給長期使用）

免費 PostgreSQL 90 天會過期一次，但比 disk 穩定。設定方法：

1. Dashboard → `New` → `PostgreSQL`
2. 名稱例如 `attendance-db`，Region 選 Singapore，Plan 選 Free
3. `Create Database`
4. 等資料庫建立完成，複製 `Internal Database URL`
5. 回到您的 Web Service → `Environment` → 新增變數：
   - **Key**: `DATABASE_URL`
   - **Value**: （貼上剛複製的 URL）
6. `Save Changes` → 系統會自動重新部署

---

## 第三部分：匯入既有 Excel 資料

部署完成後，您需要把 Excel 中的會員清單和歷史出席匯入。

### 3.1 上傳 Excel 檔案到 Repository

最簡單的方法：把兩個 Excel 檔案放進 `data/` 資料夾，推到 GitHub：

```bash
# 在本地端
cp "崇拜出席記錄 2025-2026.xlsx" church-attendance/data/history.xlsx
cp "手動崇拜點名.xlsx" church-attendance/data/members.xlsx

cd church-attendance
git add data/
git commit -m "Add seed data"
git push
```

> 註：因 `.gitignore` 預設忽略 `data/*.json`，但 `.xlsx` 檔不會被忽略。

### 3.2 在 Render Shell 執行匯入腳本

1. Service 頁面 → 左側 `Shell`
2. 在指令列輸入：
   ```bash
   python scripts/init_db.py \
     --seed-history data/history.xlsx \
     --seed-members data/members.xlsx
   ```
3. 等待約 1 分鐘，看到 `✓ Imported XXX members, XXX attendance records` 即完成

> 💡 若您後來新增會員或修改 Excel，可重新執行此指令。會略過已存在的會員。

---

## 第四部分：開始使用

### 4.1 拿到您的網址
Render 會給您一個網址，例如：
```
https://sunshine-attendance.onrender.com
```

### 4.2 設定崇拜開始時間
1. 進入 `https://your-url.onrender.com/admin/login`
2. 輸入您剛才設定的 `ADMIN_PASSWORD`
3. 進入 `設定` 頁面，調整「崇拜開始時間」（預設 10:00）

### 4.3 列印 QR Code
1. Admin → `QR Code` 頁面
2. 按右上 `🖨 列印`
3. 把每位會員的 QR code 印出來，貼在他們的會員證上

### 4.4 推廣使用
- **會員可以這樣簽到**：
  - 打開教會 WiFi 連到簽到網站，搜尋姓名按下「確認簽到」
  - 或掃描自己的 QR code 直接進入個人簽到頁
- **執事/同工可登入 Admin**：查看出席記錄、補登未簽到、看全年報表

---

## 常見問題

### Q：免費版會休眠嗎？
A：會。Render 免費 Web Service 在 15 分鐘無流量後會休眠，下次造訪首次載入需 30 秒。星期日早上崇拜開始前可以先讓人造訪一下喚醒。

### Q：我忘記管理員密碼了？
A：到 Render → Service → Environment → 修改 `ADMIN_PASSWORD` → 儲存後會自動重啟。

### Q：怎麼修改會員資料？
A：直接到網站 Admin → 會員管理 → 編輯。也可以在 Render Shell 執行 `python scripts/init_db.py --seed-members data/new_list.xlsx` 批次更新。

### Q：資料如何備份？
A：每月一次到 Admin → 全年報表 → `下載 Excel` 即可。建議放在 Google Drive。

### Q：免費 PostgreSQL 90 天到期怎麼辦？
A：Render 會在到期前 7 天 email 提醒。屆時可以：
1. 先到 Admin 下載當年的 Excel 備份
2. 在 Render 建立新的免費 PostgreSQL
3. 把新的 `DATABASE_URL` 填回 Service Environment
4. 重啟後在 Shell 重新跑 seed script 匯入資料

或升級到 Starter Postgres 方案（USD $7/月）就不會過期。

### Q：可以自訂網址（domain）嗎？
A：可以。Render 免費版支援自訂 domain。Service → Settings → Custom Domain 跟著步驟設定 DNS 即可。

---

## 進階：本機備份資料庫

```bash
# 從 Render 下載 SQLite db（需 Starter 方案有 disk 才行）
# 或用 PostgreSQL：
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

---

## 需要協助？

若部署遇到問題，可以截圖錯誤訊息，並提供：
- Render 的 build log（在 Service → Logs 查看）
- 您執行的指令

祝順利！願主祝福您和教會的事工。
