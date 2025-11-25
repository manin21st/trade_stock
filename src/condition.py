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

# Constants for file paths
TRADE_STATE_FILE = 'json/trade_state.json'
CONFIG_FILE = 'json/config.json'

# --- Trade State Management ---
def _load_trade_state():
    """진행 중인 강제 거래 상태를 `trade_state.json` 파일에서 로드합니다."""
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    trade_state_path = os.path.join(project_root, TRADE_STATE_FILE)
    try:
        if os.path.exists(trade_state_path):
            with open(trade_state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logging.debug(f"거래 상태 로드됨: {state}")
                return state
        return {}
    except Exception as e:
        logging.error(f"거래 상태 로드 중 오류 발생: {e}")
        return {}

def _save_trade_state(state):
    """진행 중인 강제 거래 상태를 `trade_state.json` 파일에 저장합니다."""
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    trade_state_path = os.path.join(project_root, TRADE_STATE_FILE)
    try:
        with open(trade_state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
        logging.debug(f"거래 상태 저장됨: {state}")
    except Exception as e:
        logging.error(f"거래 상태 저장 중 오류 발생: {e}")

# --- Helper functions for getting account/stock info ---
def _get_available_buy_cash(cycle_id):
    """현재 계좌의 매수 가능한 현금 금액을 조회합니다."""
    _, df_balance = core_logic.get_balance(cycle_id)
    if df_balance is not None and not df_balance.empty:
        # 'dnca_tot_amt'는 예수금총금액. 실제 매수 가능 금액은 'nxdy_excc_amt'에 더 가깝지만,
        # 여기서는 단순화를 위해 예수금총금액을 사용합니다.
        return int(df_balance['dnca_tot_amt'].iloc[0])
    return 0

def _get_stock_sellable_quantity(cycle_id, stock_code):
    """특정 종목의 현재 매도 가능한 수량을 조회합니다."""
    df_holdings, _ = core_logic.get_balance(cycle_id)
    if df_holdings is not None and not df_holdings.empty and 'pdno' in df_holdings.columns:
        holding = df_holdings[df_holdings['pdno'] == stock_code]
        if not holding.empty:
            return int(holding['ord_psbl_qty'].iloc[0]) # 주문 가능 수량
    return 0

def _get_stock_current_value(cycle_id, stock_code):
    """특정 종목의 현재 평가액을 조회합니다."""
    df_holdings, _ = core_logic.get_balance(cycle_id)
    if df_holdings is not None and not df_holdings.empty and 'pdno' in df_holdings.columns:
        holding = df_holdings[df_holdings['pdno'] == stock_code]
        if not holding.empty:
            return int(holding['evlu_amt'].iloc[0]) # 평가 금액
    return 0

# --- Individual Condition Functions ---
def is_trading_hours(cycle_id, stock_code, params):
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

def is_price_below_target(cycle_id, stock_code, params):
    """주식의 현재 가격이 목표 가격(`target_price`)보다 낮은지 확인합니다."""
    if not stock_code: 
        logging.error("is_price_below_target: 'stock_code'가 누락되었습니다.")
        return False

    target_price = params.get('target_price')
    if target_price is None:
        logging.warning("조건 'is_price_below_target': 파라미터에 'target_price'를 찾을 수 없습니다. 거짓으로 간주.")
        return False

    current_price_df = core_logic.get_price(cycle_id, stock_code)
    if current_price_df is None or current_price_df.empty:
        logging.error("조건 'is_price_below_target': 현재가를 가져올 수 없습니다.")
        return False
    
    current_price = int(current_price_df['stck_prpr'].iloc[0])
    
    logging.debug("조건 'is_price_below_target': 현재가=%s, 목표가=%s", current_price, target_price)

    if current_price < target_price:
        logging.debug("조건 'is_price_below_target': 충족.")
        return True
    else:
        logging.debug("조건 'is_price_below_target': 미충족.")
        return False

def has_sufficient_cash(cycle_id, stock_code, params):
    """계좌에 최소 매수 현금(`min_cash_amount`)이 충분한지 확인합니다."""
    min_cash = params.get('min_cash_amount')
    if min_cash is None:
        logging.warning("has_sufficient_cash: 파라미터에 'min_cash_amount'를 찾을 수 없습니다. 거짓으로 간주.")
        return False

    _, df_balance = core_logic.get_balance(cycle_id)
    if df_balance is None or df_balance.empty:
        logging.error("has_sufficient_cash: 계좌 잔고를 가져올 수 없습니다.")
        return False

    current_cash = int(df_balance['dnca_tot_amt'].iloc[0])

    logging.debug("조건 'has_sufficient_cash': 현재 현금=%s, 최소 필요액=%s", current_cash, min_cash)

    if current_cash >= min_cash:
        logging.debug("조건 'has_sufficient_cash': 충족.")
        return True
    else:
        logging.debug("조건 'has_sufficient_cash': 미충족.")
        return False

def is_target_profit_reached(cycle_id, stock_code, params):
    """보유 종목의 수익률이 목표 수익률(`target_profit_percent`)에 도달했는지 확인합니다."""
    if not stock_code: 
        logging.error("is_target_profit_reached: 'stock_code'가 누락되었습니다.")
        return False

    target_profit_percent = params.get('target_profit_percent')
    if target_profit_percent is None:
        logging.warning("조건 'is_target_profit_reached': 파라미터에 'target_profit_percent'를 찾을 수 없습니다. 거짓으로 간주.")
        return False

    df_holdings, _ = core_logic.get_balance(cycle_id)
    if df_holdings is None or df_holdings.empty or 'pdno' not in df_holdings.columns:
        logging.debug("조건 'is_target_profit_reached': 보유 종목이 없거나 데이터가 불완전합니다. 조건 미충족.")
        return False

    holding = df_holdings[df_holdings['pdno'] == stock_code]
    if holding.empty:
        logging.debug("조건 'is_target_profit_reached': 해당 종목(%s)을 보유하고 있지 않습니다. 조건 미충족.", stock_code)
        return False
    
    current_profit_rate = float(holding['prts_rate'].iloc[0])
    
    logging.debug("조건 'is_target_profit_reached': 현재 수익률=%.2f%%, 목표 수익률=%.2f%%", current_profit_rate, target_profit_percent)

    if current_profit_rate >= target_profit_percent:
        logging.debug("조건 'is_target_profit_reached': 충족.")
        return True
    else:
        logging.debug("조건 'is_target_profit_reached': 미충족.")
        return False

def is_stop_loss_reached(cycle_id, stock_code, params):
    """보유 종목의 손실률이 손절매 기준(`stop_loss_percent`)에 도달했는지 확인합니다."""
    if not stock_code: 
        logging.error("is_stop_loss_reached: 'stock_code'가 누락되었습니다.")
        return False

    stop_loss_percent = params.get('stop_loss_percent')
    if stop_loss_percent is None:
        logging.warning("조건 'is_stop_loss_reached': 파라미터에 'stop_loss_percent'를 찾을 수 없습니다. 거짓으로 간주.")
        return False

    df_holdings, _ = core_logic.get_balance(cycle_id)
    if df_holdings is None or df_holdings.empty or 'pdno' not in df_holdings.columns:
        logging.debug("조건 'is_stop_loss_reached': 보유 종목이 없거나 데이터가 불완전합니다. 조건 미충족.")
        return False

    holding = df_holdings[df_holdings['pdno'] == stock_code]
    if holding.empty:
        logging.debug("조건 'is_stop_loss_reached': 해당 종목(%s)을 보유하고 있지 않습니다. 조건 미충족.", stock_code)
        return False
    
    current_profit_rate = float(holding['prts_rate'].iloc[0])
    
    logging.debug("조건 'is_stop_loss_reached': 현재 수익률=%.2f%%, 손절매 기준=%.2f%%", current_profit_rate, stop_loss_percent)

    if current_profit_rate <= stop_loss_percent:
        logging.debug("조건 'is_stop_loss_reached': 충족.")
        return True
    else:
        logging.debug("조건 'is_stop_loss_reached': 미충족.")
        return False

# --- Helper for evaluating a set of conditions ---
def _evaluate_conditions(cycle_id, stock_code, conditions_config):
    """조건 목록을 평가합니다. 현재는 목록의 모든 조건이 'AND' 연산으로 처리됩니다."""
    if not conditions_config:
        return True

    all_conditions_met = True
    for cond in conditions_config:
        cond_name = cond.get('name')
        cond_params = cond.get('params', {})
        
        cond_func = globals().get(cond_name, None) 
        
        if cond_func:
            sig = inspect.signature(cond_func)
            if 'stock_code' in sig.parameters:
                condition_result = cond_func(cycle_id, stock_code, cond_params)
            else:
                condition_result = cond_func(cycle_id, None, cond_params)
            
            if not condition_result:
                all_conditions_met = False
                break
        else:
            logging.error("조건 함수 '%s'를 condition.py에서 찾을 수 없습니다.", cond_name)
            all_conditions_met = False 
            break
            
    return all_conditions_met

# --- Process General Rules ---
def _process_rules(cycle_id, config):
    """
    1. 규칙 기반 평가: `config.json`에 정의된 일반 매매 규칙들을 처리합니다.
    각 규칙의 조건을 평가하고, 조건이 충족되면 해당 규칙에 정의된 전략을 실행합니다.
    """
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
            logging.warning("규칙 '%s'에 전략 파라미터 또는 조건에 'stock_code'가 지정되지 않았습니다. 건너뜁니다.", rule_name)
            continue

        if _evaluate_conditions(cycle_id, rule_stock_code, conditions_config):
            logging.info("규칙 '%s'의 조건 충족. 전략 '%s' 실행.", rule_name, strategy_config.get('name', 'Unnamed Strategy'))
            
            strategy_func_name = strategy_config.get('name')
            if strategy_func_name:
                strategy_func = getattr(strategy, strategy_func_name, None)
                if strategy_func:
                    action = strategy_func(cycle_id, strategy_config.get('params', {}))
                    if action:
                        action['strategy_name'] = rule_name
                        return action
                else:
                    logging.error("전략 함수 '%s'를 strategy.py에서 찾을 수 없습니다.", strategy_func_name)
            else:
                logging.error("규칙 '%s'에 전략 'name'이 정의되지 않았습니다.", rule_name)
        else:
            logging.debug("규칙 '%s'의 조건이 충족되지 않았습니다.", rule_name)
    
    return None

# --- Process Active Forced Trade (State Machine for AUTO/Divisional) ---
def _process_active_forced_trade(cycle_id, config, current_state):
    """진행 중인 강제 거래 상태를 처리하고 다음 매매 행동을 결정합니다."""
    trade_type = current_state['original_trade_type']
    current_phase = current_state['current_phase']
    stock_code = current_state['stock_code']
    total_amount = current_state['total_amount']
    remaining_amount = current_state['remaining_amount']
    total_quantity = current_state['total_quantity']
    remaining_quantity = current_state['remaining_quantity']
    price = current_state['price']
    market = current_state['market']
    division_count = current_state['division_count']
    divisions_done = current_state['divisions_done']
    bought_quantity = current_state['bought_quantity']
    avg_buy_price = current_state['avg_buy_price']
    sell_profit_target_percent = current_state['sell_profit_target_percent']

    current_price_df = core_logic.get_price(cycle_id, stock_code)
    if current_price_df is None or current_price_df.empty:
        logging.error("%s의 현재가를 가져올 수 없어 수량을 계산할 수 없습니다.", stock_code)
        return None
    current_price = int(current_price_df['stck_prpr'].iloc[0])

    if current_price <= 0:
        logging.error("%s의 현재가가 0이하여서 수량을 계산할 수 없습니다.", stock_code)
        return None
    
    order_quantity = 0
    order_amount = 0

    if total_amount > 0 and total_quantity == 0: # 금액 기반 매매
        order_amount = remaining_amount if division_count <= 1 else remaining_amount // (division_count - divisions_done)
        if divisions_done == division_count - 1: order_amount = remaining_amount
        
        if 'BUY' in current_phase:
            available_cash = _get_available_buy_cash(cycle_id)
            if order_amount > available_cash:
                logging.warning("매수 희망 금액(%s원)이 매수 가능액(%s원)을 초과하여 가능액으로 조정합니다.", order_amount, available_cash)
                order_amount = available_cash
            order_quantity = order_amount // current_price
            if order_quantity == 0:
                logging.warning("매수 가능액 부족 또는 현재가 과도하여 1주도 매수할 수 없습니다.")
                return {'status': 'forced_trade_handled'}
            logging.debug("금액 기반 매수 (금액: %s, 수량: %s)", order_amount, order_quantity)
        elif 'SELL' in current_phase:
            order_quantity = _get_stock_sellable_quantity(cycle_id, stock_code)
            if order_quantity <= 0:
                logging.warning("매도할 보유 수량이 없습니다.")
                return {'status': 'forced_trade_handled'}
            logging.debug("금액 기반 매도 (가능 수량: %s)", order_quantity)
    
    elif total_quantity > 0 and total_amount == 0: # 수량 기반 매매
        order_quantity = remaining_quantity if division_count <= 1 else remaining_quantity // (division_count - divisions_done)
        if divisions_done == division_count - 1: order_quantity = remaining_quantity
        logging.debug("수량 기반 매매 (수량: %s)", order_quantity)

    if order_quantity <= 0:
        logging.debug("이번 분할 매매에서 실행할 수량이 없습니다.")
        return {'status': 'forced_trade_handled'}

    # --- AUTO 모드 BUYING 페이즈 ---
    if trade_type == 'AUTO' and current_phase == 'BUYING':
        action = {
            'type': 'BUY', 'stock_code': stock_code, 'quantity': order_quantity, 'price': price, 'market': market, 'strategy_name': 'FORCED_TRADE_AUTO_BUY_DIVISION', 'is_forced_trade': True
        }
        current_state['divisions_done'] += 1
        current_state['remaining_amount'] -= (order_quantity * (price if price > 0 else current_price))
        current_state['remaining_quantity'] -= order_quantity
        
        new_bought_total = current_state['bought_quantity'] + order_quantity
        if new_bought_total > 0:
            current_state['avg_buy_price'] = (current_state['avg_buy_price'] * current_state['bought_quantity'] + current_price * order_quantity) / new_bought_total
        else:
            current_state['avg_buy_price'] = price if price > 0 else current_price
        current_state['bought_quantity'] = new_bought_total

        if current_state['divisions_done'] >= division_count:
            if current_state['bought_quantity'] <= 0:
                logging.warning("AUTO 매매의 매수 단계가 완료되었으나 매수한 수량이 없습니다. 강제 거래를 종료합니다.")
                _save_trade_state({})
                return {'status': 'forced_trade_handled'}
            current_state['current_phase'] = 'SELLING'
            logging.info("AUTO 매매: 매수 단계 완료. 매도 단계로 전환합니다.")
        
        _save_trade_state(current_state)
        return action

    # --- AUTO 모드 SELLING 페이즈 ---
    elif trade_type == 'AUTO' and current_phase == 'SELLING':
        if bought_quantity <= 0:
            logging.warning("AUTO 매매 매도 단계 진입 - 매수된 수량이 없어 강제 거래를 종료합니다.")
            _save_trade_state({})
            return {'status': 'forced_trade_handled'}

        if avg_buy_price > 0:
            current_profit_percent = ((current_price - avg_buy_price) / avg_buy_price) * 100
            logging.debug("AUTO 매매 매도 단계: 현재 수익률 %.2f%% (목표: %.2f%%). 매수단가: %s, 현재가: %s", 
                         current_profit_percent, sell_profit_target_percent, avg_buy_price, current_price)

            if current_profit_percent >= sell_profit_target_percent:
                logging.info("AUTO 매매 매도 단계: 목표 수익률 달성. 전량 매도를 시도합니다.")
                action = {
                    'type': 'SELL', 'stock_code': stock_code, 'quantity': bought_quantity, 'price': 0, 'market': market, 'strategy_name': 'FORCED_TRADE_AUTO_SELL', 'is_forced_trade': True
                }
                # AUTO 모드는 매도 완료 후 다시 매수 단계로 리셋 (반복)
                current_state.update({'current_phase': 'BUYING', 'divisions_done': 0, 'bought_quantity': 0, 'avg_buy_price': 0.0, 'remaining_amount': total_amount, 'remaining_quantity': total_quantity})
                _save_trade_state(current_state)
                logging.info("AUTO 매매: 매도 단계 완료. 다음 사이클에 매수 단계로 재시작합니다.")
                return action
            else:
                logging.debug("AUTO 매매 매도 단계: 아직 목표 수익률에 도달하지 않았습니다. 다음 기회를 기다립니다.")
        else:
            logging.warning("AUTO 매매 매도 단계: 평균 매수 단가가 0이므로 수익률 계산 불가. 매도 보류.")
        return {'status': 'forced_trade_handled'}

    # --- 단순 BUY/SELL (분할 매매 포함) ---
    else:
        action_type = trade_type
        if order_quantity <= 0:
            logging.debug("매매할 수량이 없어 강제 거래를 실행하지 않습니다.")
            return {'status': 'forced_trade_handled'}

        current_state['divisions_done'] += 1
        current_state['remaining_amount'] -= (order_quantity * (price if price > 0 else current_price))
        current_state['remaining_quantity'] -= order_quantity

        if current_state['divisions_done'] >= division_count:
            logging.info("단순 강제 거래 (%s) 모든 분할 완료.", action_type)
            current_state.update({'active': False, 'status': 'completed'})
            _save_trade_state(current_state)
        else:
            logging.info("단순 강제 거래 (%s) %s/%s 분할 완료. 다음 분할 대기.", action_type, current_state['divisions_done'], division_count)
            _save_trade_state(current_state)

        return {
            'type': action_type, 'stock_code': stock_code, 'quantity': order_quantity, 'price': price, 'market': market, 'strategy_name': f'FORCED_TRADE_{action_type}_DIVISION', 'is_forced_trade': True
        }
