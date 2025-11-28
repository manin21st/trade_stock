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

# --- Individual Condition Functions ---
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
        "NXT": (datetime.time(8, 0), datetime.time(20, 0)) # 예시 시간, 필요시 조정
    }
    
    start_time, end_time = market_hours.get(market, market_hours["KRX"])

    if start_time <= current_time <= end_time:
        logging.debug("조건 'is_trading_hours': 충족 (%s 시장 %s-%s 내).", market, start_time.strftime('%H:%M'), end_time.strftime('%H:%M'))
        return True
    else:
        logging.debug("조건 'is_trading_hours': 미충족 (%s 시장 %s-%s 외).", market, start_time.strftime('%H:%M'), end_time.strftime('%H:%M'))
        return False

def check_basics(config):
    """
    모든 거래 로직 실행 전, 반드시 통과해야 할 기본 조건들을 한 번에 묶어서 검사합니다.
    - 현재는 거래 시간 확인만 포함됩니다.
    - 향후 API 접속 상태, 시장 개장 여부 등 다른 기본 조건을 이 함수에 쉽게 추가할 수 있습니다.
    
    :return: 모든 기본 조건 통과 시 True, 하나라도 실패 시 False
    """
    # config에서 trading_market 정보 읽어오기
    market_to_check = config.get('trading_market', 'KRX')

    if not is_trading_hours(params={'check_enabled': True}, market=market_to_check):
        logging.info("기본 실행 조건: 거래 시간이 아닙니다.")
        return False
    
    # 추가적인 기본 조건들...
    
    return True


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
def _evaluate_conditions(cycle_id, stock_code, conditions_config, market_data, config): # config 인자 추가
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
            'market': config.get('strategy_A', {}).get('market', 'KRX') # config에서 market 정보 가져오기
        }
        
        # 함수 시그니처에 따라 필요한 인자만 필터링하여 전달
        sig = inspect.signature(cond_func)
        required_args = {p: kwargs[p] for p in sig.parameters if p in kwargs}

        if not cond_func(**required_args):
            return False
            
    return True

# --- Wait Cycle Check ---
def is_wait_cycle(cycle_id, config): # config 인자는 여기서는 직접 사용 안될 수 있음. trade_state에 이미 다 있음.
    """
    실제 매매 로직을 실행하기 전, 단순히 대기만 해야 하는 사이클인지 가볍게 확인합니다.
    - 활성 규칙의 매도 단계에서 수익률 미달성 시 대기하는 경우가 주요 대상입니다.
    - 이 함수는 최소한의 API 호출(get_price)만 수행하며 로그를 남기지 않습니다.
    """
    active_trade_state = state.load_trade_state()

    # 1. 활성 상태가 아니면 대기 사이클이 아님
    if not active_trade_state.get('active', False):
        return False

    # 2. trade_state에서 필요한 파라미터 가져오기
    strategy_type = active_trade_state.get('original_trade_type') # 'AUTO', 'BUY', 'SELL'
    current_phase = active_trade_state.get('current_phase') # 'BUYING', 'SELLING'
    stock_code = active_trade_state.get('stock_code')
    
    # sell_profit_target_percent와 avg_buy_price는 매도 조건 판단에만 필요
    sell_profit_target = active_trade_state.get('sell_profit_target_percent', 0.0)
    avg_buy_price = active_trade_state.get('avg_buy_price', 0.0)


    # 3. 'AUTO' 전략의 'SELLING' 단계일 때만 대기 여부 체크
    if strategy_type == 'AUTO' and current_phase == 'SELLING':
        # stock_code가 없으면 오류이므로 대기 판단 불가 (아님)
        if not stock_code:
            return False 

        # 로그를 남기지 않고 현재가만 가볍게 조회
        price_df = core_logic.get_price(cycle_id, stock_code)
        
        if price_df is None or price_df.empty:
            # 가격 조회가 안되면, 대기 여부 판단 불가 -> 일단 대기 사이클 아님으로 처리
            return False 

        current_price = int(price_df['stck_prpr'].iloc[0])
        
        if avg_buy_price > 0: # 평균 매수 단가가 있어야 수익률 계산 가능
            current_profit_percent = ((current_price - avg_buy_price) / avg_buy_price) * 100
            if current_profit_percent < sell_profit_target:
                return True # 목표 수익률 미달성이므로 대기 사이클 맞음

    return False # 그 외 모든 경우는 대기 사이클이 아님

# --- Process Active Forced Trade (Refactored) ---
def _calculate_order_quantity(current_state, current_price, available_cash):
    """
    매수 주문에 필요한 수량을 계산합니다. (분할 매수 지원)
    수량 또는 금액 기준에 따라 계산하며, 매수 가능액을 초과하지 않도록 조정합니다.
    """

    # 수량 기반 매수 우선
    if current_state.get('total_quantity', 0) > 0:
        rem_qty = current_state.get('remaining_quantity', 0)
        div_count = current_state.get('division_count', 1)
        div_done = current_state.get('divisions_done', 0)
        
        # 마지막 분할이면 남은 수량 전부, 아니면 계산된 수량
        if div_done >= div_count - 1:
            return rem_qty

        return rem_qty // max(1, (div_count - div_done))

    # 금액 기반 매수
    if current_state.get('total_amount', 0) > 0:
        rem_amt = current_state.get('remaining_amount', 0)
        div_count = current_state.get('division_count', 1)
        div_done = current_state.get('divisions_done', 0)

        # 마지막 분할이면 남은 금액 전부, 아니면 계산된 금액
        order_amount = 0
        if div_done >= div_count - 1:
            order_amount = rem_amt
        else:
            order_amount = rem_amt // max(1, (div_count - div_done))

        if order_amount > available_cash:
            logging.warning(f"매수 희망 금액({order_amount:,}원)이 매수 가능액({available_cash:,}원)을 초과하여 가능액으로 조정합니다.")
            order_amount = available_cash

        if current_price > 0:
            return order_amount // current_price
        else:
            logging.error("현재가가 0이하여서 수량을 계산할 수 없습니다.")
            return 0

    return 0


def _get_auto_buy_action(current_state, market_data):
    """AUTO 모드의 매수 단계를 처리하고 매수 action을 결정합니다."""
    stock_code = current_state['stock_code']
    price_df = market_data.get('price_df', {}).get(stock_code)
    balance_df = market_data.get('balance_df')

    # 목표 수량 달성 시 매도 단계로 전환
    if current_state.get('remaining_quantity', 0) <= 0 and current_state.get('total_quantity', 0) > 0:
        logging.info("AUTO 매매: 목표 수량을 이미 보유하고 있거나 초과하여 매수 단계를 건너뜁니다.")
        state.set_trade_state_value('current_phase', 'SELLING')
        return {'status': 'forced_trade_handled'}

    current_price = int(price_df['stck_prpr'].iloc[0])
    available_cash = _get_available_buy_cash(balance_df)

    order_quantity = _calculate_order_quantity(current_state, current_price, available_cash)
    order_quantity = max(0, order_quantity)

    if order_quantity <= 0:
        logging.debug("AUTO 매매: 이번 분할 매수에서 실행할 수량이 없거나, 매수 가능액이 부족합니다.")
        return {'status': 'forced_trade_handled'}

    # 상태 업데이트는 실제 주문 성공 후 main_cmd에서 처리
    return {
        'type': 'BUY',
        'stock_code': stock_code,
        'quantity': order_quantity,
        'price': current_state.get('price', 0),
        'market': current_state.get('market', "KRX"),
        'strategy_name': 'FORCED_TRADE_AUTO_BUY',
        'is_forced_trade': True,
        'current_price': current_price # 상태 업데이트 시 필요
    }

def _get_auto_sell_action(current_state, market_data):
    """AUTO 모드의 매도 단계를 처리하고 매도 action을 결정합니다."""
    stock_code = current_state['stock_code']
    holdings_df = market_data.get('holdings_df')
    price_df = market_data.get('price_df', {}).get(stock_code)

    if current_state.get('bought_quantity', 0) <= 0:
        logging.warning("AUTO 매매 매도 단계: 매도할 보유 수량이 없어 강제 거래를 종료합니다.")
        state.save_trade_state({'active': False})
        return {'status': 'forced_trade_handled'}

    avg_buy_price = current_state.get('avg_buy_price', 0.0)
    sell_profit_target = current_state.get('sell_profit_target_percent', 0.0)
    current_price = int(price_df['stck_prpr'].iloc[0])

    if avg_buy_price <= 0:
        logging.warning("AUTO 매매 매도 단계: 평균 매수 단가가 0이므로 수익률 계산 불가. 매도 보류.")
        return {'status': 'forced_trade_handled'}

    current_profit_percent = ((current_price - avg_buy_price) / avg_buy_price) * 100
    logging.debug(f"AUTO 매매 매도 단계: 현재 수익률 {current_profit_percent:.2f}% (목표: {sell_profit_target}%)")

    if current_profit_percent < sell_profit_target:
        return {'status': 'forced_trade_handled'} # 목표 수익률 미도달

    sell_quantity = _get_stock_sellable_quantity(stock_code, holdings_df)
    if sell_quantity <= 0:
        logging.warning("AUTO 매매: 목표 수익률 도달했으나 매도 가능 수량이 없습니다.")
        return {'status': 'forced_trade_handled'}

    return {
        'type': 'SELL',
        'stock_code': stock_code,
        'quantity': sell_quantity,
        'price': 0, # 시장가 매도
        'market': current_state.get('market', "KRX"),
        'strategy_name': 'FORCED_TRADE_AUTO_SELL',
        'is_forced_trade': True
    }

def _get_simple_trade_action(current_state, market_data):
    """단순 강제 매수/매도 action을 결정합니다."""
    action_type = current_state['original_trade_type']
    stock_code = current_state['stock_code']
    price_df = market_data.get('price_df', {}).get(stock_code)

    order_quantity = 0
    if action_type == 'SELL':
        order_quantity = _get_stock_sellable_quantity(stock_code, market_data.get('holdings_df'))

    elif action_type == 'BUY':
        current_price = int(price_df['stck_prpr'].iloc[0])
        available_cash = _get_available_buy_cash(market_data.get('balance_df'))
        order_quantity = _calculate_order_quantity(current_state, current_price, available_cash)

    order_quantity = max(0, order_quantity)

    if order_quantity <= 0:
        logging.debug("단순 강제 거래: 매매할 수량이 없어 거래를 실행하지 않습니다.")
        # 모든 분할이 완료되었거나 더 이상 진행할 수 없으면 상태 종료
        if current_state.get('divisions_done', 0) >= current_state.get('division_count', 1):
            logging.info(f"단순 강제 거래({action_type}): 모든 분할이 완료되어 거래를 종료합니다.")
            state.save_trade_state({'active': False})

        return {'status': 'forced_trade_handled'}

    return {
        'type': action_type,
        'stock_code': stock_code,
        'quantity': order_quantity,
        'price': current_state.get('price', 0),
        'market': current_state.get('market', "KRX"),
        'strategy_name': f'FORCED_TRADE_{action_type}',
        'is_forced_trade': True,
        'current_price': int(price_df['stck_prpr'].iloc[0]) if price_df is not None and not price_df.empty else 0
    }

def find_action_to_take(cycle_id, config):
    """
    현재 매매 사이클에서 활성 전략(`active_rule_name`)에 따라 취할 행동을 '결정'하고,
    사용된 시장 데이터와 함께 반환합니다. 실제 거래 실행은 하지 않습니다.
    """
    logging.debug("[%s] 매매 행동 결정 시작...", cycle_id)
    
    active_trade_state = state.load_trade_state()

    # 1. 활성 전략이 없거나 비활성화되어 있으면 할 일 없음
    if not active_trade_state.get('active', False):
        logging.debug("[%s] 활성 매매 전략이 없습니다.", cycle_id)
        return None, {'price_df': {}, 'holdings_df': None, 'balance_df': None}

    # 2. 활성 전략의 파라미터 가져오기
    active_rule_name = active_trade_state.get('active_rule_name')
    trade_type = active_trade_state.get('original_trade_type') # 'AUTO', 'BUY', 'SELL'
    current_phase = active_trade_state.get('current_phase') # 'BUYING', 'SELLING'
    stock_code = active_trade_state.get('stock_code')

    # 3. 필요한 모든 종목 코드 수집 (현재는 활성 전략의 종목만 해당)
    all_stock_codes = {stock_code}
    all_stock_codes.discard(None) # Set for single stock

    # 4. 모든 데이터 한 번에 조회
    market_data = {'price_df': {}, 'holdings_df': None, 'balance_df': None}
    
    market_data['holdings_df'], market_data['balance_df'] = core_logic.get_balance(cycle_id)
    if stock_code: # 종목 코드가 있으면 시세 조회
        market_data['price_df'][stock_code] = core_logic.get_price(cycle_id, stock_code)

    # 5. 활성 전략에 따른 매매 행동 결정 로직 수행
    # 기존 _process_active_forced_trade 로직을 여기에 통합
    
    # 공통 예외 처리 (가격 데이터 없음 등)
    price_df = market_data.get('price_df', {}).get(stock_code)
    if price_df is None or price_df.empty:
        logging.error(f"강제거래: {stock_code}의 현재가를 가져올 수 없어 거래를 진행할 수 없습니다.")
        return {'status': 'forced_trade_handled'}, market_data # 오류 상태 반환

    current_price = int(price_df['stck_prpr'].iloc[0])
    if current_price <= 0 and trade_type != 'SELL':
        logging.error(f"강제거래: {stock_code}의 현재가가 0이하여서 수량을 계산할 수 없습니다.")
        return {'status': 'forced_trade_handled'}, market_data

    # --- AUTO 모드 ---
    if trade_type == 'AUTO':
        if current_phase == 'BUYING':
            action = _get_auto_buy_action(active_trade_state, market_data)
        elif current_phase == 'SELLING':
            action = _get_auto_sell_action(active_trade_state, market_data)
        else: # 알 수 없는 페이즈
            logging.warning("알 수 없는 강제 거래 페이즈(%s)입니다. 규칙: %s", current_phase, active_rule_name)
            action = None
    # --- 단순 BUY/SELL 모드 ---
    elif trade_type in ['BUY', 'SELL']:
        action = _get_simple_trade_action(active_trade_state, market_data)
    else: # 알 수 없는 매매 타입
        logging.warning("알 수 없는 강제 거래 타입(%s)입니다. 규칙: %s", strategy_type, active_rule_name)
        action = None
    
    if action:
        action['strategy_name'] = active_rule_name # 기존 필드 재활용
        return action, market_data

    logging.debug("[%s] 이번 사이클에 취할 매매 행동이 없습니다.", cycle_id)
    return None, market_data
