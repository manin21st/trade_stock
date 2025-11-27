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
import datetime
import os
import inspect
import state

import core_logic
import strategy
import trade # Add this line

# 이 스크립트(condition.py)는 src 폴더 안에 있으므로, 상위 폴더가 프로젝트 루트가 됩니다.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = os.path.join(PROJECT_ROOT, 'json', 'config.json')

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
def is_trading_hours(params, market='KRX', **kwargs):
    """현재 시간이 지정된 시장의 거래 시간 내인지 확인합니다."""
    check_enabled = params.get('check_enabled', True)
    if not check_enabled:
        logging.debug("조건 'is_trading_hours': 확인 비활성화. 참으로 간주.")
        return True

    now = datetime.datetime.now()
    current_time = now.time()
    
    # 주말(토요일=5, 일요일=6)은 거래일이 아님
    if now.weekday() >= 5:
        logging.debug("조건 'is_trading_hours': 주말(토/일)이므로 거래 시간이 아닙니다.")
        return False

    market_hours = {
        "KRX": (datetime.time(9, 0), datetime.time(15, 30)),
        "NXT": (datetime.time(8, 0), datetime.time(18, 0)) # 예시 시간, 필요시 조정
    }
    
    start_time, end_time = market_hours.get(market, market_hours["KRX"])

    if start_time <= current_time <= end_time:
        logging.debug("조건 'is_trading_hours': 충족 (%s 시장 %s-%s 내).", market, start_time.strftime('%H:%M'), end_time.strftime('%H:%M'))
        return True
    else:
        logging.debug("조건 'is_trading_hours': 미충족 (%s 시장 %s-%s 외).", market, start_time.strftime('%H:%M'), end_time.strftime('%H:%M'))
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
            'balance_df': market_data.get('balance_df'),
            'market': strategy_config.get('params', {}).get('market', 'KRX') if 'strategy_config' in locals() else 'KRX'
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
    trade_type = current_state['original_trade_type']
    current_phase = current_state['current_phase']
    stock_code = current_state['stock_code']
    market = current_state.get('market', "KRX")
    total_amount = current_state.get('total_amount', 0)
    remaining_amount = current_state.get('remaining_amount', 0)
    total_quantity = current_state.get('total_quantity', 0)
    remaining_quantity = current_state.get('remaining_quantity', 0)
    price = current_state.get('price', 0)
    division_count = current_state.get('division_count', 1)
    divisions_done = current_state.get('divisions_done', 0)
    bought_quantity = current_state.get('bought_quantity', 0)
    avg_buy_price = current_state.get('avg_buy_price', 0.0)
    sell_profit_target_percent = current_state.get('sell_profit_target_percent', 0.0)

    # --- 데이터 준비 ---
    price_df = market_data.get('price_df', {}).get(stock_code)
    holdings_df = market_data.get('holdings_df')
    balance_df = market_data.get('balance_df')

    # FIX: 강제 거래는 해당 시장의 거래 시간 내에만 실행되어야 합니다.
    if not is_trading_hours(params={'check_enabled': True}, market=market):
        logging.info("강제 거래: 현재는 %s 시장의 거래 시간이 아니므로 대기합니다.", market)
        return {'status': 'forced_trade_handled'}

    if price_df is None or price_df.empty:
        logging.error("강제거래: %s의 현재가를 가져올 수 없어 거래를 진행할 수 없습니다.", stock_code)
        return {'status': 'forced_trade_handled'}
    current_price = int(price_df['stck_prpr'].iloc[0])

    if current_price <= 0:
        logging.error("강제거래: %s의 현재가가 0이하여서 수량을 계산할 수 없습니다.", stock_code)
        return {'status': 'forced_trade_handled'}

    # --- AUTO 모드 초기화 (첫 실행 시 기존 보유 수량 반영) ---
    if trade_type == 'AUTO' and divisions_done == 0 and bought_quantity == 0 and current_phase == 'BUYING':
        logging.info("AUTO 모드 강제 거래 초기화: 기존 보유 수량을 확인합니다.")
        existing_holding = holdings_df[holdings_df['pdno'] == stock_code] if holdings_df is not None and not holdings_df.empty else None
        
        if existing_holding is not None and not existing_holding.empty:
            existing_qty = int(existing_holding['hldg_qty'].iloc[0])
            existing_avg_price = float(existing_holding['pchs_avg_pric'].iloc[0])
            logging.info("기존 보유 수량: %s주, 평균 단가: %s원", existing_qty, existing_avg_price)
            
            current_state['bought_quantity'] = existing_qty
            current_state['avg_buy_price'] = existing_avg_price

            if total_quantity > 0:
                new_remaining_qty = max(0, total_quantity - existing_qty)
                current_state['remaining_quantity'] = new_remaining_qty
                logging.info("수량 기반 AUTO 모드: 목표 %s주 중 %s주 보유, %s주 추가 매수 필요.", total_quantity, existing_qty, new_remaining_qty)
            
            state.save_trade_state(current_state)
            # 상태가 변경되었으므로, 변수를 최신 상태로 업데이트
            remaining_quantity = current_state['remaining_quantity']
            bought_quantity = current_state['bought_quantity']
            avg_buy_price = current_state['avg_buy_price']

    # --- 주문 수량 계산 ---
    order_quantity = 0
    if 'BUY' in current_phase:
        if total_quantity > 0: # 수량 기반 매수 우선
            # 남은 수량을 분할 매수 (total_quantity와 remaining_quantity를 사용)
            order_quantity = remaining_quantity if division_count <= 1 else remaining_quantity // max(1, (division_count - divisions_done))
            if divisions_done == division_count - 1: order_quantity = remaining_quantity
            
        elif total_amount > 0: # 금액 기반 매수 (total_amount와 remaining_amount를 사용)
            # 남은 금액을 분할 매수
            order_amount = remaining_amount if division_count <= 1 else remaining_amount // max(1, (division_count - divisions_done))
            if divisions_done == division_count - 1: order_amount = remaining_amount
            
            available_cash = _get_available_buy_cash(balance_df)
            if order_amount > available_cash:
                logging.warning("매수 희망 금액(%s원)이 매수 가능액(%s원)을 초과하여 가능액으로 조정합니다.", order_amount, available_cash)
                order_amount = available_cash
            
            order_quantity = order_amount // current_price
            if order_quantity == 0:
                logging.warning("매수 가능액 부족 또는 현재가 과도하여 1주도 매수할 수 없습니다.")

    if order_quantity < 0: order_quantity = 0

    # --- 상태에 따른 행동 결정 ---
    # AUTO 모드 BUYING
    if trade_type == 'AUTO' and current_phase == 'BUYING':
        if remaining_quantity <= 0 and total_quantity > 0:
            logging.info("AUTO 매매: 목표 수량을 이미 보유하고 있거나 초과하여 매수 단계를 건너뜁니다.")
            current_state['current_phase'] = 'SELLING'
            state.save_trade_state(current_state)
            return {'status': 'forced_trade_handled'}

        if order_quantity <= 0:
            logging.debug("AUTO 매매: 이번 분할 매수에서 실행할 수량이 없거나, 매수 가능액이 부족합니다.")
            return {'status': 'forced_trade_handled'}

        action = {'type': 'BUY', 'stock_code': stock_code, 'quantity': order_quantity, 'price': price, 'market': market, 'strategy_name': 'FORCED_TRADE_AUTO_BUY_DIVISION', 'is_forced_trade': True}
        
        trade_successful = trade.order_buy(cycle_id, stock_code, order_quantity, price, market) # state 인자 제거
        if trade_successful:
            logging.info("AUTO 매수 주문 성공. 상태 업데이트 진행.")
            current_state['divisions_done'] += 1
            current_state['remaining_quantity'] -= order_quantity
            # remaining_amount는 current_state['total_amount']를 기반으로 재계산
            # 정확한 매수 단가는 체결 정보를 조회해야 하지만, 여기서는 임시로 주문가 사용
            actual_buy_price = price if price != 0 else current_price # 시장가일 경우 현재가를 추정치로 사용
            
            new_bought_total = current_state['bought_quantity'] + order_quantity
            if new_bought_total > 0:
                current_state['avg_buy_price'] = (current_state['avg_buy_price'] * current_state['bought_quantity'] + actual_buy_price * order_quantity) / new_bought_total
            current_state['bought_quantity'] = new_bought_total

            if current_state['divisions_done'] >= division_count or current_state['remaining_quantity'] <= 0:
                current_state['current_phase'] = 'SELLING'
                logging.info("AUTO 매매: 매수 단계 완료. 총 %s주 보유, 평균 단가 %s. 매도 단계로 전환합니다.", current_state['bought_quantity'], current_state['avg_buy_price'])
            
            state.save_trade_state(current_state)
            return action
        else:
            logging.error("AUTO 매수 주문 실패. 상태를 유지하고 다음 사이클을 대기합니다.")
            return {'status': 'forced_trade_handled'}


    # AUTO 모드 SELLING
    elif trade_type == 'AUTO' and current_phase == 'SELLING':
        if bought_quantity <= 0:
            logging.warning("AUTO 매매 매도 단계: 매도할 보유 수량이 없어 강제 거래를 종료합니다.")
            state.save_trade_state({}) # 더 이상 진행할 게 없으므로 여기서는 상태 초기화
            return {'status': 'forced_trade_handled'}

        if avg_buy_price > 0:
            current_profit_percent = ((current_price - avg_buy_price) / avg_buy_price) * 100
            logging.debug("AUTO 매매 매도 단계: 현재 수익률 %.2f%% (목표: %.2f%%), 보유: %s주, 평단: %s, 현재가: %s", 
                         current_profit_percent, sell_profit_target_percent, bought_quantity, avg_buy_price, current_price)

            if current_profit_percent >= sell_profit_target_percent:
                sell_quantity = _get_stock_sellable_quantity(stock_code, holdings_df)
                if sell_quantity <= 0:
                    logging.warning("AUTO 매매: 목표 수익률 도달했으나 매도 가능 수량이 없습니다.")
                    return {'status': 'forced_trade_handled'}

                logging.info("AUTO 매매: 목표 수익률 달성. 보유 수량 %s주 전량 매도를 시도합니다.", sell_quantity)
                action = {'type': 'SELL', 'stock_code': stock_code, 'quantity': sell_quantity, 'price': 0, 'market': market, 'strategy_name': 'FORCED_TRADE_AUTO_SELL', 'is_forced_trade': True}
                
                trade_successful = trade.order_sell(cycle_id, stock_code, sell_quantity, 0, market) # state 인자 제거
                        if trade_successful:
                            logging.info("AUTO 매도 주문 성공. 새로운 매수 사이클을 위해 상태를 재설정합니다.")
                            
                            # 상태 재설정: BUYING 단계로 전환하고 필요한 값 초기화
                            current_state['current_phase'] = 'BUYING'
                            current_state['divisions_done'] = 0
                            current_state['bought_quantity'] = 0
                            current_state['avg_buy_price'] = 0.0
                            current_state['remaining_quantity'] = current_state['total_quantity'] # 목표 수량으로 초기화
                            current_state['remaining_amount'] = current_state['total_amount'] # 목표 금액으로 초기화
                            current_state['trade_id'] = f"AUTO_REPEATED_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}" # 새로운 거래 ID
                            current_state['last_action_timestamp'] = datetime.datetime.now().isoformat()
                            
                            state.save_trade_state(current_state) # 재설정된 상태 저장
                            return action                else:
                    logging.error("AUTO 매도 주문 실패. 상태를 유지하고 다음 사이클을 대기합니다.")
                    return {'status': 'forced_trade_handled'}
        else:
            logging.warning("AUTO 매매 매도 단계: 평균 매수 단가가 0이므로 수익률 계산 불가. 매도 보류.")

        return {'status': 'forced_trade_handled'}

    # 단순 BUY/SELL
    elif trade_type in ['BUY', 'SELL']:
        action_type = trade_type
        order_quantity_to_execute = 0 # 주문 실행될 수량

        if action_type == 'SELL':
            order_quantity_to_execute = _get_stock_sellable_quantity(stock_code, holdings_df)
        elif action_type == 'BUY':
             # 금액 기반, 수량 기반 계산 등 위 AUTO 로직의 일부를 가져와야 함
            if total_amount > 0 and total_quantity == 0:
                 order_amount = remaining_amount if division_count <= 1 else remaining_amount // max(1, (division_count - divisions_done))
                 if divisions_done == division_count - 1: order_amount = remaining_amount
                 order_quantity_to_execute = order_amount // current_price if current_price > 0 else 0
            elif total_quantity > 0: # 수량 기반
                 order_quantity_to_execute = remaining_quantity if division_count <= 1 else remaining_quantity // max(1, (division_count - divisions_done))
                 if divisions_done == division_count - 1: order_quantity_to_execute = remaining_quantity
        
        if order_quantity_to_execute <= 0:
            logging.debug("단순 강제 거래: 매매할 수량이 없어 거래를 실행하지 않습니다.")
            return {'status': 'forced_trade_handled'}

        action = {'type': action_type, 'stock_code': stock_code, 'quantity': order_quantity_to_execute, 'price': price, 'market': market, 'strategy_name': f'FORCED_TRADE_{action_type}_DIVISION', 'is_forced_trade': True}

        trade_successful = False
        if action_type == 'BUY':
            trade_successful = trade.order_buy(cycle_id, stock_code, order_quantity_to_execute, price, market)
        elif action_type == 'SELL':
            trade_successful = trade.order_sell(cycle_id, stock_code, order_quantity_to_execute, price, market)
        
        if trade_successful:
            logging.info("단순 강제 거래 (%s) 주문 성공. 상태 업데이트 진행.", action_type)
            current_state['divisions_done'] += 1
            if current_state['divisions_done'] >= division_count:
                logging.info("단순 강제 거래 (%s) 모든 분할 완료. 상태 초기화.", action_type)
                state.save_trade_state({})
            else:
                logging.info("단순 강제 거래 (%s) %s/%s 분할 완료. 상태 저장.", action_type, current_state['divisions_done'], division_count)
                state.save_trade_state(current_state)
            return action
        else:
            logging.error("단순 강제 거래 (%s) 주문 실패. 상태를 유지하고 다음 사이클을 대기합니다.", action_type)
            return {'status': 'forced_trade_handled'}

    return None



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
    trade_state = state.load_trade_state()
    forced_trade_config = config.get('forced_trade', {})
    
    if (forced_trade_config.get('enabled') and trade_state.get('active')):
        logging.info("[%s] 활성 강제 거래 처리 중: %s", cycle_id, trade_state.get('trade_id', 'N/A'))
        action = _process_active_forced_trade(cycle_id, config, trade_state, market_data)
        
        # 강제 거래 로직이 어떤 행동을 결정했으면 (BUY/SELL) 그것을 바로 반환
        if action and action.get('type') in ['BUY', 'SELL']:
            return action
        
        # 강제 거래가 활성화되어 있지만, 현재 사이클에서 매매 action이 없었던 경우 (예: 대기 상태)
        # 이 경우, 일반 규칙을 평가할 필요 없이 바로 함수 종료
        # _process_active_forced_trade가 'forced_trade_handled'를 반환하면 이곳으로 오게 됩니다.
        if action and action.get('status') == 'forced_trade_handled':
            return action # 'forced_trade_handled' 상태를 그대로 main_cmd.py에 전달
        
        # 만약 강제 거래가 활성화되어 있지만, _process_active_forced_trade가 None을 반환한 경우 (예외 상황)
        # 이 경우도 일반 규칙을 평가하지 않고 종료하는 것이 합리적입니다.
        return None # 또는 {'status': 'no_action_in_forced_trade'}

    # 3. 일반 규칙 처리
    logging.debug("[%s] 일반 매매 규칙 평가 중...", cycle_id)
    action = _process_rules(cycle_id, config, market_data)
    if action:
        return action

    logging.debug("[%s] 이번 사이클에 취할 매매 행동이 없습니다.", cycle_id)
    return None


