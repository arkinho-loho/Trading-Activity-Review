"""
交割单解析模块
读取同花顺导出的交割单Excel文件，进行字段映射和数据验证
"""

import pandas as pd
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime


# 同花顺交割单字段映射
FIELD_MAPPING = {
    '操作': 'direction',
    '证券代码': 'code',
    '证券名称': 'name',
    '成交数量': 'quantity',
    '成交均价': 'price',
    '成交金额': 'amount',
    '发生金额': 'net_amount',
    '手续费': 'commission',
    '印花税': 'stamp_duty',
    '过户费': 'transfer_fee',
    '交收日期': 'date',
}

# 有效交易方向
VALID_DIRECTIONS = ['买入', '卖出', '证券买入', '证券卖出']


def parse_delivery_slip(file_path: str) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    解析交割单文件

    Args:
        file_path: 交割单Excel文件路径

    Returns:
        Tuple[pd.DataFrame, List[Dict]]: (处理后的DataFrame, 错误日志)
    """
    errors = []

    # 检查文件是否存在
    if not os.path.exists(file_path):
        errors.append({
            'type': 'file_not_found',
            'message': f'文件不存在: {file_path}',
            'severity': 'critical'
        })
        return pd.DataFrame(), errors

    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)
    except Exception as e:
        errors.append({
            'type': 'file_read_error',
            'message': f'读取文件失败: {str(e)}',
            'severity': 'critical'
        })
        return pd.DataFrame(), errors

    # 字段映射
    df = map_fields(df, errors)

    # 数据验证
    df = validate_data(df, errors)

    # 数据标准化
    df = normalize_data(df, errors)

    return df, errors


def map_fields(df: pd.DataFrame, errors: List[Dict]) -> pd.DataFrame:
    """字段映射"""
    # 查找可能的列名
    available_cols = df.columns.tolist()

    # 创建反向映射
    reverse_mapping = {v: k for k, v in FIELD_MAPPING.items()}

    # 重命名列
    rename_dict = {}
    for col in available_cols:
        col_lower = col.lower().strip()
        for field_key, field_value in FIELD_MAPPING.items():
            if field_key.lower() == col_lower or field_value.lower() == col_lower:
                rename_dict[col] = field_value
                break

    if rename_dict:
        df = df.rename(columns=rename_dict)

    return df


def validate_data(df: pd.DataFrame, errors: List[Dict]) -> pd.DataFrame:
    """数据验证"""
    # 检查必要字段
    required_fields = ['direction', 'code', 'quantity', 'price']
    missing_fields = [f for f in required_fields if f not in df.columns]

    if missing_fields:
        errors.append({
            'type': 'missing_fields',
            'message': f'缺少必要字段: {missing_fields}',
            'severity': 'critical'
        })
        return pd.DataFrame()

    # 过滤无效记录
    initial_count = len(df)

    # 过滤有效交易方向
    if 'direction' in df.columns:
        df = df[df['direction'].isin(VALID_DIRECTIONS)]

    # 过滤数量为0的记录
    if 'quantity' in df.columns:
        df = df[df['quantity'] > 0]

    # 过滤价格为0的记录
    if 'price' in df.columns:
        df = df[df['price'] > 0]

    filtered_count = len(df)
    if filtered_count < initial_count:
        errors.append({
            'type': 'data_filtered',
            'message': f'过滤了 {initial_count - filtered_count} 条无效记录',
            'severity': 'info'
        })

    return df


def normalize_data(df: pd.DataFrame, errors: List[Dict]) -> pd.DataFrame:
    """数据标准化"""
    if df.empty:
        return df

    # 标准化证券代码（6位数字，前补0）
    if 'code' in df.columns:
        df['code'] = df['code'].astype(str).str.zfill(6)

    # 标准化日期格式
    if 'date' in df.columns:
        # 先转换为字符串，处理 YYYYMMDD 格式（如 20231123）
        df['date'] = df['date'].astype(str)
        # 移除可能的时间部分（如 1970-01-01 00:00:00.020231123）
        df['date'] = df['date'].str.extract(r'(\d{8})')[0]
        # 解析为日期
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
        # 检查无效日期
        if df['date'].isna().any():
            invalid_count = df['date'].isna().sum()
            errors.append({
                'type': 'invalid_date',
                'message': f'有 {invalid_count} 条记录日期格式无效',
                'severity': 'warning'
            })
            df = df[df['date'].notna()]

    # 标准化方向字段
    if 'direction' in df.columns:
        df['direction'] = df['direction'].apply(lambda x: '买入' if '买' in str(x) else '卖出')

    # 确保数值字段为数字类型
    numeric_fields = ['quantity', 'price', 'amount', 'net_amount', 'commission', 'stamp_duty', 'transfer_fee']
    for field in numeric_fields:
        if field in df.columns:
            df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)

    # 按日期排序（使用stable排序保持相同日期的记录顺序）
    if 'date' in df.columns:
        df = df.sort_values('date', kind='stable').reset_index(drop=True)

    return df


def get_summary(df: pd.DataFrame) -> Dict:
    """获取交割单摘要"""
    if df.empty:
        return {
            'total_records': 0,
            'buy_count': 0,
            'sell_count': 0,
            'date_range': None
        }

    buy_count = len(df[df['direction'] == '买入'])
    sell_count = len(df[df['direction'] == '卖出'])

    date_range = None
    if 'date' in df.columns and not df['date'].empty:
        date_range = {
            'start': df['date'].min().strftime('%Y-%m-%d'),
            'end': df['date'].max().strftime('%Y-%m-%d')
        }

    return {
        'total_records': len(df),
        'buy_count': buy_count,
        'sell_count': sell_count,
        'date_range': date_range
    }
