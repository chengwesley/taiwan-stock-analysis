---
name: taiwan-stock-analysis
description: |
  台灣上市上櫃公司三維財務分析儀表板。從 Goodinfo.tw 抓取真實財報數據（損益表、資產負債表、現金流量表），計算關鍵財務指標，生成互動式三分頁 HTML 儀表板（經營分析 / 獲利分析 / 財務健全度）並匯出為可分享的 HTML 檔案。

  當使用者提到以下情境時，一定要使用這個 skill：
  - 「幫我分析 XXXX（股票代碼）」、「財報分析」、「三維分析」
  - 「管銷研發費用分析」、「獲利能力」、「財務健全度」
  - 提到台灣股票代碼（4位數字）並要求分析
  - 「經營/獲利/財務分析」、「幫我看這家公司」
  - 任何涉及台股財務數據視覺化的需求
---

# 台灣股票三維財務分析 Skill

## 概述

本 skill 從 Goodinfo.tw 抓取台灣上市/上櫃公司的真實財報數據，計算三大維度的財務指標，並生成一份互動式 HTML 儀表板及下載檔案。

**三大分析維度：**
- 📊 **經營分析**：營收成長、毛利率、費用率、管銷研費結構
- 💰 **獲利分析**：淨利、EPS、ROE、ROA、三層利潤率
- 🏦 **財務健全度**：流動比率、負債比率、現金流量、現金部位

---

## 步驟一：抓取財報數據

使用以下 Python 腳本從 Goodinfo.tw 抓取數據。**重要：** Goodinfo.tw 需要特定的 `CLIENT_KEY` Cookie，公式如下：

```python
import requests
from bs4 import BeautifulSoup
import time

def get_goodinfo_data(stock_id, rpt_cat):
    """
    rpt_cat 可選：IS_YEAR（損益表）、BS_YEAR（資產負債表）、CF_YEAR（現金流量表）
    """
    tz_offset = -480  # 台灣 UTC+8
    now_ms = time.time() * 1000
    days_since_epoch = now_ms / 86400000
    days_adjusted = days_since_epoch - tz_offset / 1440
    
    client_key = f"2.8|38057.1435627105|46946.0324515993|{tz_offset}|{days_adjusted}|{days_adjusted}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://goodinfo.tw/'
    }
    cookies = {'CLIENT_KEY': client_key}
    url = f"https://goodinfo.tw/tw/StockFinDetail.asp?RPT_CAT={rpt_cat}&STOCK_ID={stock_id}&REINIT={days_adjusted:.10f}"
    
    r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    r.encoding = 'utf-8'
    return BeautifulSoup(r.text, 'html.parser'), days_adjusted
```

### 解析方式

每種報表的數據都在 HTML 中**最後一個（第 6 個，index=6）大型 table** 裡。抓取後迭代所有 `<tr>` 行，解析每行的第 1 欄（項目名稱）和後續欄位（年度數值）。

**三張報表的抓取順序：**
1. `IS_YEAR` → 損益表（營收、毛利、費用、營業利益、淨利、EPS）
2. `BS_YEAR` → 資產負債表（現金、應收帳款、存貨、流動資產、負債、股東權益）
3. `CF_YEAR` → 現金流量表（營業CF、投資CF、融資CF、現金股利）

**關鍵欄位對照（損益表）：**

| 中文欄位名 | 用途 |
|-----------|------|
| 營業收入合計 | 年度營收 |
| 營業毛利（毛損） | 毛利金額 |
| 銷售費用 | 銷售費用 |
| 管理費用 | 管理費用 |
| 研究發展費用 | R&D費用 |
| 營業利益（損失） | 營業利益 |
| 本期淨利（淨損） | 稅後淨利 |
| 基本每股盈餘（元） | EPS |

**關鍵欄位對照（資產負債表）：**

| 中文欄位名 | 用途 |
|-----------|------|
| 現金及約當現金 | 現金部位 |
| 存貨 | 存貨 |
| 流動資產合計 | 流動資產 |
| 流動負債合計 | 流動負債 |
| 負債總額 | 總負債 |
| 股東權益總額 | 股東權益 |
| 資產總額 | 總資產 |

**關鍵欄位對照（現金流量表）：**

| 中文欄位名 | 用途 |
|-----------|------|
| 營業活動之淨現金流入（出） | 營業CF |
| 投資活動之淨現金流入（出） | 投資CF |
| 融資活動之淨現金流入（出） | 融資CF |
| 發放現金股利 | 現金股利 |

---

## 步驟二：計算衍生指標

從原始數據計算以下指標：

```python
# 費用率（各費用 / 營收）
sell_ratio = sell_exp / revenue * 100
admin_ratio = admin_exp / revenue * 100
rd_ratio = rd_exp / revenue * 100
total_opex_ratio = (sell_exp + admin_exp + rd_exp) / revenue * 100

# 毛利率、營業利益率、淨利率
gross_margin = gross_profit / revenue * 100
op_margin = op_income / revenue * 100
net_margin = net_income / revenue * 100

# 流動比率、負債比率
current_ratio = current_assets / current_liabilities * 100
debt_ratio = total_liabilities / total_assets * 100

# ROE、ROA（簡化估算）
roe = net_income / equity * 100
roa = net_income / total_assets * 100

# 自由現金流
fcf = operating_cf + capex  # capex 通常為負值
```

---

## 步驟三：建立 HTML 儀表板

使用 `scripts/build_dashboard.py` 生成 HTML 檔案。詳細模板規格請參閱 `references/dashboard_template.md`。

### 儀表板架構

```
header（公司名稱 + 股票代碼 + 資料來源標注）
├── Tab 1：經營分析
│   ├── KPI Cards（5張）：營收、毛利率、費用率、營業利益、營業利益率
│   ├── Insight Box（3-5條重點）
│   ├── Charts（2×2格）：營收+毛利率combo / 費用堆疊柱 / 費用率折線 / 營業利益+利益率
│   └── Data Table：損益表明細
├── Tab 2：獲利分析
│   ├── KPI Cards（5張）：淨利、淨利率、EPS、ROE、ROA
│   ├── Insight Box
│   ├── Charts（2×2格）：淨利+淨利率 / EPS / 三層利潤率 / 現金股利
│   └── Data Table：獲利能力彙總
└── Tab 3：財務健全度
    ├── KPI Cards（5張）：現金、流動比率、負債比率、營業CF、自由CF
    ├── Insight Box
    ├── Charts（2×2格）：資產負債結構 / 現金流三表 / 流動+負債比率 / 現金趨勢
    └── Data Tables（左右並排）：資產負債表摘要 / 現金流量摘要
```

### Chart.js 設定

- CDN：`https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.min.js`
- 所有圖表需設 `maintainAspectRatio: false`，container 高度固定 `240px`
- 組合圖（bar + line）使用雙 Y 軸（`yAxisID: 'y'` 和 `yAxisID: 'y2'`）
- 配色：藍 `#3182ce`、綠 `#38a169`、橘 `#dd6b20`、紅 `#e53e3e`、紫 `#805ad5`、青 `#319795`

### KPI Card 顏色規則

- 🟢 **green**（`border-left: 4px solid #38a169`）：正向指標（成長、高利潤率）
- 🔵 **blue**（`border-left: 4px solid #3182ce`）：中性指標（費用率、比率）
- 🟠 **orange**（`border-left: 4px solid #dd6b20`）：需關注（費用上升）
- 🔴 **red**（`border-left: 4px solid #e53e3e`）：警示（虧損、高負債）

### 常見 HTML 格式錯誤（務必避免）

1. KPI card 中的 `kpi-change` div 結尾，只能用 `</div>`，絕對不能混入 `</td></tr>`
2. 所有 `<canvas>` 需包在 `class="chart-container"` 的 div 內（含固定高度）
3. tab 切換函數：`onclick="switchTab('ops')"` 等，函數需在 HTML 底部 `<script>` 中定義

---

## 步驟四：Insight Box 撰寫指引

每個分頁的 insight box 需包含 3-5 條**數字具體**的觀察，說明趨勢背後的意義：

- ❌ 不好：「營收有所成長」
- ✅ 好：「三年營收 112.2 → 124.9 億，CAGR +5.6%，顯示業務穩健擴張」

### 常見解讀重點

**經營面：**
- 毛利率是否有結構性改善？（品項組合優化 vs 成本控制）
- 費用率是否隨營收成長而下降？（規模效益）
- 研發投入占比是否維持或提升？

**獲利面：**
- 淨利成長是否超過營收成長？（利潤率擴張）
- EPS 趨勢是否持續創新高？
- 現金配息是否反映獲利品質？

**財務面：**
- 流動比率 > 150% 為健康，> 200% 為優異
- 負債比率 < 50% 通常為穩健，< 40% 為優良
- 營業現金流 > 淨利：現金轉換品質佳
- 自由現金流（營業CF - 資本支出）是否充裕？

---

## 步驟五：輸出

1. 儲存 HTML 檔案至工作目錄，檔名格式：`{公司縮寫}_{股票代碼}_analysis.html`
2. 提供 `computer://` 下載連結
3. 用 2-3 句話摘要三大維度的核心發現

---

## 注意事項

- Goodinfo.tw 抓取時若 `CLIENT_KEY` 失效，重新計算 `days_adjusted`（使用當前時間戳）
- 若某年度數據缺失（顯示為 `-` 或空白），在圖表中以 `null` 處理，不要填入 0
- 金額單位統一為**億元**（Goodinfo.tw 預設顯示）
- 分析期間預設為**最近三年**（如 2022-2024），但可依用戶需求調整
- 此 skill 僅適用於**台灣上市/上櫃公司**（4位數股票代碼）
