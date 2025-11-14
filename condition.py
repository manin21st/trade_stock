# -*- coding: utf-8 -*-

"""
Condition library for the trading bot.
Contains functions that check various conditions to decide whether to trade.
"""

import logging
import json
import core_logic # Will be used to get real-time data

CONFIG_FILE = 'config.json'

def _load_config():
    """Loads the shared configuration file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error("Failed to load or parse %s: %s", CONFIG_FILE, e)
        return None

def is_trading_hours(cycle_id):
    """
    Checks if the current time is within trading hours.
    (This is a placeholder and needs real implementation).
    """
    # Placeholder: always return True if enabled in config
    config = _load_config()
    check_enabled = config.get('strategy_A', {}).get('buy_conditions', {}).get('check_trading_hours', False)
    if config and check_enabled:
        logging.info("Condition 'is_trading_hours': Check enabled. Met (Placeholder)", extra={'cycle_id': cycle_id})
        return True
    elif not config:
         return False # Could not load config
    else:
        logging.info("Condition 'is_trading_hours': Check disabled. Not applied.", extra={'cycle_id': cycle_id})
        return True


def is_price_below_target(cycle_id, stock_code):
    """
    Checks if the stock's current price is below the target price from config.
    """
    config = _load_config()
    if not config:
        return False

    target_price = config.get('strategy_A', {}).get('buy_conditions', {}).get('target_price')
    if target_price is None:
        logging.warning("Buy target price not found in config. Configured value: %s", target_price, extra={'cycle_id': cycle_id})
        return False

    # --- Get current price ---
    current_price_df = core_logic.get_price(cycle_id, stock_code)
    if current_price_df is None or current_price_df.empty:
        logging.error("Could not fetch price for %s", stock_code, extra={'cycle_id': cycle_id})
        return False
    
    current_price = int(current_price_df['stck_prpr'].iloc[0])
    
    logging.info("[%s] Condition 'is_price_below_target': Current Price=%s, Target Price=%s", stock_code, current_price, target_price, extra={'cycle_id': cycle_id})

    if current_price < target_price:
        logging.info("[%s] Condition 'is_price_below_target': Met", stock_code, extra={'cycle_id': cycle_id})
        return True
    else:
        logging.info("[%s] Condition 'is_price_below_target': Not Met", stock_code, extra={'cycle_id': cycle_id})
        return False


def has_sufficient_cash(cycle_id):
    """
    Checks if the account has enough cash for a purchase.
    """
    config = _load_config()
    if not config:
        return False
        
    min_cash = config.get('strategy_A', {}).get('buy_conditions', {}).get('min_cash_amount')
    if min_cash is None:
        logging.warning("Minimum cash amount not found in config. Configured value: %s", min_cash, extra={'cycle_id': cycle_id})
        return False

    # --- Get current balance ---
    _, df_balance = core_logic.get_balance(cycle_id)
    if df_balance is None or df_balance.empty:
        logging.error("Could not fetch account balance.", extra={'cycle_id': cycle_id})
        return False

    current_cash = int(df_balance['dnca_tot_amt'].iloc[0])

    logging.info("Condition 'has_sufficient_cash': Current Cash=%s, Minimum Required=%s", current_cash, min_cash, extra={'cycle_id': cycle_id})

    if current_cash > min_cash:
        logging.info("Condition 'has_sufficient_cash': Met", extra={'cycle_id': cycle_id})
        return True
    else:
        logging.info("Condition 'has_sufficient_cash': Not Met", extra={'cycle_id': cycle_id})
        return False

# --- Placeholder functions for selling ---
def is_target_profit_reached(cycle_id, stock_code):
    config = _load_config()
    target_profit = config.get('strategy_A', {}).get('sell_conditions', {}).get('target_profit_percent')
    logging.info("[%s] Condition 'is_target_profit_reached': Not implemented. Configured: %s%%", stock_code, target_profit, extra={'cycle_id': cycle_id})
    return False

def is_stop_loss_reached(cycle_id, stock_code):
    config = _load_config()
    stop_loss = config.get('strategy_A', {}).get('sell_conditions', {}).get('stop_loss_percent')
    logging.info("[%s] Condition 'is_stop_loss_reached': Not implemented. Configured: %s%%", stock_code, stop_loss, extra={'cycle_id': cycle_id})
    return False
