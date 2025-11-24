# -*- coding: utf-8 -*-

"""
Condition library for the trading bot.
Contains functions that check various conditions in a sequence to decide whether to trade.
"""

import logging
import json
import math
import datetime
import core_logic
import strategy # Import the new strategy module

# -----------------------------------------------------------------------------
# Main decision function, called by main_cmd.py
# -----------------------------------------------------------------------------

def find_action_to_take(cycle_id, config):
    """
    Checks all defined conditions in order and returns the first valid action.
    This is the main entry point for the decision-making process.
    """
    # The pipeline of condition handlers, executed in order.
    condition_pipeline = [
        _check_forced_trade,
        _process_rules
    ]

    for handler in condition_pipeline:
        action = handler(cycle_id, config)
        if action:
            return action  # Return the first action decided upon

    return None # No action was decided

# -----------------------------------------------------------------------------
# 1. Forced Trade Handler
# -----------------------------------------------------------------------------

def _check_forced_trade(cycle_id, config):
    """
    Handles the forced trade condition. If enabled, returns a trade action.
    """
    forced_trade_config = config.get('forced_trade', {})
    
    if not forced_trade_config.get('enabled', False):
        return None # Forced trade is not enabled, move to the next handler
    
    trade_type = forced_trade_config.get('trade_type')
    stock_code = forced_trade_config.get('stock_code')
    quantity = forced_trade_config.get('quantity')
    price = forced_trade_config.get('price', 0) # Default to 0 (market price)
    market = forced_trade_config.get('market', 'KRX') # Read the market parameter

    if not all([trade_type, stock_code, quantity > 0]):
        logging.error("Forced trade is enabled but configuration is incomplete or invalid.", extra={'cycle_id': cycle_id})
        return None
    action = {
        'type': trade_type,
        'stock_code': stock_code,
        'quantity': quantity,
        'price': price,
        'market': market, # Add market to the action dictionary
        'strategy_name': 'FORCED_TRADE',
        'is_forced_trade': True
    }
    return action

# -----------------------------------------------------------------------------
# 2. Process General Rules
# -----------------------------------------------------------------------------

def _process_rules(cycle_id, config):
    """
    Processes the general trading rules defined in the config.
    Iterates through rules, evaluates conditions, and executes strategy.
    """
    rules = config.get('rules', [])
    if not rules:
        logging.info("No general rules defined in config.", extra={'cycle_id': cycle_id})
        return None

    for rule in rules:
        rule_name = rule.get('rule_name', 'Unnamed Rule')
        logging.info("Evaluating rule: '%s'", rule_name, extra={'cycle_id': cycle_id})

        conditions_config = rule.get('conditions', [])
        strategy_config = rule.get('strategy', {})
        
        # Check if target_stock is explicitly provided in strategy_config or conditions
        # For evaluation purposes, we often need a stock_code from the rule context.
        # This assumes that conditions either specify stock_code or it's a global check.
        # For simplicity, we'll extract it from the first condition that has it,
        # or from strategy_config if present there.
        rule_stock_code = strategy_config.get('params', {}).get('stock_code')
        if not rule_stock_code:
            for cond in conditions_config:
                if cond.get('params', {}).get('stock_code'):
                    rule_stock_code = cond['params']['stock_code']
                    break

        if not rule_stock_code:
            logging.warning("Rule '%s' does not specify a 'stock_code' in its strategy params or conditions. Skipping.", rule_name, extra={'cycle_id': cycle_id})
            continue

        # Evaluate conditions for the rule (Assumes AND operator for now)
        if _evaluate_conditions(cycle_id, rule_stock_code, conditions_config):
            logging.info("Conditions met for rule '%s'. Executing strategy '%s'.", 
                         rule_name, strategy_config.get('name', 'Unnamed Strategy'), extra={'cycle_id': cycle_id})
            
            # Dynamically call the strategy function from strategy.py
            strategy_func_name = strategy_config.get('name')
            if strategy_func_name:
                strategy_func = getattr(strategy, strategy_func_name, None)
                if strategy_func:
                    action = strategy_func(cycle_id, strategy_config.get('params', {}))
                    if action:
                        action['strategy_name'] = rule_name # Use rule_name as strategy_name for logging clarity
                        return action
                else:
                    logging.error("Strategy function '%s' not found in strategy.py.", strategy_func_name, extra={'cycle_id': cycle_id})
            else:
                logging.error("Rule '%s' has no strategy 'name' defined.", rule_name, extra={'cycle_id': cycle_id})
        else:
            logging.info("Conditions not met for rule '%s'.", rule_name, extra={'cycle_id': cycle_id})
    
    return None # No rule conditions were met

# -----------------------------------------------------------------------------
# Helper for evaluating a set of conditions
# -----------------------------------------------------------------------------

def _evaluate_conditions(cycle_id, stock_code, conditions_config):
    """
    Evaluates a list of conditions. Assumes an 'AND' operator for all conditions
    in the list for now.
    """
    if not conditions_config:
        return True # No conditions means always true

    all_conditions_met = True
    for cond in conditions_config:
        cond_name = cond.get('name')
        cond_params = cond.get('params', {})
        
        # Dynamically call the condition function from this module
        cond_func = globals().get(cond_name, None) # Use globals() to get functions in this module
        
        if cond_func:
            # Pass stock_code to condition functions where applicable
            # Inspect function signature to decide if stock_code should be passed
            import inspect
            sig = inspect.signature(cond_func)
            if 'stock_code' in sig.parameters:
                condition_result = cond_func(cycle_id, stock_code, cond_params)
            else:
                condition_result = cond_func(cycle_id, None, cond_params) # Pass None if stock_code not accepted
            
            logging.debug("[%s] Condition '%s' (%s) evaluated to: %s", stock_code, cond_name, cond_params, condition_result, extra={'cycle_id': cycle_id})
            if not condition_result:
                all_conditions_met = False
                break # Short-circuit for AND operator
        else:
            logging.error("Condition function '%s' not found in condition.py.", cond_name, extra={'cycle_id': cycle_id})
            # Treat unknown conditions as false to be safe, or raise an error
            all_conditions_met = False 
            break
            
    return all_conditions_met

# -----------------------------------------------------------------------------
# Individual Condition Functions (Refactored to accept params and stock_code)
# -----------------------------------------------------------------------------

def is_trading_hours(cycle_id, stock_code, params):
    """Checks if the current time is within trading hours."""
    check_enabled = params.get('check_enabled', False)
    if not check_enabled:
        logging.debug("[%s] Condition 'is_trading_hours': Check disabled. Assuming True.", stock_code, extra={'cycle_id': cycle_id})
        return True
    
    current_time = datetime.datetime.now().time()
    start_time = datetime.time(9, 0) # KST 09:00
    end_time = datetime.time(15, 30) # KST 15:30
    
    if start_time <= current_time <= end_time:
        logging.info("[%s] Condition 'is_trading_hours': Met (within 09:00-15:30 KST).", stock_code, extra={'cycle_id': cycle_id})
        return True
    else:
        logging.info("[%s] Condition 'is_trading_hours': Not met (outside 09:00-15:30 KST).", stock_code, extra={'cycle_id': cycle_id})
        return False

def is_price_below_target(cycle_id, stock_code, params):
    """
    Checks if the stock's current price is below the target price.
    Requires 'target_price' in params.
    """
    if not stock_code: 
        logging.error("is_price_below_target: 'stock_code' is missing.", extra={'cycle_id': cycle_id})
        return False

    target_price = params.get('target_price')
    if target_price is None:
        logging.warning("[%s] Condition 'is_price_below_target': 'target_price' not found in params. Assuming False.", stock_code, extra={'cycle_id': cycle_id})
        return False

    current_price_df = core_logic.get_price(cycle_id, stock_code)
    if current_price_df is None or current_price_df.empty:
        logging.error("[%s] Condition 'is_price_below_target': Could not fetch price.", stock_code, extra={'cycle_id': cycle_id})
        return False
    
    current_price = int(current_price_df['stck_prpr'].iloc[0])
    
    logging.info("[%s] Condition 'is_price_below_target': Current Price=%s, Target Price=%s", stock_code, current_price, target_price, extra={'cycle_id': cycle_id})

    if current_price < target_price:
        logging.info("[%s] Condition 'is_price_below_target': Met.", stock_code, extra={'cycle_id': cycle_id})
        return True
    else:
        logging.info("[%s] Condition 'is_price_below_target': Not Met.", stock_code, extra={'cycle_id': cycle_id})
        return False


def has_sufficient_cash(cycle_id, stock_code, params):
    """
    Checks if the account has enough cash for a purchase.
    Requires 'min_cash_amount' in params.
    """
    min_cash = params.get('min_cash_amount')
    if min_cash is None:
        logging.warning("has_sufficient_cash: 'min_cash_amount' not found in params. Assuming False.", extra={'cycle_id': cycle_id})
        return False

    _, df_balance = core_logic.get_balance(cycle_id)
    if df_balance is None or df_balance.empty:
        logging.error("has_sufficient_cash: Could not fetch account balance.", extra={'cycle_id': cycle_id})
        return False

    current_cash = int(df_balance['dnca_tot_amt'].iloc[0])

    logging.info("[%s] Condition 'has_sufficient_cash': Current Cash=%s, Minimum Required=%s", stock_code, current_cash, min_cash, extra={'cycle_id': cycle_id})

    if current_cash >= min_cash:
        logging.info("[%s] Condition 'has_sufficient_cash': Met.", stock_code, extra={'cycle_id': cycle_id})
        return True
    else:
        logging.info("[%s] Condition 'has_sufficient_cash': Not Met.", stock_code, extra={'cycle_id': cycle_id})
        return False

def is_target_profit_reached(cycle_id, stock_code, params):
    """
    Checks if the profit target for a held stock is reached.
    Requires 'target_profit_percent' in params.
    """
    if not stock_code: 
        logging.error("is_target_profit_reached: 'stock_code' is missing.", extra={'cycle_id': cycle_id})
        return False

    target_profit_percent = params.get('target_profit_percent')
    if target_profit_percent is None:
        logging.warning("[%s] Condition 'is_target_profit_reached': 'target_profit_percent' not found in params. Assuming False.", stock_code, extra={'cycle_id': cycle_id})
        return False

    _, df_holdings = core_logic.get_balance(cycle_id)
    if df_holdings is None or df_holdings.empty:
        logging.info("[%s] Condition 'is_target_profit_reached': No holdings found. Condition not met.", stock_code, extra={'cycle_id': cycle_id})
        return False

    # Check if the required column exists before access
    if 'pdno' not in df_holdings.columns:
        logging.info("[%s] Condition 'is_target_profit_reached': No 'pdno' column in holdings, no stocks held. Condition not met.", stock_code, extra={'cycle_id': cycle_id})
        return False

    # Find the holding for the specific stock_code
    holding = df_holdings[df_holdings['pdno'] == stock_code]
    if holding.empty:
        logging.info("[%s] Condition 'is_target_profit_reached': Stock not held. Condition not met.", stock_code, extra={'cycle_id': cycle_id})
        return False
    
    current_profit_rate = float(holding['prts_rate'].iloc[0]) # 평가손익률
    
    logging.info("[%s] Condition 'is_target_profit_reached': Current Profit Rate=%s%%, Target Profit Rate=%s%%", stock_code, current_profit_rate, target_profit_percent, extra={'cycle_id': cycle_id})

    if current_profit_rate >= target_profit_percent:
        logging.info("[%s] Condition 'is_target_profit_reached': Met.", stock_code, extra={'cycle_id': cycle_id})
        return True
    else:
        logging.info("[%s] Condition 'is_target_profit_reached': Not Met.", stock_code, extra={'cycle_id': cycle_id})
        return False

def is_stop_loss_reached(cycle_id, stock_code, params):
    """
    Checks if the stop loss for a held stock is triggered.
    Requires 'stop_loss_percent' in params.
    """
    if not stock_code: 
        logging.error("is_stop_loss_reached: 'stock_code' is missing.", extra={'cycle_id': cycle_id})
        return False

    stop_loss_percent = params.get('stop_loss_percent')
    if stop_loss_percent is None:
        logging.warning("[%s] Condition 'is_stop_loss_reached': 'stop_loss_percent' not found in params. Assuming False.", stock_code, extra={'cycle_id': cycle_id})
        return False

    _, df_holdings = core_logic.get_balance(cycle_id)
    if df_holdings is None or df_holdings.empty:
        logging.info("[%s] Condition 'is_stop_loss_reached': No holdings found. Condition not met.", stock_code, extra={'cycle_id': cycle_id})
        return False

    # Check if the required column exists before access
    if 'pdno' not in df_holdings.columns:
        logging.info("[%s] Condition 'is_stop_loss_reached': No 'pdno' column in holdings, no stocks held. Condition not met.", stock_code, extra={'cycle_id': cycle_id})
        return False

    # Find the holding for the specific stock_code
    holding = df_holdings[df_holdings['pdno'] == stock_code]
    if holding.empty:
        logging.info("[%s] Condition 'is_stop_loss_reached': Stock not held. Condition not met.", stock_code, extra={'cycle_id': cycle_id})
        return False
    
    current_profit_rate = float(holding['prts_rate'].iloc[0]) # 평가손익률
    
    logging.info("[%s] Condition 'is_stop_loss_reached': Current Profit Rate=%s%%, Stop Loss Rate=%s%%", stock_code, current_profit_rate, stop_loss_percent, extra={'cycle_id': cycle_id})

    if current_profit_rate <= stop_loss_percent:
        logging.info("[%s] Condition 'is_stop_loss_reached': Met.", stock_code, extra={'cycle_id': cycle_id})
        return True
    else:
        logging.info("[%s] Condition 'is_stop_loss_reached': Not Met.", stock_code, extra={'cycle_id': cycle_id})
        return False