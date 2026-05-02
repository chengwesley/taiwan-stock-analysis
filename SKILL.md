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
| 推銷費用 | 推銷費用 |
| 管理費用 | 管理費用 |
| 研究發展費用 | R&D費用 |
| 營業利益（損失） | 營業利益 |
| 稅後淨利 | 稅後淨利（母公司） |
| 每股稅後盈餘(元) | EPS |

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
| 固定資產（增加）減少 | 資本支出（負值為增加） |
| 發放現金股利 | 現金股利 |

> 若 `推銷費用`、`稅後淨利`、`每股稅後盈餘(元)` 等欄位名稱在特定公司財報中略有差異，需迭代所有欄位名稱以關鍵字模糊比對（如 `'推銷' in k`、`'每股' in k and '盈餘' in k`）。

---

## 步驟二：計算衍生指標

從原始數據計算以下指標：

```python
# 費用率（各費用 / 營收）
sell_ratio   = sell_exp / revenue * 100
admin_ratio  = admin_exp / revenue * 100
rd_ratio     = rd_exp / revenue * 100
total_opex_ratio = (sell_exp + admin_exp + rd_exp) / revenue * 100

# 毛利率、營業利益率、淨利率
gross_margin = gross_profit / revenue * 100
op_margin    = op_income / revenue * 100
net_margin   = net_income / revenue * 100

# 流動比率、負債比率
current_ratio = current_assets / current_liabilities * 100
debt_ratio    = total_liabilities / total_assets * 100

# ROE、ROA
roe = net_income / equity * 100
roa = net_income / total_assets * 100

# 自由現金流（使用固定資產增減作為 capex 代理）
fcf = operating_cf + capex  # capex 為負值（資產增加）時 FCF = op_cf - |capex|
```

---

## 步驟二點五：三層驗證機制

每次抓取完財報數據後，執行以下三層驗證，結果存入 `result['verification']`。

---

### A. 資料來源標注（Provenance）

在 `result['metadata']` 中記錄完整的數據血緣：

```python
result['metadata'] = {
    'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%S+08:00'),
    'source': 'Goodinfo.tw',
    'source_urls': {
        'income_statement': f'https://goodinfo.tw/tw/StockFinDetail.asp?RPT_CAT=IS_YEAR&STOCK_ID={stock_id}',
        'balance_sheet':    f'https://goodinfo.tw/tw/StockFinDetail.asp?RPT_CAT=BS_YEAR&STOCK_ID={stock_id}',
        'cash_flow':        f'https://goodinfo.tw/tw/StockFinDetail.asp?RPT_CAT=CF_YEAR&STOCK_ID={stock_id}',
    },
    'mops_url':     f'https://mops.twse.com.tw/mops/web/t05st01?step=1&co_id={stock_id}&TYPEK=sii',
    'mops_url_otc': f'https://mops.twse.com.tw/mops/web/t05st01?step=1&co_id={stock_id}&TYPEK=otc',
    'years_covered': years[:3],
    'currency': 'TWD 億元',
}
```

---

### B. 合理性檢查（Sanity Check）

計算完衍生指標後，執行以下規則，產生 `result['verification']['sanity']` 列表：

```python
def sanity_check(metrics, years):
    """
    metrics 為 {year: {gross_margin, op_margin, net_margin,
                        current_ratio, debt_ratio, roe, roa}} 的字典
    回傳 warnings 列表，每項為 {'level': 'warn'|'error', 'field': str, 'msg': str}
    """
    warnings = []
    for yr in years:
        m = metrics.get(yr, {})

        gm = m.get('gross_margin')
        if gm is not None:
            if gm > 100:
                warnings.append({'level': 'error', 'field': f'{yr} 毛利率',
                    'msg': f'{gm:.1f}% 超過 100%，數據可能有誤'})
            elif gm < -50:
                warnings.append({'level': 'error', 'field': f'{yr} 毛利率',
                    'msg': f'{gm:.1f}% 低於 -50%，請確認是否為特殊損失年度'})

        cr = m.get('current_ratio')
        if cr is not None and cr < 0:
            warnings.append({'level': 'error', 'field': f'{yr} 流動比率',
                'msg': f'{cr:.1f}% 為負值，請檢查資產負債表數據'})

        dr = m.get('debt_ratio')
        if dr is not None and dr > 100:
            warnings.append({'level': 'warn', 'field': f'{yr} 負債比率',
                'msg': f'{dr:.1f}% 超過 100%，若非金融業則為警示訊號'})

        roe = m.get('roe')
        if roe is not None and roe > 100:
            warnings.append({'level': 'warn', 'field': f'{yr} ROE',
                'msg': f'{roe:.1f}% 超過 100%，可能為高槓桿，請確認股東權益是否偏低'})

    # 相鄰年度淨利率波動檢查
    nm_list = [(yr, metrics[yr].get('net_margin')) for yr in years if yr in metrics]
    for i in range(1, len(nm_list)):
        yr_prev, nm_prev = nm_list[i-1]
        yr_curr, nm_curr = nm_list[i]
        if nm_prev is not None and nm_curr is not None:
            if abs(nm_curr - nm_prev) > 30:
                warnings.append({'level': 'warn',
                    'field': f'{yr_prev}→{yr_curr} 淨利率',
                    'msg': f'波動 {nm_curr - nm_prev:+.1f} 個百分點，建議確認是否有一次性損益'})

    return warnings

result['verification'] = {
    'sanity': sanity_check(metrics_by_year, years[:3]),
    'sanity_pass': all(w['level'] != 'error' for w in warnings)
}
```

---

### C. MOPS 原始申報連結（D）

`result['metadata']['mops_url']`（上市）和 `mops_url_otc`（上櫃）已在步驟 A 記錄，儀表板的驗證列中以連結按鈕呈現，讓使用者可一鍵核對原始申報。

---

## 步驟三：建立 HTML 儀表板

**直接由 Claude 手寫完整 HTML**，不使用 Python 模板生成。參考 `references/dashboard_template.md` 的 CSS 與 Chart.js 規格。

### 儀表板架構

```
header（公司名稱 + 股票代碼 + 資料來源標注）
verify-bar（抓取時間 | 合理性檢查徽章 | MOPS連結按鈕 | Goodinfo原始連結）
verify-warnings（若 sanity warnings 不為空才渲染）
├── Tab 1：經營分析
│   ├── KPI Cards（5張）：含具體數字的 kpi-change 說明文字
│   ├── Insight Box（3-5條重點）：🔍 經營亮點
│   ├── Charts（2×2格）：營收+毛利率 / 費用堆疊 / 費用率折線 / 營業利益+利益率
│   └── Data Table：損益表明細（含「趨勢評估」欄）
├── Tab 2：獲利分析
│   ├── KPI Cards（5張）：含具體數字的 kpi-change 說明文字
│   ├── Insight Box：🔍 獲利亮點
│   ├── Charts（2×2格）：淨利+淨利率 / EPS / 三層利潤率 / 現金股利
│   └── Data Table：獲利能力彙總（含「趨勢評估」欄）
└── Tab 3：財務健全度
    ├── KPI Cards（5張）：含具體數字的 kpi-change 說明文字
    ├── Insight Box：🔍 財務健全度亮點
    ├── Charts（2×2格）：資產負債結構 / 現金流三表 / 流動+負債比率 / 現金趨勢
    └── Data Tables（左右並排）：資產負債表摘要 / 現金流量摘要（均含「趨勢評估」欄）
```

### KPI Card 規格

KPI card 的 `kpi-change` **必須包含具體數字**，不可只寫方向文字：

```html
<!-- ❌ 錯誤：沒有數字 -->
<div class="kpi-change up">▲ 持續成長</div>

<!-- ✅ 正確：含具體數字 + 背景說明 -->
<div class="kpi-change up">▲ +18.1% YoY（2024年68,596億），AI伺服器訂單驅動</div>
<div class="kpi-change neutral">■ 2022年59.6% → 2023年54.4% → 2024年V型反彈至56.1%</div>
<div class="kpi-change down">▼ 三年持續下滑 159% → 155% → 146%，首度低於150%警戒線</div>
```

**顏色規則：**
- 🟢 `green`（`border-left: 4px solid #38a169`）：正向指標
- 🔵 `blue`（`border-left: 4px solid #3182ce`）：中性指標
- 🟠 `orange`（`border-left: 4px solid #dd6b20`）：需關注
- 🔴 `red`（`border-left: 4px solid #e53e3e`）：警示

### 數據表格「趨勢評估」欄規格

**每張數據表格必須包含第四欄「趨勢評估」**，用簡短文字描述趨勢方向與意義：

```html
<thead>
  <tr><th>項目</th><th>2022</th><th>2023</th><th>2024</th><th>趨勢評估</th></tr>
</thead>
<tbody>
  <tr><td>稅後淨利（億元）</td><td>8,385</td><td>11,733</td><td class="up">▲ 創三年新高</td></tr>
  <tr><td>EPS（元）</td><td>32.34</td><td>45.25</td><td class="up">▲ 高速成長 +40%</td></tr>
  <tr><td>毛利率</td><td>54.4%</td><td>56.1%</td><td class="neutral">■ 高檔震盪</td></tr>
  <tr><td>負債比率</td><td>57.9%</td><td>61.4%</td><td class="down">▼ 突破60%，需關注</td></tr>
</tbody>
```

**趨勢評估文字規則：**
- `▲` + `class="up"`（綠色）：改善 / 成長 / 創高
- `▼` + `class="down"`（紅色）：惡化 / 衰退 / 低於警戒
- `■` + `class="neutral"`（灰色）：橫盤 / 高檔震盪 / 波動但無明顯方向
- 文字應包含**一個關鍵事實**（數字或判斷），不超過 12 字

### Chart.js 設定

- CDN：`https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.min.js`
- 所有圖表需設 `maintainAspectRatio: false`，container 高度固定 `240px`
- 組合圖（bar + line）使用雙 Y 軸（`yAxisID: 'y'` 和 `yAxisID: 'y2'`）
- Tab 切換：`onclick="switchTab('ops')"` 搭配 `event.target.classList.add('active')`

### 常見 HTML 格式錯誤（務必避免）

1. KPI card 中的 `kpi-change` div 結尾只能用 `</div>`，不能混入 `</td></tr>`
2. 所有 `<canvas>` 需包在 `class="chart-container"` 的 div 內（含固定高度 240px）
3. 數據表格的「趨勢評估」欄 `<td>` 需搭配顏色 class（`up`/`down`/`neutral`）

---

## 步驟四：Insight Box 撰寫規範

每個分頁的 insight box 標題用 `🔍 {分頁名}亮點`，包含 **4–5 條具體數字觀察**。

### 必須符合的格式要求

```
❌ 不合格：「營收有所成長」（無數字、無幅度）
❌ 不合格：「毛利率略有下降」（無具體數值）
✅ 合格：「三年營收 61,622 → 68,596 → 81,031 億，CAGR +14.6%，2025年加速成長 +18.1%，AI伺服器訂單驅動」
✅ 合格：「2023年營業CF為 -982 億（異常），係大量備料AI伺服器存貨所致；2024年存貨消化後強勁回復至 4,456 億，現金轉換能力確認」
```

**每條觀察應包含：**
1. **起點 → 終點數字**（或三年數列）
2. **幅度**（YoY %、CAGR、或絕對變化）
3. **原因推斷或意義**（一句話說明為什麼）

### 各分頁的核心觀察方向

**📊 經營分析亮點：**
- 三年營收趨勢與 CAGR，點名最新年的關鍵驅動因素
- 毛利率是否有結構性改善（品項組合 vs 成本控制）
- 費用率是否隨營收成長而下降（規模效益），研發投入是否維持
- 營業利益率的三年趨勢與費用攤薄效益

**💰 獲利分析亮點：**
- EPS 三年數列 + 最新年 YoY，是否創新高
- 淨利成長是否超過營收成長（利潤率擴張）
- ROE 趨勢，說明改善或惡化原因（淨利 vs 股東權益變化）
- 現金股利三年趨勢，換算配息率或成長幅度

**🏦 財務健全度亮點：**
- 流動比率三年趨勢，是否高於 150%（健康）或 200%（優異）
- 負債比率三年趨勢，是否接近或超過 60%（需關注）
- 現金部位變化，說明增減原因（配息、資本支出、CF 情況）
- 營業 CF 與淨利比較（> 1 為佳），自由現金流是否充裕

---

## 步驟五：輸出

1. 儲存 HTML 檔案至工作目錄，檔名格式：`{公司縮寫}_{股票代碼}_analysis.html`
2. 提供下載連結
3. 用 2–3 句話摘要三大維度的核心發現（含具體數字）
4. 附上驗證狀態：
   - 若有合理性警示（`sanity_pass == False`）→ 明確提醒用戶檢查具體欄位
   - 一律附上 MOPS 連結，讓用戶可自行核對原始申報

---

## 注意事項

- Goodinfo.tw 抓取時若 `CLIENT_KEY` 失效，重新計算 `days_adjusted`（使用當前時間戳）
- 若某年度數據缺失（顯示為 `-` 或空白），在圖表中以 `null` 處理，不要填入 0
- 金額單位統一為**億元**（Goodinfo.tw 預設顯示）
- 分析期間預設為**最近三年**，但可依用戶需求調整
- 此 skill 僅適用於**台灣上市/上櫃公司**（4位數股票代碼）
- 欄位名稱因公司不同略有差異，抓取時需以關鍵字模糊比對而非完全匹配
