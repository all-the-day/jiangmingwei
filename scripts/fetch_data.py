#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A股业绩预告数据采集脚本
数据源：东方财富网
"""

import requests
import json
import os
from datetime import datetime

class EastMoneyYJYG:
    """东方财富网业绩预告数据采集"""

    def __init__(self):
        self.url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Referer': 'https://data.eastmoney.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def get_yjyg(self, report_date=None, page=1, page_size=500):
        """
        获取业绩预告数据

        Args:
            report_date: 报告期，如 '2024-12-31'，默认为最新季度
            page: 页码
            page_size: 每页条数

        Returns:
            list: 业绩预告数据列表
        """
        if report_date is None:
            # 自动计算最新报告期
            now = datetime.now()
            year = now.year
            month = now.month
            if month <= 4:
                report_date = f"{year-1}-12-31"
            elif month <= 7:
                report_date = f"{year}-03-31"
            elif month <= 10:
                report_date = f"{year}-06-30"
            else:
                report_date = f"{year}-09-30"

        all_data = []
        current_page = 1

        while True:
            params = {
                'reportName': 'RPT_PUBLIC_OP_NEWPREDICT',
                'columns': 'ALL',
                'pageNumber': current_page,
                'pageSize': page_size,
                'sortColumns': 'NOTICE_DATE,SECURITY_CODE',
                'sortTypes': '-1,-1',
                'filter': f"(REPORT_DATE='{report_date}')",
                'source': 'WEB',
                'client': 'WEB'
            }

            try:
                response = requests.get(self.url, headers=self.headers, params=params, timeout=30)
                result = response.json()

                if result.get('success') and result.get('result'):
                    data = result['result'].get('data', [])
                    if not data:
                        break
                    all_data.extend(data)

                    total = result['result'].get('count', 0)
                    if current_page * page_size >= total:
                        break
                    current_page += 1
                else:
                    break
            except Exception as e:
                print(f"请求失败: {e}")
                break

        return all_data, report_date


def format_number(value, unit='亿'):
    """格式化数字显示（API返回单位是元）"""
    if value is None:
        return '-'
    try:
        num = float(value)
        if unit == '亿':
            return f"{num/100000000:.2f}"  # 元 -> 亿元
        return f"{num:.2f}"
    except:
        return '-'


def format_percent(value):
    """格式化百分比显示"""
    if value is None:
        return '-'
    try:
        return f"{float(value):.2f}%"
    except:
        return '-'


def get_type_class(predict_type):
    """根据预告类型返回CSS类名"""
    if predict_type is None:
        return ''
    if predict_type in ['预增', '扭亏', '略增', '续盈']:
        return 'type-up'
    elif predict_type in ['预减', '首亏', '略减', '续亏']:
        return 'type-down'
    return ''


def generate_html(data, report_date, output_path):
    """生成HTML页面"""

    # 按同比增长排序（取上限值，降序）
    def sort_key(item):
        try:
            val = item.get('ADD_AMP_UPPER') or item.get('ADD_AMP_LOWER')
            return float(val) if val else float('-inf')
        except:
            return float('-inf')

    sorted_data = sorted(data, key=sort_key, reverse=True)

    # 生成表格行
    rows = []
    for item in sorted_data:
        notice_date = item.get('NOTICE_DATE', '-')
        if notice_date and notice_date != '-':
            notice_date = notice_date[:10]

        code = item.get('SECURITY_CODE', '-')
        name = item.get('SECURITY_NAME_ABBR', '-')
        market = item.get('TRADE_MARKET', '-')
        predict_type = item.get('PREDICT_TYPE', '-')
        type_class = get_type_class(predict_type)

        # 预告净利润（区间，单位：万元 -> 亿元）
        profit_low = format_number(item.get('PREDICT_AMT_LOWER'))
        profit_up = format_number(item.get('PREDICT_AMT_UPPER'))
        if profit_low == profit_up:
            profit = profit_low
        elif profit_low == '-' and profit_up != '-':
            profit = profit_up
        elif profit_up == '-' and profit_low != '-':
            profit = profit_low
        else:
            profit = f"{profit_low} ~ {profit_up}"

        # 同比增长（区间）
        amp_low = format_percent(item.get('ADD_AMP_LOWER'))
        amp_up = format_percent(item.get('ADD_AMP_UPPER'))
        if amp_low == amp_up:
            amp = amp_low
        elif amp_low == '-' and amp_up != '-':
            amp = amp_up
        elif amp_up == '-' and amp_low != '-':
            amp = amp_low
        else:
            amp = f"{amp_low} ~ {amp_up}"

        rows.append(f'''        <tr>
          <td>{notice_date}</td>
          <td>{code}</td>
          <td>{name}</td>
          <td>{market}</td>
          <td class="{type_class}">{predict_type}</td>
          <td>{profit}</td>
          <td>{amp}</td>
        </tr>''')

    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>A股业绩预告</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="container">
    <h1>A股业绩预告</h1>
    <p class="info">
      报告期：{report_date} | 数据来源：东方财富网 | 更新时间：{update_time}
    </p>
    <p class="info">共 {len(sorted_data)} 条记录，按归母净利润同比增长从高到低排列</p>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>披露日期</th>
            <th>股票代码</th>
            <th>公司名称</th>
            <th>交易市场</th>
            <th>预告性质</th>
            <th>预告净利润(亿)</th>
            <th>同比增长</th>
          </tr>
        </thead>
        <tbody>
{chr(10).join(rows)}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"已生成 {output_path}，共 {len(sorted_data)} 条记录")


def main():
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    output_path = os.path.join(project_dir, 'docs', 'index.html')

    print("开始采集A股业绩预告数据...")

    client = EastMoneyYJYG()
    data, report_date = client.get_yjyg()

    print(f"采集完成，共 {len(data)} 条记录")

    generate_html(data, report_date, output_path)


if __name__ == '__main__':
    main()
