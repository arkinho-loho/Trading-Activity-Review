"""
股票交易分析主模块
整合所有模块，提供完整的分析流程
"""

import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import pandas as pd

from parser import parse_delivery_slip, get_summary
from classifier import classify_dataframe, get_type_statistics
from pairing import pair_trades, categorize_by_holding_period
# 价格获取已移除（只分析已平仓交易）
from metrics import (
    calculate_metrics,
    calculate_metrics_by_type,
    calculate_metrics_by_holding_period,
    format_metrics
)
from exporter import export_to_excel
from reporter import generate_report


def analyze_delivery_slip(
    file_path: str,
    include_holdings: bool = True,
    output_dir: str = None
) -> Dict:
    """
    分析交割单主函数

    Args:
        file_path: 交割单Excel文件路径
        include_holdings: 是否将持仓纳入计算
        output_dir: 输出目录（默认在交割单同目录创建output）

    Returns:
        Dict: 包含excel_path, report_path, error_log, summary
    """
    errors = []

    # 确定输出目录
    if output_dir is None:
        base_dir = os.path.dirname(os.path.abspath(file_path))
        output_dir = os.path.join(base_dir, '交易活动回顾_' + datetime.now().strftime('%Y-%m-%d'))

    print(f"开始分析交割单: {file_path}")
    print(f"输出目录: {output_dir}")

    # ========== 步骤1: 解析交割单 ==========
    print("\n[1/9] 解析交割单...")
    df, parse_errors = parse_delivery_slip(file_path)
    errors.extend(parse_errors)

    if df.empty:
        return {
            'excel_path': None,
            'report_path': None,
            'error_log': errors,
            'summary': {'error': '无法解析交割单'}
        }

    summary = get_summary(df)
    print(f"  - 有效交易: {summary['total_records']} 条 (买入{summary['buy_count']} + 卖出{summary['sell_count']})")

    # ========== 步骤2: 证券类型识别 ==========
    print("\n[2/9] 识别证券类型...")
    df = classify_dataframe(df)
    type_stats = get_type_statistics(df)
    print(f"  - 证券类型分布: {type_stats}")

    # ========== 步骤3: 过滤有效交易（已在parser中完成） ==========
    print("\n[3/9] 过滤有效交易...")
    # 已在parser中过滤，此处可做额外处理

    # ========== 步骤4: FIFO配对 ==========
    print("\n[4/9] 执行FIFO配对...")
    paired_trades, holdings, pair_errors = pair_trades(df)
    errors.extend(pair_errors)
    print(f"  - 配对交易: {len(paired_trades)} 笔")
    print(f"  - 未平仓持仓: {len(holdings)} 笔")

    # ========== 步骤5: 持仓处理（合并同一证券代码） ==========
    print("\n[5/9] 处理持仓（合并同一证券代码）...")

    # 合并同一证券代码的持仓
    from exporter import merge_holdings
    holdings = merge_holdings(holdings)
    print(f"  - 合并后持仓: {len(holdings)} 只")

    # 不获取持仓价格，不纳入胜率/赔率计算
    holdings_with_prices = holdings

    # ========== 步骤6: 计算指标 ==========
    # 只计算已平仓交易的胜率和赔率（不纳入持仓）
    print("\n[6/9] 计算交易指标...")
    metrics = calculate_metrics(paired_trades, holdings, include_holdings=False)
    print(f"  - 胜率: {metrics['win_rate']:.2%}")
    print(f"  - 赔率: {metrics['odds']:.2f}")
    print(f"  - 凯利仓位: {metrics['kelly']:.2%}")

    # ========== 步骤7: 分类统计 ==========
    print("\n[7/9] 分类统计...")
    type_metrics = calculate_metrics_by_type(paired_trades, holdings)
    period_metrics = calculate_metrics_by_holding_period(paired_trades)
    print(f"  - 证券类型: {len(type_metrics)} 种")
    print(f"  - 持有期限: {len(period_metrics)} 类")

    # ========== 步骤8: 生成报告 ==========
    print("\n[8/9] 生成报告...")

    # 导出Excel
    excel_path = export_to_excel(
        paired_trades,
        holdings_with_prices,
        metrics,
        type_metrics,
        period_metrics,
        output_dir
    )
    print(f"  - Excel: {excel_path}")

    # 生成Markdown报告（错误日志已合并到报告中）
    report_path = generate_report(
        file_path,
        summary,
        metrics,
        paired_trades,
        holdings_with_prices,
        type_metrics,
        period_metrics,
        errors,
        output_dir
    )
    print(f"  - 报告: {report_path}")

    # 构建返回结果
    result = {
        'excel_path': excel_path,
        'report_path': report_path,
        'error_log': errors,
        'summary': {
            'file_path': file_path,
            'total_records': summary['total_records'],
            'paired_trades': len(paired_trades),
            'holdings': len(holdings),
            'metrics': metrics,
            'output_dir': output_dir
        }
    }

    print("\n" + "=" * 50)
    print("分析完成!")
    print("=" * 50)

    return result


def get_user_confirmation(summary: Dict) -> str:
    """
    获取用户确认信息

    Args:
        summary: 交割单摘要

    Returns:
        str: 确认消息
    """
    lines = [
        "请确认以下信息：",
        "",
        f"文件: {summary.get('file_path', 'N/A')}",
        f"记录数: {summary.get('total_records', 0)} 条",
        f"有效交易: {summary.get('paired_trades', 0)} 笔",
        f"持仓数量: {summary.get('holdings', 0)} 笔",
        "",
        "是否将当前持仓纳入胜率/赔率计算？",
        "[1] 是 - 使用最新收盘价计算浮动盈亏",
        "[2] 否 - 仅统计已平仓交易",
    ]

    return "\n".join(lines)


def main():
    """测试入口"""
    import sys
    import io

    # 设置标准输出编码为 UTF-8，解决 Windows GBK 环境下的编码问题
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    if len(sys.argv) < 2:
        print("用法: python analysis.py <交割单文件路径>")
        print("示例: python analysis.py Desktop/交割单.xlsx")
        sys.exit(1)

    file_path = sys.argv[1]

    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)

    # 执行分析
    result = analyze_delivery_slip(file_path)

    # 打印结果
    print("\n" + format_metrics(result['summary']['metrics']))


if __name__ == '__main__':
    main()
