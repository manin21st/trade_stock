# -*- coding: utf-8 -*-

"""
Trade library for the trading bot.
Contains functions that execute buy and sell orders.
"""

import logging
import core_logic

def order_buy(cycle_id, stock_code, quantity, price=0, market="KRX"):
    """
    Executes a buy order (market or limit) by calling the core logic.
    """
    success, result = core_logic.create_order(
        cycle_id=cycle_id,
        trade_type='BUY',
        stock_code=stock_code,
        quantity=quantity,
        price=price,
        market=market
    )
    return success

def order_sell(cycle_id, stock_code, quantity, price=0, market="KRX"):
    """
    Executes a sell order (market or limit) by calling the core logic.
    """
    success, result = core_logic.create_order(
        cycle_id=cycle_id,
        trade_type='SELL',
        stock_code=stock_code,
        quantity=quantity,
        price=price,
        market=market
    )
    return success


