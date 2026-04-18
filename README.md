# sanrio_search

LINE webhook bot — 收到圖片訊息後透過 Google Lens 搜圖，回覆最符合的 URL。

匹配優先順序：`www.sanrio.co.jp` > `*.sanrio.co.jp` > 任何 `.jp` 網域。

## 在新電腦上部署

### 1. 安裝必要軟體

| 軟體 | 用途 | 安裝方式 |
|------|------|----------|
| **Python 3.12+** | 執行服務 | https://www.python.org/downloads/ |
| **Node.js 18+** | playwright-cli 需要 | https://nodejs.org/ |
| **ngrok** | 將本機暴露為公開 HTTPS 網址 | `winget install ngrok.ngrok` |

### 2. 下載專案

```bash
git clone https://github.com/dijkstra1115/sanrio_search.git
cd sanrio_search
```

### 3. 安裝依賴

```bash
pip install -r requirements.txt
npm install -g @playwright/cli@latest
```

### 4. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入：

```
LINE_CHANNEL_SECRET=你的_LINE_Channel_Secret
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_Channel_Access_Token
APP_BASE_URL=https://你的ngrok網域
```

### 5. 設定 ngrok

1. 到 https://ngrok.com 註冊免費帳號
2. 到 Dashboard 取得 authtoken 並執行：
   ```bash
   ngrok config add-authtoken 你的token
   ```
3. 到 **Domains** 頁面領取一個免費固定網域（如 `xxx.ngrok-free.dev`）
4. 把 `https://你的網域` 填到 `.env` 的 `APP_BASE_URL`（啟動腳本會自動從這裡提取 ngrok 網域）
5. 把 `https://你的網域/webhook` 設為 LINE Developers Console 的 Webhook URL（只需設定一次）

### 6. 一鍵啟動

雙擊專案根目錄的 `start.bat`。

腳本會自動：檢查環境 → 安裝缺少的依賴 → 啟動 ngrok 隧道 → 啟動服務。

按 `Ctrl+C` 停止。

## 手動啟動（不用 ngrok）

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

需要自行處理公網暴露和 HTTPS。

## 本機測試

```bash
python -m app.scripts.smoke_lookup --image-path ./your_image.jpg --json
```

## 環境變數說明

| 變數 | 必填 | 預設值 | 說明 |
|------|------|--------|------|
| `LINE_CHANNEL_SECRET` | 是 | — | LINE Channel Secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | 是 | — | LINE Channel Access Token |
| `APP_BASE_URL` | 是 | — | 服務公開 URL |
| `LOG_LEVEL` | 否 | `INFO` | 日誌等級 |
| `LOOKUP_TIMEOUT_SECONDS` | 否 | `45` | 單次搜圖超時秒數 |
| `PLAYWRIGHT_HEADLESS` | 否 | `false` | 無頭模式（目前會被 Google 擋，建議 `false`） |
| `PLAYWRIGHT_CLI_COMMAND` | 否 | 自動偵測 | 覆寫 playwright-cli 指令 |

## 注意事項

- Google Lens 會在無頭模式下偵測並阻擋請求（跳轉到 `/sorry/`），因此預設使用有頭模式。
- 服務同一時間只處理一張圖片，後續請求會收到「請稍候」的回覆。
- 連續被 Google 阻擋時會啟動指數退避冷卻（5 分鐘 → 30 分鐘 → 2 小時）。
