"""
Markdown报告生成模块
生成分析报告
"""

import os
from typing import List, Dict
from datetime import datetime


def generate_report(
    file_path: str,
    summary: Dict,
    metrics: Dict,
    paired_trades: List[Dict],
    holdings: List[Dict],
    type_metrics: Dict,
    period_metrics: Dict,
    errors: List[Dict],
    output_dir: str
) -> str:
    """
    生成Markdown分析报告

    Args:
        file_path: 原始交割单文件路径
        summary: 交割单摘要
        metrics: 核心指标
        paired_trades: 配对交易列表
        holdings: 持仓列表
        type_metrics: 按类型分类指标
        period_metrics: 按持有期限分类指标
        errors: 错误日志
        output_dir: 输出目录

    Returns:
        str: 生成的报告文件路径
    """
    os.makedirs(output_dir, exist_ok=True)

    date_str = datetime.now().strftime('%Y-%m-%d')
    report_path = os.path.join(output_dir, f'分析报告_{date_str}.md')

    # 持仓已在analysis.py步骤5合并，此处直接使用
    # holdings 已经是合并后的持仓列表（含当前价格和浮动盈亏）

    # 生成报告内容
    content = _generate_content(
        file_path, summary, metrics, paired_trades,
        holdings, type_metrics, period_metrics, errors
    )

    # 写入文件
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return report_path


def _generate_content(
    file_path: str,
    summary: Dict,
    metrics: Dict,
    paired_trades: List[Dict],
    holdings: List[Dict],
    type_metrics: Dict,
    period_metrics: Dict,
    errors: List[Dict]
) -> str:
    """生成报告内容"""

    lines = []

    # 标题
    lines.append("# 股票交易分析报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 1. 数据概览
    lines.append("## 1. 数据概览")
    lines.append("")
    lines.append(f"- **交割单文件**: `{file_path}`")
    lines.append(f"- **总记录数**: {summary.get('total_records', 0)} 条")
    lines.append(f"- **买入交易**: {summary.get('buy_count', 0)} 笔")
    lines.append(f"- **卖出交易**: {summary.get('sell_count', 0)} 笔")

    if summary.get('date_range'):
        dr = summary['date_range']
        lines.append(f"- **交易时间范围**: {dr['start']} 至 {dr['end']}")

    lines.append("")

    # 2. 核心指标
    lines.append("## 2. 核心指标（全部交易）")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总交易笔数 | {metrics['total_trades']} |")
    lines.append(f"| 盈利笔数 | {metrics['win_count']} |")
    lines.append(f"| 亏损笔数 | {metrics['loss_count']} |")
    lines.append(f"| **胜率** | **{metrics['win_rate']:.2%}** |")
    lines.append(f"| 平均盈利 | ¥{metrics['avg_profit']:.2f} |")
    lines.append(f"| 平均亏损 | ¥{metrics['avg_loss']:.2f} |")
    lines.append(f"| **赔率(盈亏比)** | **{metrics['odds']:.2f}** |")
    lines.append(f"| **凯利仓位** | **{metrics['kelly']:.2%}** |")
    lines.append(f"| 半凯利仓位 | {metrics.get('half_kelly', metrics['kelly']/2):.2%} |")
    lines.append(f"| 1/4凯利仓位 | {metrics.get('quarter_kelly', metrics['kelly']/4):.2%} |")
    lines.append(f"| 总盈亏 | ¥{metrics['total_profit']:.2f} |")

    if metrics.get('holdings_count', 0) > 0:
        lines.append(f"| 持仓数量 | {metrics['holdings_count']} |")
        lines.append(f"| 纳入持仓计算 | {'是' if metrics.get('include_holdings') else '否'} |")

    lines.append("")

    # 3. 按证券类型详细统计
    if type_metrics:
        lines.append("## 3. 按证券类型详细统计")
        lines.append("")
        lines.append("| 类型 | 交易笔数 | 胜率 | 赔率 | 凯利 | 半凯利 | 1/4凯利 | 总盈亏 |")
        lines.append("|------|----------|------|------|------|--------|---------|--------|")

        for sec_type, type_metric in type_metrics.items():
            win_rate = type_metric.get('win_rate', 0)
            odds = type_metric.get('odds', 0)
            kelly = type_metric.get('kelly', 0)
            half_kelly = type_metric.get('half_kelly', kelly/2)
            quarter_kelly = type_metric.get('quarter_kelly', kelly/4)
            total_profit = type_metric.get('total_profit', 0)
            total_trades = type_metric.get('total_trades', 0)

            lines.append(f"| {sec_type} | {total_trades} | {win_rate:.1%} | {odds:.2f} | {kelly:.1%} | {half_kelly:.1%} | {quarter_kelly:.1%} | ¥{total_profit:.2f} |")

        lines.append("")

        # 证券类型交易建议
        lines.append("### 证券类型交易建议")
        lines.append("")
        for sec_type, type_metric in type_metrics.items():
            win_rate = type_metric.get('win_rate', 0)
            odds = type_metric.get('odds', 0)
            kelly = type_metric.get('kelly', 0)
            half_kelly = type_metric.get('half_kelly', kelly/2)
            quarter_kelly = type_metric.get('quarter_kelly', kelly/4)
            total_trades = type_metric.get('total_trades', 0)
            total_profit = type_metric.get('total_profit', 0)

            if total_trades < 10:
                lines.append(f"### {sec_type}")
                lines.append(f"样本不足({total_trades}笔)，建议积累更多数据后再做判断")
            else:
                # 评级
                if win_rate >= 0.6 and odds >= 1.5:
                    rating = "⭐ 优秀"
                elif win_rate >= 0.5 and odds >= 1.2:
                    rating = "✅ 良好"
                elif win_rate >= 0.4:
                    rating = "⚠️ 一般"
                else:
                    rating = "❌ 较差"

                advice = _get_trading_advice(win_rate, odds, kelly)
                lines.append(f"### {sec_type} {rating}")
                lines.append(advice)

        lines.append("")

    # 4. 按持有期限详细统计
    if period_metrics:
        lines.append("## 4. 按持有期限详细统计")
        lines.append("")
        lines.append("| 持有期限 | 交易笔数 | 胜率 | 赔率 | 凯利 | 半凯利 | 1/4凯利 | 总盈亏 |")
        lines.append("|----------|----------|------|------|------|--------|---------|--------|")

        period_order = ['1周以内', '1月以内', '2月以内', '3月以内', '6月以内', '1年以内', '1年以上']
        for period in period_order:
            if period in period_metrics:
                pm = period_metrics[period]
                win_rate = pm.get('win_rate', 0)
                odds = pm.get('odds', 0)
                kelly = pm.get('kelly', 0)
                half_kelly = pm.get('half_kelly', kelly/2)
                quarter_kelly = pm.get('quarter_kelly', kelly/4)
                count = pm.get('total_trades', pm.get('count', 0))
                total_profit = pm.get('total_profit', 0)

                lines.append(f"| {period} | {count} | {win_rate:.1%} | {odds:.2f} | {kelly:.1%} | {half_kelly:.1%} | {quarter_kelly:.1%} | ¥{total_profit:.2f} |")

        lines.append("")

        # 持有期限交易建议
        lines.append("### 持有期限交易建议")
        lines.append("")
        best_period = None
        best_kelly = 0

        for period in period_order:
            if period in period_metrics:
                pm = period_metrics[period]
                kelly = pm.get('kelly', 0)
                win_rate = pm.get('win_rate', 0)
                odds = pm.get('odds', 0)
                count = pm.get('total_trades', pm.get('count', 0))

                if count >= 10 and kelly > best_kelly:
                    best_kelly = kelly
                    best_period = period

                if count < 5:
                    lines.append(f"### {period}")
                    lines.append(f"样本不足({count}笔)，建议继续观察")
                else:
                    advice = _get_trading_advice(win_rate, odds, kelly)
                    lines.append(f"### {period}")
                    lines.append(advice)

        lines.append("")

        if best_period:
            lines.append(f"### 💡 最佳持有期限")
            lines.append(f"{best_period}，凯利仓位 {best_kelly:.1%}，建议重点关注")

        lines.append("")

    # 5. 综合评估与资金管理建议
    lines.append("## 5. 综合评估与资金管理建议")
    lines.append("")

    kelly_pct = metrics.get('kelly', 0)
    win_rate = metrics.get('win_rate', 0)
    odds = metrics.get('odds', 0)

    lines.append("### 5.1 交易表现评估")
    lines.append("")
    if win_rate >= 0.6:
        lines.append(f"- **胜率评级**: ⭐ 优秀 ({win_rate:.1%})")
    elif win_rate >= 0.5:
        lines.append(f"- **胜率评级**: ✅ 良好 ({win_rate:.1%})")
    elif win_rate >= 0.4:
        lines.append(f"- **胜率评级**: ⚠️ 一般 ({win_rate:.1%})")
    else:
        lines.append(f"- **胜率评级**: ❌ 较差 ({win_rate:.1%})")

    if odds >= 1.5:
        lines.append(f"- **赔率评级**: ⭐ 优秀 ({odds:.2f})")
    elif odds >= 1.2:
        lines.append(f"- **赔率评级**: ✅ 良好 ({odds:.2f})")
    elif odds >= 1.0:
        lines.append(f"- **赔率评级**: ⚠️ 一般 ({odds:.2f})")
    else:
        lines.append(f"- **赔率评级**: ❌ 较差 ({odds:.2f})")

    # 综合评级
    overall = win_rate * odds
    if overall >= 0.9:
        lines.append(f"- **综合评级**: ⭐ 优秀 (胜率×赔率={overall:.2f})")
    elif overall >= 0.6:
        lines.append(f"- **综合评级**: ✅ 良好 (胜率×赔率={overall:.2f})")
    elif overall >= 0.4:
        lines.append(f"- **综合评级**: ⚠️ 一般 (胜率×赔率={overall:.2f})")
    else:
        lines.append(f"- **综合评级**: ❌ 较差 (胜率×赔率={overall:.2f})")

    lines.append("")
    lines.append("### 5.2 资金管理建议")
    lines.append("")
    lines.append("**凯利公式详解**:")
    lines.append("")
    lines.append("> Kelly% = (p × b - q) / b")
    lines.append("> - p = 胜率")
    lines.append("> - b = 赔率（盈亏比）")
    lines.append("> - q = 1 - p = 败率")
    lines.append("")
    lines.append(f"**您的数据**: 胜率={win_rate:.2%}, 赔率={odds:.2f}")
    lines.append("")
    lines.append("**仓位建议**:")
    lines.append("")
    lines.append(f"| 仓位类型 | 建议比例 | 说明 |")
    lines.append(f"|----------|----------|------|")
    lines.append(f"| 凯利仓位 | {kelly_pct:.1%} | 最优仓位，但波动较大 |")
    half_kelly = metrics.get('half_kelly', kelly_pct/2)
    quarter_kelly = metrics.get('quarter_kelly', kelly_pct/4)
    lines.append(f"| 半凯利 | {half_kelly:.1%} | 保守推荐，波动适中 |")
    lines.append(f"| 1/4凯利 | {quarter_kelly:.1%} | 最保守，安全边际高 |")
    lines.append("")

    if kelly_pct > 0.25:
        lines.append("> ⚠️ **注意**: 凯利仓位超过25%属于高仓位，建议:")
        lines.append("> - 风险厌恶者建议使用半凯利或1/4凯利仓位")
        lines.append("> - 做好止损纪律，单次亏损不超过总资金的2%")
    elif kelly_pct > 0.1:
        lines.append("> ✅ **适中**: 凯利仓位在10%-25%之间，风险可控")
    else:
        lines.append("> 💡 **偏低**: 凯利仓位低于10%，可适当增加投入或寻找更多机会")

    lines.append("")

    # 6. 持仓明细
    if holdings:
        lines.append("## 6. 当前持仓")
        lines.append("")
        lines.append("| 证券代码 | 证券名称 | 买入日期 | 买入价 | 数量 | 现价 | 浮动盈亏 | 盈亏比例 |")
        lines.append("|----------|----------|----------|--------|------|------|----------|----------|")

        for h in holdings:
            code = h.get('code', '')
            name = h.get('name', '')
            buy_date = h.get('buy_date', '')
            if hasattr(buy_date, 'strftime'):
                buy_date = buy_date.strftime('%Y-%m-%d')
            buy_price = h.get('buy_price', 0)
            quantity = h.get('quantity', 0)
            current_price = h.get('current_price')
            floating = h.get('floating_profit', 0)
            floating_pct = h.get('floating_profit_pct', 0)

            if current_price is not None and current_price != 'N/A':
                lines.append(f"| {code} | {name} | {buy_date} | ¥{buy_price:.2f} | {quantity} | ¥{current_price:.2f} | ¥{floating:.2f} | {floating_pct:.2f}% |")
            else:
                lines.append(f"| {code} | {name} | {buy_date} | ¥{buy_price:.2f} | {quantity} | N/A | N/A | N/A |")

        lines.append("")

    # 7. 错误日志
    if errors:
        lines.append("## 7. 处理日志")
        lines.append("")

        critical_errors = [e for e in errors if e.get('severity') == 'critical']
        warnings = [e for e in errors if e.get('severity') == 'warning']
        infos = [e for e in errors if e.get('severity') == 'info']

        if critical_errors:
            lines.append(f"### 严重错误 ({len(critical_errors)})")
            lines.append("")
            for e in critical_errors:
                lines.append(f"- [{e.get('type')}] {e.get('message')}")
            lines.append("")

        if warnings:
            lines.append(f"### 警告 ({len(warnings)})")
            lines.append("")
            for e in warnings:
                lines.append(f"- [{e.get('type')}] {e.get('message')}")
            lines.append("")

        if infos:
            lines.append(f"### 信息 ({len(infos)})")
            lines.append("")
            for e in infos:
                lines.append(f"- [{e.get('type')}] {e.get('message')}")
            lines.append("")

    # 8. 附录
    lines.append("## 8. 附录")
    lines.append("")
    lines.append("### 指标说明")
    lines.append("")
    lines.append("- **胜率**: 盈利交易笔数 / 总交易笔数")
    lines.append("- **赔率(盈亏比)**: 平均盈利金额 / 平均亏损金额")
    lines.append("- **凯利仓位**: (胜率 × 赔率 - 败率) / 赔率，表示应投入的资金比例")
    lines.append("- **半凯利**: 凯利仓位的一半，波动更小")
    lines.append("- **1/4凯利**: 凯利仓位的四分之一，最保守的仓位建议")
    lines.append("")

    return "\n".join(lines)


def _get_trading_advice(win_rate: float, odds: float, kelly: float) -> str:
    """根据指标生成交易建议"""
    if kelly <= 0:
        return "不建议交易，建议优化策略或等待更好机会"

    if win_rate >= 0.6 and odds >= 1.5:
        return f"表现优秀，建议保持，当前凯利仓位 {kelly:.1%}"
    elif win_rate >= 0.5 and odds >= 1.2:
        return f"表现良好，可适当参与，建议仓位 {kelly:.1%}（半凯利 {kelly/2:.1%} 更稳健）"
    elif win_rate >= 0.4:
        return f"表现一般，建议谨慎，使用半凯利 {kelly/2:.1%} 或 1/4凯利 {kelly/4:.1%}"
    else:
        return "表现较差，建议减少交易或优化策略"
