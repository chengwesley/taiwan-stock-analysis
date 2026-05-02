# HTML 儀表板模板規格

## CSS 樣式核心

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Microsoft JhengHei', 'Noto Sans TC', sans-serif; background: #f0f4f8; color: #2d3748; }

/* Header 漸層 */
.header {
  background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 50%, #3182ce 100%);
  color: white; padding: 24px 32px;
  display: flex; justify-content: space-between; align-items: center;
}

/* Tab 切換 */
.tabs { display: flex; background: white; border-bottom: 2px solid #e2e8f0; padding: 0 32px; }
.tab { padding: 14px 24px; cursor: pointer; font-size: 0.95rem; font-weight: 600;
  color: #718096; border-bottom: 3px solid transparent; margin-bottom: -2px; transition: all 0.2s; }
.tab.active { color: #2b6cb0; border-bottom-color: #2b6cb0; }

/* KPI Cards */
.kpi-row { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.kpi-card { flex: 1; min-width: 180px; background: white; border-radius: 12px;
  padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.07); border-left: 4px solid #3182ce; }
.kpi-card.green { border-left-color: #38a169; }
.kpi-card.orange { border-left-color: #dd6b20; }
.kpi-card.red { border-left-color: #e53e3e; }
.kpi-card.purple { border-left-color: #805ad5; }
.kpi-label { font-size: 0.78rem; color: #718096; margin-bottom: 6px; font-weight: 500; text-transform: uppercase; }
.kpi-value { font-size: 1.7rem; font-weight: 700; color: #2d3748; }
.kpi-change { font-size: 0.82rem; margin-top: 4px; }
.up { color: #38a169; } .down { color: #e53e3e; } .neutral { color: #718096; }

/* Charts */
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
.chart-card { background: white; border-radius: 12px; padding: 22px; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
.chart-card.full { grid-column: 1 / -1; }
.chart-title { font-size: 0.92rem; font-weight: 700; color: #4a5568; margin-bottom: 16px;
  padding-bottom: 10px; border-bottom: 1px solid #f0f4f8; }
.chart-container { position: relative; height: 240px; }  /* 固定高度！必要 */

/* Tables */
.data-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.data-table th { background: #2b6cb0; color: white; padding: 10px 14px; text-align: center; }
.data-table td { padding: 9px 14px; text-align: right; border-bottom: 1px solid #e2e8f0; }
.data-table tr:nth-child(even) td { background: #f7fafc; }
.data-table td:first-child { text-align: left; font-weight: 500; }
.data-table .section-header td { background: #ebf8ff; color: #2b6cb0; font-weight: 700; }
.data-table .total-row td { background: #e6fffa; color: #276749; font-weight: 700; }

/* Insight Box */
.insight-box { background: linear-gradient(135deg, #ebf8ff, #e6fffa);
  border: 1px solid #bee3f8; border-radius: 12px; padding: 18px 22px; margin-bottom: 20px; }
.insight-box h3 { color: #2b6cb0; font-size: 0.9rem; margin-bottom: 10px; }
.insight-box ul { list-style: none; }
.insight-box ul li { font-size: 0.87rem; color: #4a5568; padding: 3px 0;
  padding-left: 18px; position: relative; }
.insight-box ul li::before { content: '▸'; position: absolute; left: 0; color: #3182ce; }
```

## KPI Card HTML 結構（正確範例）

```html
<div class="kpi-card green">
  <div class="kpi-label">指標名稱</div>
  <div class="kpi-value">數值</div>
  <div class="kpi-change up">▲ 說明文字</div>
</div>
```

⚠️ **常見錯誤**：`kpi-change` 的結尾必須是 `</div>`，絕對不能是 `</td></tr>`

## Chart.js 組合圖（雙Y軸）範例

```javascript
new Chart(document.getElementById('myChart'), {
  type: 'bar',
  data: {
    labels: ['2022', '2023', '2024'],
    datasets: [
      { 
        label: '數值 (億元)', 
        data: [100, 120, 140], 
        backgroundColor: 'rgba(49,130,206,0.15)',
        borderColor: '#3182ce', borderWidth: 2,
        yAxisID: 'y'   // 左軸
      },
      { 
        label: '比率 (%)', 
        data: [10, 15, 20], 
        type: 'line',
        borderColor: '#38a169', backgroundColor: '#38a169',
        pointRadius: 5, tension: 0.3,
        yAxisID: 'y2'  // 右軸
      }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    scales: {
      x: { grid: { display: false } },
      y: { grid: { color: 'rgba(0,0,0,0.05)' } },
      y2: { 
        position: 'right', 
        grid: { display: false },
        ticks: { callback: v => v + '%' }
      }
    }
  }
});
```

## Tab 切換 JavaScript

```javascript
function switchTab(name) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  event.target.classList.add('active');
}
```

Tab HTML：
```html
<div class="tab active" onclick="switchTab('ops')">📊 經營分析</div>
<div class="tab" onclick="switchTab('profit')">💰 獲利分析</div>
<div class="tab" onclick="switchTab('finance')">🏦 財務健全度</div>
```

## 完整 HTML 骨架

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>{公司名稱} ({股票代碼}) 三維財務分析</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.min.js"></script>
  <style>/* 貼入上方所有 CSS */</style>
</head>
<body>
  <!-- Header -->
  <div class="header">
    <div>
      <h1>{公司名稱} ({股票代碼}) 財務分析儀表板</h1>
      <div class="subtitle">資料來源：Goodinfo.tw｜分析期間：{起年} – {迄年}｜金額單位：億元 (NTD)</div>
    </div>
    <div class="badge">🏢 {產業類別}</div>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    <div class="tab active" onclick="switchTab('ops')">📊 經營分析</div>
    <div class="tab" onclick="switchTab('profit')">💰 獲利分析</div>
    <div class="tab" onclick="switchTab('finance')">🏦 財務健全度</div>
  </div>

  <!-- Tab 1: 經營分析 -->
  <div id="ops" class="tab-content active">
    <!-- 5個 KPI Cards -->
    <!-- Insight Box -->
    <!-- 2×2 Charts Grid -->
    <!-- 損益表 Data Table -->
  </div>

  <!-- Tab 2: 獲利分析 -->
  <div id="profit" class="tab-content">
    <!-- 5個 KPI Cards -->
    <!-- Insight Box -->
    <!-- 2×2 Charts Grid -->
    <!-- 獲利彙總 Data Table -->
  </div>

  <!-- Tab 3: 財務健全度 -->
  <div id="finance" class="tab-content">
    <!-- 5個 KPI Cards -->
    <!-- Insight Box -->
    <!-- 2×2 Charts Grid -->
    <!-- 左右並排：資產負債 + 現金流量 Tables -->
  </div>

  <script>/* 所有 Chart.js 初始化 + switchTab 函數 */</script>
</body>
</html>
```
