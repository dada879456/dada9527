#!/usr/bin/env python
# -*- coding: utf-8 -*-

import okx.MarketData as MarketData
import time
from pprint import pprint
import argparse

# API 凭证
api_key = "8f0e1156-ea8e-4a51-97ca-518f026a17ed"
secret_key = "2AB73E702E14182CAD129CD46D2BA7E1"
passphrase = "@Zz12345678"

# 交易参数
flag = "0"  # 实盘:"0", 模拟盘:"1"

def get_ticker(inst_id):
    """
    获取单个产品的行情信息
    
    参数:
    inst_id (str): 产品ID，例如 "BTC-USDT"
    
    返回:
    dict: 行情数据
    """
    marketDataAPI = MarketData.MarketAPI(flag=flag)
    result = marketDataAPI.get_ticker(instId=inst_id)
    return result

def print_ticker_info(ticker_data):
    """打印行情信息并提取关键指标"""
    if ticker_data.get('code') == '0' and ticker_data.get('data'):
        data = ticker_data['data'][0]
        
        # 提取关键信息
        last_price = float(data.get('last', 0))
        open_24h = float(data.get('open24h', 0))
        high_24h = float(data.get('high24h', 0))
        low_24h = float(data.get('low24h', 0))
        vol_24h = float(data.get('vol24h', 0))
        
        # 计算24小时价格变化
        price_change = last_price - open_24h
        price_change_percent = (price_change / open_24h * 100) if open_24h != 0 else 0
        
        # 打印格式化信息
        print(f"\n==== {data.get('instId')} 行情信息 ====")
        print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(data.get('ts', '0')) / 1000))}")
        print(f"最新价格: {last_price}")
        print(f"24小时变化: {price_change:+.8f} ({price_change_percent:+.2f}%)")
        print(f"24小时最高: {high_24h}")
        print(f"24小时最低: {low_24h}")
        print(f"24小时成交量: {vol_24h}")
        print(f"买一价: {data.get('bidPx', '无数据')}, 买一量: {data.get('bidSz', '无数据')}")
        print(f"卖一价: {data.get('askPx', '无数据')}, 卖一量: {data.get('askSz', '无数据')}")
        
        print("\n完整数据:")
        pprint(data)
    else:
        print(f"获取行情信息失败: {ticker_data}")

def continuous_ticker(inst_id, interval=5, count=0):
    """
    持续获取行情信息
    
    参数:
    inst_id (str): 产品ID
    interval (int): 刷新间隔，单位为秒
    count (int): 获取次数，0表示无限次
    """
    tries = 0
    try:
        while count == 0 or tries < count:
            result = get_ticker(inst_id)
            print_ticker_info(result)
            tries += 1
            
            if count == 0 or tries < count:
                print(f"\n{interval}秒后刷新...")
                time.sleep(interval)
                print("\033[H\033[J", end="")  # 清屏
    except KeyboardInterrupt:
        print("\n程序已被用户中断")

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description='获取OKX单个产品行情信息')
#     parser.add_argument('--instid', type=str, default='BTC-USDT', help='产品ID (例如: BTC-USDT, ETH-USDT)')
#     parser.add_argument('--interval', type=int, default=5, help='刷新间隔，单位为秒')
#     parser.add_argument('--count', type=int, default=1, help='获取次数，0表示无限次')
#     args = parser.parse_args()
    
#     if args.count == 1:
#         # 获取一次行情数据
#         result = get_ticker(args.instid)
#         print(result)
#         # print_ticker_info(result)
#     else:
#         # 持续获取行情数据
#         continuous_ticker(args.instid, args.interval, args.count) 