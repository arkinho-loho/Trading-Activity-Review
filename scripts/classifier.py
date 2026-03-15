"""
证券类型识别模块
通过证券代码和名称双重验证识别证券类型
"""

import pandas as pd
from typing import Dict, List


# 证券类型
SECURITY_TYPES = {
    'FUND': '基金',
    'CB': '可转债',
    'STOCK': '个股',
    'OTHER': '其他'
}


def classify_security(code: str, name: str = '') -> str:
    """
    识别证券类型

    Args:
        code: 证券代码（6位数字）
        name: 证券名称

    Returns:
        str: 证券类型 (ETF/LOF基金/可转债/个股/其他)
    """
    code = str(code).strip()
    name = str(name).strip() if name else ''

    # 首先尝试代码识别
    type_from_code = classify_by_code(code)
    if type_from_code != SECURITY_TYPES['OTHER']:
        return type_from_code

    # 代码无法识别，尝试名称识别
    type_from_name = classify_by_name(name)
    if type_from_name != SECURITY_TYPES['OTHER']:
        return type_from_name

    # 都无法识别，返回"其他"
    return SECURITY_TYPES['OTHER']


def classify_by_code(code: str) -> str:
    """
    通过证券代码识别类型

    代码规则：
    - 51/15/50/56/58/16/501开头 → 基金（ETF/LOF）
    - 11/12开头 → 可转债
    - 60/000/001/002/300/688 → 个股
    """
    if len(code) < 2:
        return SECURITY_TYPES['OTHER']

    prefix = code[:2]
    prefix3 = code[:3] if len(code) >= 3 else ''

    # 基金（ETF/LOF）: 50、51、15、56、58、16、501开头
    if prefix in ['50', '51', '15', '56', '58', '16'] or prefix3 == '501':
        return SECURITY_TYPES['FUND']

    # 可转债: 11、12开头
    if prefix in ['11', '12']:
        return SECURITY_TYPES['CB']

    # 个股: 60、00、30、68开头
    if code.startswith('60') or code.startswith('00') or code.startswith('30') or code.startswith('68'):
        return SECURITY_TYPES['STOCK']

    return SECURITY_TYPES['OTHER']


def classify_by_name(name: str) -> str:
    """
    通过证券名称识别类型

    名称规则：
    - 含"ETF"/"LOF"/"分级" → 基金
    - 含"转债"/"EB" → 可转债
    """
    if not name:
        return SECURITY_TYPES['OTHER']

    name_upper = name.upper()

    # 基金（ETF/LOF）
    if 'ETF' in name_upper or 'LOF' in name_upper or '分级' in name:
        return SECURITY_TYPES['FUND']

    # 可转债
    if '转债' in name or 'EB' in name_upper:
        return SECURITY_TYPES['CB']

    return SECURITY_TYPES['OTHER']


def classify_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    为DataFrame添加证券类型列

    Args:
        df: 包含code和name列的DataFrame

    Returns:
        pd.DataFrame: 添加了security_type列的DataFrame
    """
    if df.empty:
        return df

    if 'code' not in df.columns:
        return df

    # 确保有name列
    if 'name' not in df.columns:
        df['name'] = ''

    # 批量分类
    df['security_type'] = df.apply(
        lambda row: classify_security(row['code'], row.get('name', '')),
        axis=1
    )

    return df


def get_type_statistics(df: pd.DataFrame) -> Dict:
    """
    获取证券类型统计

    Args:
        df: 包含security_type列的DataFrame

    Returns:
        Dict: 各类型统计
    """
    if df.empty or 'security_type' not in df.columns:
        return {}

    stats = df['security_type'].value_counts().to_dict()
    return stats
