# -*- coding: utf-8 -*-
"""
condition.py - 매매 조건 평가 및 전략 결정 엔진

이 모듈은 `config.json`에 정의된 매매 규칙(rules)을 평가하여 실제 거래를
실행할지 여부를 결정하는 역할을 합니다. 각 규칙에 명시된 모든 조건(conditions)이
충족되면, 해당 규칙에 연결된 전략(strategy)을 실행하도록 결정하고 그 결과를 반환합니다.

주요 기능:
1.  **규칙 기반 평가**: `config.json`의 'rules' 목록을 순회하며 각 규칙을 평가합니다.
2.  **복합 조건 검사**: 한 규칙 내에 정의된 여러 조건(예: 가격 조건, 시간 조건, 잔고 조건 등)이 모두 참(AND)인지 확인합니다.
3.  **동적 전략 호출**: 조건이 모두 충족된 규칙의 'strategy' 정보를 바탕으로, `strategy.py` 모듈에 정의된 실제 매매 전략 함수(예: `simple_buy`)를 동적으로 찾아 실행을 요청합니다.
4.  **실행 결정 반환**: 평가 결과에 따라 매수, 매도 또는 아무것도 하지 않음(`None`)을 나타내는 실행 계획(action)을 `main_cmd.py`에 반환합니다.
"""

import logging
import json
import math
import datetime
import os
import inspect

import core_logic
import strategy

# 이 스크립트(condition.py)는 src 폴더 안에 있으므로, 상위 폴더가 프로젝트 루트가 됩니다.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Constants for file paths
TRADE_STATE_FILE = os.path.join(PROJECT_ROOT, 'json', 'trade_state.json')
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'json', 'config.json')

# --- Trade State Management ---
def _load_trade_state():
    """진행 중인 강제 거래 상태를 `trade_state.json` 파일에서 로드합니다."""
    try:
        if os.path.exists(TRADE_STATE_FILE):
            with open(TRADE_STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logging.debug(f"거래 상태 로드됨: {state}")
                return state
        return {}
    except Exception as e:
        logging.error(f"거래 상태 로드 중 오류 발생: {e}")
        return {}

def _save_trade_state(state):
    """진행 중인 강제 거래 상태를 `trade_state.json` 파일에 저장합니다."""
    try:
        with open(TRADE_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
        logging.debug(f"거래 상태 저장됨: {state}")
    except Exception as e:
        logging.error(f"거래 상태 저장 중 오류 발생: {e}")

# --- Helper functions for getting account/stock info ---
def _get_available_buy_cash(balance_df):
    """현재 계좌의 매수 가능한 현금 금액을 조회합니다."""
    if balance_df is not None and not balance_df.empty:
        return int(balance_df['dnca_tot_amt'].iloc[0])
    return 0

def _get_stock_sellable_quantity(stock_code, holdings_df):
    """특정 종목의 현재 매도 가능한 수량을 조회합니다."""
    if holdings_df is not None and not holdings_df.empty and 'pdno' in holdings_df.columns:
        holding = holdings_df[holdings_df['pdno'] == stock_code]
        if not holding.empty:
            return int(holding['ord_psbl_qty'].iloc[0])
    return 0

def _get_stock_current_value(stock_code, holdings_df):
    """특정 종목의 현재 평가액을 조회합니다."""
    if holdings_df is not None and not holdings_df.empty and 'pdno' in holdings_df.columns:
        holding = holdings_df[holdings_df['pdno'] == stock_code]
        if not holding.empty:
            return int(holding['evlu_amt'].iloc[0])
    return 0

# --- Individual Condition Functions (Refactored) ---
def is_trading_hours(params, **kwargs):
    """현재 시간이 거래 시간(정규장 09:00-15:30 KST) 내인지 확인합니다."""
    check_enabled = params.get('check_enabled', False)
    if not check_enabled:
        logging.debug("조건 'is_trading_hours': 확인 비활성화. 참으로 간주.")
        return True
    
    current_time = datetime.datetime.now().time()
    start_time = datetime.time(9, 0)
    end_time = datetime.time(15, 30)
    
    if start_time <= current_time <= end_time:
        logging.debug("조건 'is_trading_hours': 충족 (09:00-15:30 KST 내).")
        return True
    else:
        logging.debug("조건 'is_trading_hours': 미충족 (09:00-15:30 KST 외).")
        return False

def is_price_below_target(stock_code, params, price_df, **kwargs):
    """주식의 현재 가격이 목표 가격(`target_price`)보다 낮은지 확인합니다."""
    if not stock_code: 
        logging.error("is_price_below_target: 'stock_code'가 누락되었습니다.")
        return False

    target_price = params.get('target_price')
    if target_price is None:
        logging.warning("조건 'is_price_below_target': 파라미터에 'target_price'를 찾을 수 없습니다. 거짓으로 간주.")
        return False

    if price_df is None or price_df.empty:
        logging.error("조건 'is_price_below_target': 현재가를 담은 데이터프레임이 없습니다.")
        return False
    
    current_price = int(price_df['stck_prpr'].iloc[0])
    logging.debug("조건 'is_price_below_target': 현재가=%s, 목표가=%s", current_price, target_price)

    return current_price < target_price

def has_sufficient_cash(params, balance_df, **kwargs):
    """계좌에 최소 매수 현금(`min_cash_amount`)이 충분한지 확인합니다."""
    min_cash = params.get('min_cash_amount')
    if min_cash is None:
        logging.warning("has_sufficient_cash: 파라미터에 'min_cash_amount'를 찾을 수 없습니다. 거짓으로 간주.")
        return False

    if balance_df is None or balance_df.empty:
        logging.error("has_sufficient_cash: 계좌 잔고 데이터프레임이 없습니다.")
        return False

    current_cash = int(balance_df['dnca_tot_amt'].iloc[0])
    logging.debug("조건 'has_sufficient_cash': 현재 현금=%s, 최소 필요액=%s", current_cash, min_cash)

    return current_cash >= min_cash

def is_target_profit_reached(stock_code, params, holdings_df, **kwargs):
    """보유 종목의 수익률이 목표 수익률(`target_profit_percent`)에 도달했는지 확인합니다."""
    if not stock_code: 
        logging.error("is_target_profit_reached: 'stock_code'가 누락되었습니다.")
        return False

    target_profit_percent = params.get('target_profit_percent')
    if target_profit_percent is None:
        logging.warning("조건 'is_target_profit_reached': 파라미터에 'target_profit_percent'를 찾을 수 없습니다. 거짓으로 간주.")
        return False

    if holdings_df is None or holdings_df.empty or 'pdno' not in holdings_df.columns:
        logging.debug("조건 'is_target_profit_reached': 보유 종목이 없거나 데이터가 불완전합니다. 조건 미충족.")
        return False

    holding = holdings_df[holdings_df['pdno'] == stock_code]
    if holding.empty:
        logging.debug("조건 'is_target_profit_reached': 해당 종목(%s)을 보유하고 있지 않습니다. 조건 미충족.", stock_code)
        return False
    
    current_profit_rate = float(holding['evlu_pfls_rt'].iloc[0])
    logging.debug("조건 'is_target_profit_reached': 현재 수익률=%.2f%%, 목표 수익률=%.2f%%", current_profit_rate, target_profit_percent)

    return current_profit_rate >= target_profit_percent

def is_stop_loss_reached(stock_code, params, holdings_df, **kwargs):
    """보유 종목의 손실률이 손절매 기준(`stop_loss_percent`)에 도달했는지 확인합니다."""
    if not stock_code: 
        logging.error("is_stop_loss_reached: 'stock_code'가 누락되었습니다.")
        return False

    stop_loss_percent = params.get('stop_loss_percent')
    if stop_loss_percent is None:
        logging.warning("조건 'is_stop_loss_reached': 파라미터에 'stop_loss_percent'를 찾을 수 없습니다. 거짓으로 간주.")
        return False

    if holdings_df is None or holdings_df.empty or 'pdno' not in holdings_df.columns:
        logging.debug("조건 'is_stop_loss_reached': 보유 종목이 없거나 데이터가 불완전합니다. 조건 미충족.")
        return False

    holding = holdings_df[holdings_df['pdno'] == stock_code]
    if holding.empty:
        logging.debug("조건 'is_stop_loss_reached': 해당 종목(%s)을 보유하고 있지 않습니다. 조건 미충족.", stock_code)
        return False
    
    current_profit_rate = float(holding['evlu_pfls_rt'].iloc[0])
    logging.debug("조건 'is_stop_loss_reached': 현재 수익률=%.2f%%, 손절매 기준=%.2f%%", current_profit_rate, stop_loss_percent)

    return current_profit_rate <= stop_loss_percent

# --- Helper for evaluating a set of conditions ---
def _evaluate_conditions(cycle_id, stock_code, conditions_config, market_data):
    """조건 목록을 평가합니다. 현재는 목록의 모든 조건이 'AND' 연산으로 처리됩니다."""
    if not conditions_config:
        return True

    for cond in conditions_config:
        cond_name = cond.get('name')
        cond_params = cond.get('params', {})
        cond_func = globals().get(cond_name)
        
        if not cond_func:
            logging.error("조건 함수 '%s'를 condition.py에서 찾을 수 없습니다.", cond_name)
            return False

        # 각 조건 함수에 필요한 데이터를 market_data에서 전달
        kwargs = {
            'cycle_id': cycle_id,
            'stock_code': stock_code,
            'params': cond_params,
            'price_df': market_data.get('price_df', {}).get(stock_code),
            'holdings_df': market_data.get('holdings_df'),
            'balance_df': market_data.get('balance_df')
        }
        
        # 함수 시그니처에 따라 필요한 인자만 필터링하여 전달
        sig = inspect.signature(cond_func)
        required_args = {p: kwargs[p] for p in sig.parameters if p in kwargs}

        if not cond_func(**required_args):
            return False
            
    return True

# --- Process General Rules ---
def _process_rules(cycle_id, config, market_data):
    """`config.json`에 정의된 일반 매매 규칙들을 처리합니다."""
    rules = config.get('rules', [])
    if not rules:
        logging.info("설정에 정의된 일반 규칙이 없습니다.")
        return None

    for rule in rules:
        rule_name = rule.get('rule_name', 'Unnamed Rule')
        logging.debug("규칙 평가 중: '%s'", rule_name)

        conditions_config = rule.get('conditions', [])
        strategy_config = rule.get('strategy', {})
        
        rule_stock_code = strategy_config.get('params', {}).get('stock_code')
        if not rule_stock_code:
            for cond in conditions_config:
                if cond.get('params', {}).get('stock_code'):
                    rule_stock_code = cond['params']['stock_code']
                    break

        if not rule_stock_code:
            logging.warning("규칙 '%s'에 'stock_code'가 지정되지 않았습니다. 건너뜁니다.", rule_name)
            continue

        if _evaluate_conditions(cycle_id, rule_stock_code, conditions_config, market_data):
            logging.info("규칙 '%s'의 조건 충족. 전략 '%s' 실행.", rule_name, strategy_config.get('name', 'Unnamed Strategy'))
            
            strategy_func_name = strategy_config.get('name')
            if not strategy_func_name:
                logging.error("규칙 '%s'에 전략 'name'이 정의되지 않았습니다.", rule_name)
                continue

            strategy_func = getattr(strategy, strategy_func_name, None)
            if not strategy_func:
                logging.error("전략 함수 '%s'를 strategy.py에서 찾을 수 없습니다.", strategy_func_name)
                continue
            
            # 전략 함수에 필요한 데이터 전달
            strategy_kwargs = {
                'cycle_id': cycle_id,
                'params': strategy_config.get('params', {}),
                'price_df': market_data.get('price_df', {}).get(rule_stock_code),
                'holdings_df': market_data.get('holdings_df'),
                'balance_df': market_data.get('balance_df')
            }
            sig = inspect.signature(strategy_func)
            required_strategy_args = {p: strategy_kwargs[p] for p in sig.parameters if p in strategy_kwargs}

            action = strategy_func(**required_strategy_args)
            if action:
                action['strategy_name'] = rule_name
                return action
        else:
            logging.debug("규칙 '%s'의 조건이 충족되지 않았습니다.", rule_name)
    
    return None

# --- Process Active Forced Trade (State Machine for AUTO/Divisional) ---
def _process_active_forced_trade(cycle_id, config, current_state, market_data):
    """진행 중인 강제 거래 상태를 처리하고 다음 매매 행동을 결정합니다."""
    # (이하 로직은 이미 market_data를 사용하도록 준비된 것으로 가정, 필요시 수정)
    # ... (기존 로직과 유사하게, 단 core_logic 호출 대신 market_data 사용)
    # 예시: current_price = int(market_data['price_df'][stock_code]['stck_prpr'].iloc[0])
    # 예시: available_cash = _get_available_buy_cash(market_data['balance_df'])
    # ...

    return None # 임시로 비활성화

def find_action_to_take(cycle_id, config):
    """
    현재 매매 사이클에서 취할 행동을 결정합니다.
    - 필요한 모든 시장 데이터를 한 번에 조회합니다.
    - 강제 거래 상태를 확인하고, 있으면 해당 거래를 처리합니다.
    - 강제 거래가 없으면 일반 매매 규칙을 평가하여 행동을 결정합니다.
    """
    logging.debug("[%s] 매매 행동 결정 시작...", cycle_id)
    
    # 1. 필요한 모든 데이터 한 번에 조회
    all_stock_codes = {
        cond.get('params', {}).get('stock_code')
        for rule in config.get('rules', [])
        for cond in rule.get('conditions', [])
        if cond.get('params', {}).get('stock_code')
    } | {
        rule.get('strategy', {}).get('params', {}).get('stock_code')
        for rule in config.get('rules', [])
        if rule.get('strategy', {}).get('params', {}).get('stock_code')
    }
    all_stock_codes.discard(None)
    
    market_data = {'price_df': {}, 'holdings_df': None, 'balance_df': None}
    
    for code in all_stock_codes:
        market_data['price_df'][code] = core_logic.get_price(cycle_id, code)
        
    market_data['holdings_df'], market_data['balance_df'] = core_logic.get_balance(cycle_id)

    # 2. 강제 거래 상태 확인 및 처리
    trade_state = _load_trade_state()
    if trade_state.get('active'):
        logging.info("[%s] 활성 강제 거래 처리 중: %s", cycle_id, trade_state.get('trade_id', 'N/A'))
        action = _process_active_forced_trade(cycle_id, config, trade_state, market_data)
        if action:
            return action
        return {'status': 'forced_trade_handled'}

    # 3. 일반 규칙 처리
    logging.debug("[%s] 일반 매매 규칙 평가 중...", cycle_id)
    action = _process_rules(cycle_id, config, market_data)
    if action:
        return action

    logging.debug("[%s] 이번 사이클에 취할 매매 행동이 없습니다.", cycle_id)
    return None


