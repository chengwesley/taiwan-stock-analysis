#!/usr/bin/env python3
"""
fetch_goodinfo.py
從 Goodinfo.tw 抓取台灣股票財報數據
用法：python fetch_goodinfo.py <股票代碼>
範例：python fetch_goodinfo.py 3617
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import sys

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

        # 第一行通常含年度標題
        if i == 0 and any(y in row_data for y in ['2024', '2023', '2022', '2021', '2020']):
            # 取出年度列（奇數欄位是年度，偶數是%）
            for val in row_data[1:]:
                if len(val) == 4 and val.isdigit():
                    years.append(val)
            continue

        if len(row_data) >= 3 and row_data[0]:
            field_name = row_data[0]
            values = {}
            # 跳過第一欄（名稱），每兩欄取一個數值（奇數=金額，偶數=占比）
            val_cols = row_data[1:]
            for j, yr in enumerate(years):
                if j * 2 < len(val_cols):
                    raw = val_cols[j * 2]
                    try:
                        values[yr] = float(raw.replace(',', ''))
                    except:
                        values[yr] = None
            if values:
                data[field_name] = values

    return data, years

def fetch_all(stock_id):
    client_key, days_adjusted = get_client_key()
    result = {'stock_id': stock_id, 'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S')}

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

    return result

if __name__ == '__main__':
    stock_id = sys.argv[1] if len(sys.argv) > 1 else '3617'
    data = fetch_all(stock_id)

    # 輸出關鍵指標摘要
    is_d = data['income_statement']
    bs_d = data['balance_sheet']
    cf_d = data['cash_flow']
    years = data['years'][:3]  # 最近3年

    print(f"\n=== {stock_id} 財報摘要 ===")
    print(f"年度: {years}")

    for yr in years:
        rev_key = next((k for k in is_d if '營業收入' in k), None)
        rev = is_d.get(rev_key, {}).get(yr) if rev_key else None
        eps_key = next((k for k in is_d if '基本每股盈餘' in k), None)
        eps = is_d.get(eps_key, {}).get(yr) if eps_key else None
        print(f"  {yr}: 營收={rev}億, EPS={eps}元")

    # 存成 JSON 供後續使用
    out_file = f'{stock_id}_raw_data.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n原始數據已存至 {out_file}")
