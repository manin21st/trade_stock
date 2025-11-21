# -*- coding: utf-8 -*-

"""
Strategy library for the trading bot.
Contains functions that define specific trading strategies to be executed
when conditions are met. These functions will return an action dictionary.
"""

import logging
import core_logic # To get current price for quantity calculation if needed

def simple_buy(cycle_id, params):
    """
    Executes a simple buy strategy based on provided parameters.
    Returns an action dictionary for main_cmd.py.
    """
    stock_code = params.get('stock_code')
    order_amount_krw = params.get('order_amount_krw')
    quantity = params.get('quantity') # Can be used for fixed quantity buys
    price = params.get('price', 0) # 0 for market order
    market = params.get('market', "KRX") # Default to KRX

    if not stock_code:
        logging.error("[%s] simple_buy strategy: 'stock_code' is missing in params.", cycle_id, extra={'cycle_id': cycle_id})
        return None

    # If buying by amount, calculate quantity based on current price
    if order_amount_krw and not quantity:
        current_price_df = core_logic.get_price(cycle_id, stock_code)
        if current_price_df is None or current_price_df.empty:
            logging.error("[%s] simple_buy strategy: Could not fetch current price for %s to calculate quantity.", stock_code, extra={'cycle_id': cycle_id})
            return None
        current_price = int(current_price_df['stck_prpr'].iloc[0])
        
        if current_price > 0:
            quantity = order_amount_krw // current_price
            if quantity == 0:
                logging.warning("[%s] simple_buy strategy: order_amount_krw %s is not enough to buy even 1 share of %s at price %s.", cycle_id, order_amount_krw, stock_code, current_price, extra={'cycle_id': cycle_id})
                return None
            logging.info("[%s] simple_buy strategy: Calculated quantity %s for %s at %s KRW.", cycle_id, quantity, stock_code, current_price, extra={'cycle_id': cycle_id})
        else:
            logging.error("[%s] simple_buy strategy: Current price for %s is 0, cannot calculate quantity.", cycle_id, stock_code, extra={'cycle_id': cycle_id})
            return None

    elif not quantity:
        logging.error("[%s] simple_buy strategy: Either 'order_amount_krw' or 'quantity' must be provided.", cycle_id, extra={'cycle_id': cycle_id})
        return None
    
    return {
        'type': 'BUY',
        'stock_code': stock_code,
        'quantity': quantity,
        'price': price,
        'market': market,
        'strategy_name': 'simple_buy'
    }

def simple_sell(cycle_id, params):
    """
    Executes a simple sell strategy based on provided parameters.
    Returns an action dictionary for main_cmd.py.
    """
    stock_code = params.get('stock_code')
    sell_all = params.get('sell_all', False)
    quantity = params.get('quantity') # For fixed quantity sells
    price = params.get('price', 0) # 0 for market order
    market = params.get('market', "KRX") # Default to KRX

    if not stock_code:
        logging.error("[%s] simple_sell strategy: 'stock_code' is missing in params.", cycle_id, extra={'cycle_id': cycle_id})
        return None

    if sell_all:
        # Need to get actual holding quantity from core_logic.get_balance
        _, df_holdings = core_logic.get_balance(cycle_id)
        if df_holdings is not None and not df_holdings.empty:
            held_qty = df_holdings[df_holdings['pdno'] == stock_code]['hldg_qty'].iloc[0] if stock_code in df_holdings['pdno'].values else 0
        else:
            held_qty = 0

        if held_qty > 0:
            quantity = int(held_qty)
            logging.info("[%s] simple_sell strategy: 'sell_all' is true. Determined quantity %s from holdings for %s.", cycle_id, quantity, stock_code, extra={'cycle_id': cycle_id})
        else:
            logging.warning("[%s] simple_sell strategy: 'sell_all' is true, but no holdings found for %s.", cycle_id, stock_code, extra={'cycle_id': cycle_id})
            return None
    elif not quantity or quantity <= 0:
        logging.error("[%s] simple_sell strategy: Either 'sell_all' or a valid 'quantity' must be provided.", cycle_id, extra={'cycle_id': cycle_id})
        return None

    return {
        'type': 'SELL',
        'stock_code': stock_code,
        'quantity': quantity,
        'price': price,
        'market': market,
        'strategy_name': 'simple_sell'
    }