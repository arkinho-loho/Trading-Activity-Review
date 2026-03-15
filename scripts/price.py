"""
股价获取模块
使用akshare获取实时/历史股价
"""

import akshare as ak
from typing import Dict, Optional, List
import pandas as pd
from datetime import datetime, timedelta
import time


def get_stock_price(code: str, name: str = '', max_retries: int = 3) -> Optional[float]:
    """
    获取股票/ETF最新价格

    Args:
        code: 证券代码（6位数字）
        name: 证券名称（用于类型判断）
        max_retries: 最大重试次数

    Returns:
        Optional[float]: 最新价格，失败返回None
    """
    # 判断证券类型
    security_type = _get_security_type(code, name)

    for attempt in range(max_retries):
        try:
            if security_type == '基金':
                price = _get_etf_price(code)
            elif security_type == '可转债':
                price = _get_cb_price(code)
            else:  # 个股
                price = _get_stock_price(code)

            if price is not None and price > 0:
                return price

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)  # 短暂等待后重试
                continue
            else:
                # 最后一次尝试失败，记录错误
                pass

    return None


def _get_security_type(code: str, name: str) -> str:
    """判断证券类型（用于决定价格获取接口）"""
    code = str(code)

    # 基金（ETF/LOF）: 50、51、15、56、58、16、501开头
    if (code.startswith('50') or code.startswith('51') or code.startswith('15') or
        code.startswith('56') or code.startswith('58') or code.startswith('16') or
        code.startswith('501')):
        return '基金'

    # 可转债: 11、12开头
    if code.startswith('11') or code.startswith('12'):
        return '可转债'

    # 个股: 60、00、30、68开头
    if code.startswith('60') or code.startswith('00') or code.startswith('30') or code.startswith('68'):
        return '个股'

    # 通过名称判断
    name_upper = name.upper() if name else ''
    if 'ETF' in name_upper or 'LOF' in name_upper or '分级' in name:
        return '基金'
    if '转债' in name or 'EB' in name_upper:
        return '可转债'

    return '个股'


def _get_stock_price(code: str) -> Optional[float]:
    """获取A股股票价格"""
    # 尝试获取最近交易日收盘价
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )

        if df is not None and not df.empty:
            # 返回最近收盘价
            return float(df.iloc[-1]['收盘'])
    except Exception:
        pass

    return None


def _get_etf_price(code: str) -> Optional[float]:
    """获取ETF价格"""
    # 尝试使用ETF行情接口
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

    try:
        df = ak.fund_etf_hist_em(
            symbol=code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )

        if df is not None and not df.empty:
            return float(df.iloc[-1]['收盘'])
    except Exception:
        pass

    # 备选：尝试使用股票接口
    return _get_stock_price(code)


def _get_lof_price(code: str) -> Optional[float]:
    """获取LOF基金价格"""
    # LOF基金通常使用股票接口
    return _get_stock_price(code)


def _get_cb_price(code: str) -> Optional[float]:
    """获取可转债价格"""
    return _get_stock_price(code)


def get_multiple_prices(securities: List[Dict]) -> Dict[str, float]:
    """
    批量获取证券价格

    Args:
        securities: 证券列表，每个元素包含 code 和 name

    Returns:
        Dict[str, float]: {code: price}
    """
    prices = {}

    for sec in securities:
        code = sec.get('code', '')
        name = sec.get('name', '')

        price = get_stock_price(code, name)
        if price is not None:
            prices[code] = price
        else:
            prices[code] = None

        # 避免请求过快
        time.sleep(0.2)

    return prices


def calculate_floating_profit(holdings: List[Dict], prices: Dict[str, float]) -> List[Dict]:
    """
    计算浮动盈亏

    Args:
        holdings: 持仓列表
        prices: 价格字典 {code: price}

    Returns:
        List[Dict]: 添加了浮动盈亏的持仓列表
    """
    for holding in holdings:
        code = holding.get('code', '')
        current_price = prices.get(code)

        if current_price is not None:
            buy_price = holding.get('buy_price', 0)
            quantity = holding.get('quantity', 0)

            # 计算浮动盈亏（忽略费用）
            holding['current_price'] = current_price
            holding['floating_profit'] = (current_price - buy_price) * quantity
            holding['floating_profit_pct'] = ((current_price - buy_price) / buy_price * 100) if buy_price > 0 else 0
        else:
            holding['current_price'] = None
            holding['floating_profit'] = None
            holding['floating_profit_pct'] = None

    return holdings
