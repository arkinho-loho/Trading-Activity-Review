"""
指标计算模块
计算胜率、赔率、凯利仓位等核心指标
"""

import pandas as pd
from typing import List, Dict, Optional
import numpy as np


def calculate_metrics(paired_trades: List[Dict], holdings: List[Dict] = None, include_holdings: bool = True) -> Dict:
    """
    计算核心交易指标

    Args:
        paired_trades: 配对后的交易列表
        holdings: 持仓列表（可选）
        include_holdings: 是否将持仓纳入计算

    Returns:
        Dict: 包含各项指标
    """
    # 处理平仓交易
    trades_df = pd.DataFrame(paired_trades)

    if trades_df.empty:
        return {
            'total_trades': 0,
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'odds': 0,
            'kelly': 0,
            'total_profit': 0,
            'profit_rate': 0,
        }

    # 基本统计
    total_trades = len(trades_df)
    win_count = len(trades_df[trades_df['profit'] > 0])
    loss_count = len(trades_df[trades_df['profit'] < 0])
    break_even = len(trades_df[trades_df['profit'] == 0])

    # 胜率
    win_rate = win_count / total_trades if total_trades > 0 else 0

    # 平均盈利和平均亏损
    profits = trades_df[trades_df['profit'] > 0]['profit']
    losses = trades_df[trades_df['profit'] < 0]['profit']

    avg_profit = profits.mean() if len(profits) > 0 else 0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else 0

    # 赔率（盈亏比）
    odds = avg_profit / avg_loss if avg_loss > 0 else 0

    # 凯利仓位
    kelly = calculate_kelly(win_rate, odds)
    # 半凯利仓位（更保守）
    half_kelly = kelly / 2 if kelly > 0 else 0
    # 1/4凯利仓位（最保守）
    quarter_kelly = kelly / 4 if kelly > 0 else 0

    # 总盈亏
    total_profit = trades_df['profit'].sum()

    # 盈利比例（盈利金额 / |亏损金额|）
    total_loss = abs(trades_df[trades_df['profit'] < 0]['profit'].sum()) if loss_count > 0 else 0
    profit_rate = total_profit / total_loss if total_loss > 0 else 0

    # 如果包含持仓，计算持仓浮动盈亏
    if include_holdings and holdings:
        holdings_with_profit = [h for h in holdings if h.get('floating_profit') is not None]
        if holdings_with_profit:
            floating_profit = sum(h['floating_profit'] for h in holdings_with_profit)
            total_profit += floating_profit

    return {
        'total_trades': total_trades,
        'win_count': win_count,
        'loss_count': loss_count,
        'break_even': break_even,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'odds': odds,
        'kelly': kelly,
        'half_kelly': half_kelly,
        'quarter_kelly': quarter_kelly,
        'total_profit': total_profit,
        'profit_rate': profit_rate,
        'holdings_count': len(holdings) if holdings else 0,
        'include_holdings': include_holdings,
    }


def calculate_kelly(win_rate: float, odds: float) -> float:
    """
    计算凯利仓位

    公式: Kelly% = (p * b - q) / b
    其中:
        p = 胜率
        q = 1 - p = 败率
        b = 赔率（盈亏比）

    Args:
        win_rate: 胜率 (0-1)
        odds: 赔率（盈亏比）

    Returns:
        float: 凯利仓位比例（负数表示不应下注）
    """
    if odds <= 0:
        return 0

    q = 1 - win_rate
    kelly = (win_rate * odds - q) / odds

    # 凯利仓位不能为负
    return max(0, kelly)


def calculate_metrics_by_type(paired_trades: List[Dict], holdings: List[Dict] = None) -> Dict:
    """
    按证券类型分类计算指标

    Args:
        paired_trades: 配对后的交易列表
        holdings: 持仓列表

    Returns:
        Dict: 按类型分类的指标
    """
    trades_df = pd.DataFrame(paired_trades)

    if trades_df.empty:
        return {}

    # 按证券类型分组
    if 'security_type' not in trades_df.columns:
        # 如果没有类型字段，尝试添加
        from classifier import classify_security
        trades_df['security_type'] = trades_df.apply(
            lambda row: classify_security(row['code'], row.get('name', '')),
            axis=1
        )

    result = {}
    for sec_type in trades_df['security_type'].unique():
        type_trades = trades_df[trades_df['security_type'] == sec_type].to_dict('records')
        type_holdings = [h for h in (holdings or []) if _get_holding_type(h) == sec_type]

        # 计算完整指标
        metrics = calculate_metrics(type_trades, type_holdings, include_holdings=False)
        result[sec_type] = metrics

    return result


def _get_holding_type(holding: Dict) -> str:
    """获取持仓的证券类型"""
    from classifier import classify_security
    return classify_security(holding.get('code', ''), holding.get('name', ''))


def calculate_metrics_by_holding_period(paired_trades: List[Dict]) -> Dict:
    """
    按持有期限分类计算指标

    Args:
        paired_trades: 配对后的交易列表

    Returns:
        Dict: 按持有期限分类的指标
    """
    from pairing import categorize_by_holding_period

    categories = categorize_by_holding_period(paired_trades)

    result = {}
    for period, data in categories.items():
        if data['count'] > 0:
            trades = data['trades']
            profits = [t['profit'] for t in trades]
            wins = len([p for p in profits if p > 0])
            losses = len([p for p in profits if p < 0])

            # 计算胜率
            win_rate = wins / data['count']

            # 计算赔率
            avg_profit = sum([p for p in profits if p > 0]) / wins if wins > 0 else 0
            avg_loss = abs(sum([p for p in profits if p < 0]) / losses) if losses > 0 else 0
            odds = avg_profit / avg_loss if avg_loss > 0 else 0

            # 计算凯利仓位
            kelly = calculate_kelly(win_rate, odds)
            half_kelly = kelly / 2 if kelly > 0 else 0
            quarter_kelly = kelly / 4 if kelly > 0 else 0

            result[period] = {
                'total_trades': data['count'],
                'win_count': wins,
                'loss_count': losses,
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'odds': odds,
                'kelly': kelly,
                'half_kelly': half_kelly,
                'quarter_kelly': quarter_kelly,
                'total_profit': data['profit'],
            }

    return result


def format_metrics(metrics: Dict) -> str:
    """
    格式化指标为可读字符串

    Args:
        metrics: 指标字典

    Returns:
        str: 格式化的字符串
    """
    lines = [
        "=" * 50,
        "交易指标统计",
        "=" * 50,
        f"总交易笔数: {metrics['total_trades']}",
        f"盈利笔数: {metrics['win_count']}",
        f"亏损笔数: {metrics['loss_count']}",
        f"胜率: {metrics['win_rate']:.2%}",
        f"平均盈利: ¥{metrics['avg_profit']:.2f}",
        f"平均亏损: ¥{metrics['avg_loss']:.2f}",
        f"赔率(盈亏比): {metrics['odds']:.2f}",
        f"凯利仓位: {metrics['kelly']:.2%}",
        f"半凯利仓位: {metrics.get('half_kelly', metrics['kelly']/2):.2%}",
        f"1/4凯利仓位: {metrics.get('quarter_kelly', metrics['kelly']/4):.2%}",
        f"总盈亏: ¥{metrics['total_profit']:.2f}",
    ]

    if metrics.get('holdings_count', 0) > 0:
        lines.append(f"持仓数量: {metrics['holdings_count']}")
        lines.append(f"纳入持仓计算: {'是' if metrics.get('include_holdings') else '否'}")

    lines.append("=" * 50)

    return "\n".join(lines)
