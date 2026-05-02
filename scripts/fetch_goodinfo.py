#!/usr/bin/env python3
"""
fetch_goodinfo.py
從 Goodinfo.tw 抓取台灣股票財報數據，含三層驗證機制（Provenance / Sanity / MOPS連結）
用法：python fetch_goodinfo.py <股票代碼>
範例：python fetch_goodinfo.py 2317
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import sys


# ─── 抓取層 ───────────────────────────────────────────────

def get_client_key():
    tz_offset = -480  # 台灣 UTC+8
    now_ms = time.time() * 1000
    days_since_epoch = now_ms / 86400000
    days_adjusted = days_since_epoch - tz_offset / 1440
    client_key = f"2.8|38057.1435627105|46946.0324515993|{tz_offset}|{days_adjusted}|{days_adjusted}"
    return client_key, days_adjusted

def fetch_report(stock_id, rpt_cat, days_adjusted, client_key):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://goodinfo.tw/'
    }
    cookies = {'CLIENT_KEY': client_key}
    url = f"https://goodinfo.tw/tw/StockFinDetail.asp?RPT_CAT={rpt_cat}&STOCK_ID={stock_id}&REINIT={days_adjusted:.10f}"
    r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    r.encoding = 'utf-8'
    return BeautifulSoup(r.text, 'html.parser')

def parse_table(soup):
    """解析 Goodinfo 財報表格，返回 {欄位名: {年度: 數值}} 的字典"""
    tables = soup.find_all('table')
    if len(tables) < 7:
        return {}, []

    t = tables[6]  # 財報數據在第7個表格（index=6）
    rows = t.find_all('tr')
    years = []
    data = {}

    for i, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        if not cells:
            continue
        row_data = [c.get_text(strip=True) for c in cells]

        if i == 0 and any(y in row_data for y in ['2025', '2024', '2023', '2022', '2021', '2020']):
            for val in row_data[1:]:
                if len(val) == 4 and val.isdigit():
                    years.append(val)
            continue

        if len(row_data) >= 3 and row_data[0]:
            field_name = row_data[0]
            values = {}
            val_cols = row_data[1:]
            for j, yr in enumerate(years):
                if j * 2 < len(val_cols):
                    raw = val_cols[j * 2]
                    try:
                        values[yr] = float(raw.replace(',', ''))
                    except Exception:
                        values[yr] = None
            if values:
                data[field_name] = values

    return data, years


# ─── 驗證層 A：資料來源標注 ────────────────────────────────

def build_metadata(stock_id, years):
    return {
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


# ─── 驗證層 B：合理性檢查 ──────────────────────────────────

def sanity_check(metrics_by_year, years):
    """
    metrics_by_year: {year: {gross_margin, op_margin, net_margin,
                              current_ratio, debt_ratio, roe, roa}}
    回傳 warnings 列表，每項為 {'level': 'warn'|'error', 'field': str, 'msg': str}
    """
    warnings = []

    for yr in years:
        m = metrics_by_year.get(yr, {})

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
    nm_list = [(yr, metrics_by_year[yr].get('net_margin'))
               for yr in years if yr in metrics_by_year]
    for i in range(1, len(nm_list)):
        yr_prev, nm_prev = nm_list[i - 1]
        yr_curr, nm_curr = nm_list[i]
        if nm_prev is not None and nm_curr is not None:
            delta = nm_curr - nm_prev
            if abs(delta) > 30:
                warnings.append({'level': 'warn',
                    'field': f'{yr_prev}→{yr_curr} 淨利率',
                    'msg': f'波動 {delta:+.1f} 個百分點，建議確認是否有一次性損益'})

    return warnings


# ─── 主流程 ───────────────────────────────────────────────

def fetch_all(stock_id):
    client_key, days_adjusted = get_client_key()
    result = {'stock_id': stock_id}

    print(f"正在抓取 {stock_id} 損益表...")
    is_soup = fetch_report(stock_id, 'IS_YEAR', days_adjusted, client_key)
    is_data, years = parse_table(is_soup)
    result['income_statement'] = is_data
    result['years'] = years

    time.sleep(1)
    print(f"正在抓取 {stock_id} 資產負債表...")
    bs_soup = fetch_report(stock_id, 'BS_YEAR', days_adjusted, client_key)
    bs_data, _ = parse_table(bs_soup)
    result['balance_sheet'] = bs_data

    time.sleep(1)
    print(f"正在抓取 {stock_id} 現金流量表...")
    cf_soup = fetch_report(stock_id, 'CF_YEAR', days_adjusted, client_key)
    cf_data, _ = parse_table(cf_soup)
    result['cash_flow'] = cf_data

    # 驗證層 A：資料標注
    result['metadata'] = build_metadata(stock_id, years)

    return result


def run_verification(result, metrics_by_year):
    """在 fetch_all() 之後、建立儀表板之前呼叫。"""
    years = result['years'][:3]

    # 驗證層 B：合理性檢查
    warnings = sanity_check(metrics_by_year, years)
    sanity_pass = all(w['level'] != 'error' for w in warnings)

    result['verification'] = {
        'sanity': warnings,
        'sanity_pass': sanity_pass,
    }

    if warnings:
        print(f"\n⚠️  合理性檢查發現 {len(warnings)} 項警示：")
        for w in warnings:
            icon = '❌' if w['level'] == 'error' else '⚠️ '
            print(f"  {icon} [{w['field']}] {w['msg']}")
    else:
        print("✅ 合理性檢查通過，所有指標在合理範圍內")

    # 驗證層 C：MOPS 連結（已在 metadata 中）
    print(f"📋 MOPS 官方申報（上市）：{result['metadata']['mops_url']}")

    return result


if __name__ == '__main__':
    stock_id = sys.argv[1] if len(sys.argv) > 1 else '2330'
    data = fetch_all(stock_id)

    is_d = data['income_statement']
    bs_d = data['balance_sheet']
    cf_d = data['cash_flow']
    years = data['years'][:3]

    # 計算衍生指標（示範用）
    def g(table, key, yr):
        return table.get(key, {}).get(yr)
    def safe(a, b): return a / b * 100 if (a is not None and b) else None

    metrics_by_year = {}
    for yr in years:
        rev_key  = next((k for k in is_d if '營業收入' in k), None)
        gp_key   = next((k for k in is_d if '毛利' in k and '淨額' not in k), None)
        ni_key   = next((k for k in is_d if '稅後淨利' in k), None)
        ca_key   = next((k for k in bs_d if '流動資產合計' in k), None)
        cl_key   = next((k for k in bs_d if '流動負債合計' in k), None)
        tl_key   = next((k for k in bs_d if '負債總額' in k), None)
        ta_key   = next((k for k in bs_d if '資產總額' in k), None)
        eq_key   = next((k for k in bs_d if '股東權益總額' in k), None)

        rev = g(is_d, rev_key, yr) if rev_key else None
        gp  = g(is_d, gp_key,  yr) if gp_key  else None
        ni  = g(is_d, ni_key,  yr) if ni_key  else None
        ca  = g(bs_d, ca_key,  yr) if ca_key  else None
        cl  = g(bs_d, cl_key,  yr) if cl_key  else None
        tl  = g(bs_d, tl_key,  yr) if tl_key  else None
        ta  = g(bs_d, ta_key,  yr) if ta_key  else None
        eq  = g(bs_d, eq_key,  yr) if eq_key  else None

        metrics_by_year[yr] = {
            'gross_margin':  safe(gp, rev),
            'net_margin':    safe(ni, rev),
            'current_ratio': safe(ca, cl),
            'debt_ratio':    safe(tl, ta),
            'roe':           safe(ni, eq),
            'roa':           safe(ni, ta),
        }

    data = run_verification(data, metrics_by_year)

    print(f"\n=== {stock_id} 財報摘要 ===")
    print(f"年度: {years}")
    for yr in years:
        rev_key = next((k for k in is_d if '營業收入' in k), None)
        eps_key = next((k for k in is_d if '每股' in k and '盈餘' in k), None)
        rev = g(is_d, rev_key, yr) if rev_key else None
        eps = g(is_d, eps_key, yr) if eps_key else None
        print(f"  {yr}: 營收={rev}億, EPS={eps}元")

    out_file = f'{stock_id}_raw_data.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n原始數據（含驗證結果）已存至 {out_file}")
