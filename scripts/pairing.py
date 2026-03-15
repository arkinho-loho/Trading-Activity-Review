"""
FIFO配对模块
使用先进先出算法对买卖交易进行配对
"""

import pandas as pd
from typing import List, Dict, Tuple
from datetime import datetime

from classifier import classify_security


class FIFOQueue:
    """FIFO队列，用于存储待配对的买入持仓"""

    def __init__(self):
        self.queue: List[Dict] = []

    def push(self, position: Dict):
        """添加持仓到队列"""
        self.queue.append(position)

    def pop(self) -> Dict:
        """取出最早的持仓"""
        if self.queue:
            return self.queue.pop(0)
        return None

    def is_empty(self) -> bool:
        """队列是否为空"""
        return len(self.queue) == 0

    def peek(self) -> Dict:
        """查看最早的持仓（不取出）"""
        if self.queue:
            return self.queue[0]
        return None

    def update_first(self, position: Dict):
        """更新最早的持仓"""
        if self.queue:
            self.queue[0] = position


def pair_trades(df: pd.DataFrame) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    FIFO配对买卖交易

    Args:
        df: 处理后的交易数据DataFrame

    Returns:
        Tuple[List[Dict], List[Dict], List[Dict]]:
        - paired_trades: 配对后的交易记录
        - holdings: 未平仓持仓
        - errors: 错误日志
    """
    paired_trades = []
    holdings = []
    errors = []

    if df.empty:
        return [], [], []

    # 按证券代码分组
    grouped = df.groupby('code')

    for code, group in grouped:
        group = group.sort_values('date').reset_index(drop=True)

        # 获取证券名称
        name = group.iloc[0].get('name', code)

        # 持仓队列
        queue = FIFOQueue()

        # 处理每笔交易
        for idx, row in group.iterrows():
            direction = row['direction']
            quantity = row['quantity']
            price = row['price']
            date = row['date']
            commission = row.get('commission', 0)
            stamp_duty = row.get('stamp_duty', 0)
            transfer_fee = row.get('transfer_fee', 0)

            if direction == '买入':
                # 买入时添加到持仓队列
                position = {
                    'code': code,
                    'name': name,
                    'buy_date': date,
                    'buy_price': price,
                    'buy_quantity': quantity,
                    'buy_commission': commission,
                    'remaining_quantity': quantity,
                }
                queue.push(position)

            elif direction == '卖出':
                # 卖出时尝试配对
                remaining_sell = quantity

                while remaining_sell > 0 and not queue.is_empty():
                    position = queue.peek()

                    if position['remaining_quantity'] <= 0:
                        queue.pop()
                        continue

                    # 计算可配对数量
                    match_quantity = min(remaining_sell, position['remaining_quantity'])

                    # 计算盈亏
                    sell_amount = match_quantity * price
                    buy_cost = match_quantity * position['buy_price']

                    # 考虑费用
                    total_commission = commission + position.get('buy_commission', 0) * (match_quantity / position['buy_quantity'])
                    total_stamp_duty = stamp_duty * (match_quantity / quantity) if stamp_duty > 0 else 0

                    profit = sell_amount - buy_cost - total_commission - total_stamp_duty

                    # 配对记录
                    paired = {
                        'code': code,
                        'name': name,
                        'buy_date': position['buy_date'],
                        'sell_date': date,
                        'buy_price': position['buy_price'],
                        'sell_price': price,
                        'quantity': match_quantity,
                        'profit': profit,
                        'holding_days': (date - position['buy_date']).days,
                        'buy_commission': total_commission,
                        'sell_commission': commission * (match_quantity / quantity),
                    }
                    paired_trades.append(paired)

                    # 更新持仓
                    remaining_sell -= match_quantity
                    position['remaining_quantity'] -= match_quantity

                    if position['remaining_quantity'] <= 0:
                        queue.pop()
                    else:
                        queue.update_first(position)

                # 如果卖出数量还有剩余，记录错误
                if remaining_sell > 0:
                    errors.append({
                        'type': 'unmatched_sell',
                        'message': f'证券 {code}({name}) 卖出 {remaining_sell} 股无法配对（无对应持仓）',
                        'severity': 'warning'
                    })

        # 处理完所有交易后，剩余的持仓即为未平仓
        while not queue.is_empty():
            position = queue.pop()
            holdings.append({
                'code': position['code'],
                'name': position['name'],
                'buy_date': position['buy_date'],
                'buy_price': position['buy_price'],
                'quantity': position['remaining_quantity'],
                'buy_commission': position['buy_commission'],
            })

    # 为配对交易添加证券品种和持仓时长
    for trade in paired_trades:
        trade['security_type'] = classify_security(trade['code'], trade['name'])
        trade['holding_period'] = calculate_holding_period(trade['holding_days'])

    # 为持仓添加证券品种
    for holding in holdings:
        holding['security_type'] = classify_security(holding['code'], holding['name'])

    return paired_trades, holdings, errors


def calculate_holding_period(days: int) -> str:
    """
    根据持有天数返回持有期限分类

    Args:
        days: 持有天数

    Returns:
        str: 持有期限分类
    """
    if days <= 7:
        return '1周以内'
    elif days <= 30:
        return '1月以内'
    elif days <= 60:
        return '2月以内'
    elif days <= 90:
        return '3月以内'
    elif days <= 180:
        return '6月以内'
    elif days <= 365:
        return '1年以内'
    else:
        return '1年以上'


def categorize_by_holding_period(paired_trades: List[Dict]) -> Dict:
    """
    按持有期限分类配对交易

    Args:
        paired_trades: 配对后的交易列表

    Returns:
        Dict: 按持有期限分类的统计
    """
    categories = {
        '1周以内': {'count': 0, 'profit': 0, 'trades': []},
        '1月以内': {'count': 0, 'profit': 0, 'trades': []},
        '2月以内': {'count': 0, 'profit': 0, 'trades': []},
        '3月以内': {'count': 0, 'profit': 0, 'trades': []},
        '6月以内': {'count': 0, 'profit': 0, 'trades': []},
        '1年以内': {'count': 0, 'profit': 0, 'trades': []},
        '1年以上': {'count': 0, 'profit': 0, 'trades': []},
    }

    for trade in paired_trades:
        period = calculate_holding_period(trade['holding_days'])
        categories[period]['count'] += 1
        categories[period]['profit'] += trade['profit']
        categories[period]['trades'].append(trade)

    return categories
