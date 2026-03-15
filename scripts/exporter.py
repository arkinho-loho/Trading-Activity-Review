"""
Excel导出模块
将分析结果导出为Excel文件
"""

import pandas as pd
from typing import List, Dict
import os
from datetime import datetime


def merge_holdings(holdings: List[Dict]) -> List[Dict]:
    """
    合并同一证券代码的持仓

    Args:
        holdings: 持仓列表

    Returns:
        List[Dict]: 合并后的持仓列表
    """
    if not holdings:
        return []

    # 按证券代码分组
    merged = {}

    for h in holdings:
        code = h.get('code', '')
        if code not in merged:
            merged[code] = {
                'code': code,
                'name': h.get('name', ''),
                'quantity': 0,
                'total_cost': 0,  # 总成本
                'buy_commission': 0,
                'security_type': h.get('security_type', ''),
            }

        # 累加数量和成本
        qty = h.get('quantity', 0)
        price = h.get('buy_price', 0)
        merged[code]['quantity'] += qty
        merged[code]['total_cost'] += price * qty
        merged[code]['buy_commission'] += h.get('buy_commission', 0)

        # 保留最新的买入日期（按时间倒序，第一条就是最近的）
        if 'buy_date' not in merged[code]:
            merged[code]['buy_date'] = h.get('buy_date', '')

    # 计算加权平均成本
    result = []
    for code, data in merged.items():
        if data['quantity'] > 0:
            avg_price = data['total_cost'] / data['quantity']
            result.append({
                'code': code,
                'name': data['name'],
                'buy_date': data.get('buy_date', ''),
                'buy_price': avg_price,
                'quantity': data['quantity'],
                'buy_commission': data['buy_commission'],
                'security_type': data['security_type'],
            })

    return result


def export_to_excel(
    paired_trades: List[Dict],
    holdings: List[Dict],
    metrics: Dict,
    type_metrics: Dict,
    period_metrics: Dict,
    output_dir: str
) -> str:
    """
    导出分析结果到Excel

    Args:
        paired_trades: 配对后的交易列表
        holdings: 持仓列表
        metrics: 核心指标
        type_metrics: 按类型分类的指标
        period_metrics: 按持有期限分类的指标
        output_dir: 输出目录

    Returns:
        str: 生成的Excel文件路径
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 生成文件名
    date_str = datetime.now().strftime('%Y-%m-%d')
    excel_path = os.path.join(output_dir, f'数据表格_{date_str}.xlsx')

    # 创建Excel写入器
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # 1. 核心指标
        metrics_df = pd.DataFrame([metrics])
        metrics_df.to_excel(writer, sheet_name='核心指标', index=False)

        # 2. 配对交易明细
        if paired_trades:
            trades_df = pd.DataFrame(paired_trades)
            # 格式化日期
            if 'buy_date' in trades_df.columns:
                trades_df['buy_date'] = pd.to_datetime(trades_df['buy_date']).dt.strftime('%Y-%m-%d')
            if 'sell_date' in trades_df.columns:
                trades_df['sell_date'] = pd.to_datetime(trades_df['sell_date']).dt.strftime('%Y-%m-%d')
            trades_df.to_excel(writer, sheet_name='配对交易', index=False)

        # 3. 持仓明细（已在analysis.py步骤5合并）
        if holdings:
            holdings_df = pd.DataFrame(holdings)
            if 'buy_date' in holdings_df.columns:
                holdings_df['buy_date'] = pd.to_datetime(holdings_df['buy_date']).dt.strftime('%Y-%m-%d')
            holdings_df.to_excel(writer, sheet_name='持仓明细', index=False)

        # 4. 按类型统计
        if type_metrics:
            type_data = []
            for sec_type, type_metric in type_metrics.items():
                type_metric_copy = type_metric.copy()
                type_metric_copy['security_type'] = sec_type
                type_data.append(type_metric_copy)

            type_df = pd.DataFrame(type_data)
            # 调整列顺序
            cols = ['security_type'] + [c for c in type_df.columns if c != 'security_type']
            type_df = type_df[cols]
            type_df.to_excel(writer, sheet_name='按类型统计', index=False)

        # 5. 按持有期限统计
        if period_metrics:
            period_data = []
            for period, period_metric in period_metrics.items():
                period_metric_copy = period_metric.copy()
                period_metric_copy['holding_period'] = period
                period_data.append(period_metric_copy)

            period_df = pd.DataFrame(period_data)
            # 调整列顺序
            cols = ['holding_period'] + [c for c in period_df.columns if c != 'holding_period']
            period_df = period_df[cols]
            period_df.to_excel(writer, sheet_name='按期限统计', index=False)

    return excel_path
