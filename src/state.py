# -*- coding: utf-8 -*-
"""
state.py - 애플리케이션 상태 관리 모듈

이 모듈은 `trade_state.json` 파일의 CRUD(Create, Read, Update, Delete)를 포함하여,
애플리케이션의 영속적인 상태 관리와 관련된 모든 데이터 처리 로직을 담당합니다.
외부 모듈은 이 모듈의 API를 통해서만 상태 데이터에 접근하고 수정해야 합니다.
"""
import json
import os
import logging
import datetime
import core_logic

# --- 파일 경로 설정 ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADE_STATE_FILE = os.path.join(PROJECT_ROOT, 'json', 'trade_state.json')


# --- Core CRUD 및 기본 API 함수 ---

def init_trade_state(config):
    """
    config.json을 기반으로 `trade_state.json`을 초기화하거나 업데이트합니다.
    `main_cmd.py`에서 프로그램 시작 시 한 번만 호출됩니다.
    """
    # current_app_state = load_trade_state() # 이 시점에서는 항상 초기화되므로 이전 상태 로드는 불필요

    # 1. config에서 활성 trading_rule 이름 가져오기
    active_rule_name = config.get('trading_rule')
    if not active_rule_name:
        logging.info("활성 trading_rule이 config에 지정되지 않았습니다. 강제 매매를 비활성화합니다.")
        return save_trade_state({'active': False})
    
    # 2. config의 rules 배열에서 해당 rule 찾기
    active_rule_config = None
    for rule in config.get('rules', []):
        if rule.get('rule_name') == active_rule_name:
            active_rule_config = rule
            break
    
    if not active_rule_config:
        logging.error(f"지정된 활성 규칙 '{active_rule_name}'을 config.json의 rules에서 찾을 수 없습니다. 강제 매매를 비활성화합니다.")
        return save_trade_state({'active': False})

    # 3. 활성 규칙의 enabled 플래그 확인 (규칙 자체를 비활성화할 경우)
    if not active_rule_config.get('enabled', True):
        logging.info(f"규칙 '{active_rule_name}'이(가) 비활성화되어 있습니다. 강제 매매를 비활성화합니다.")
        return save_trade_state({'active': False})

    # 4. active_rule_config에서 파라미터 추출 및 trade_state 초기화
    logging.info(f"활성 규칙 '{active_rule_name}'으로 강제 매매 초기화 중...")
    
    # 규칙 파라미터에서 stock_code 가져오기. 없으면 기본 값 또는 오류 처리
    stock_code = active_rule_config.get('stock_code')
    if not stock_code:
        logging.error(f"규칙 '{active_rule_name}'에 stock_code가 지정되지 않았습니다. 강제 매매를 비활성화합니다.")
        return save_trade_state({'active': False})
    
    # 실제 보유 수량을 조회하여 초기 상태에 반영
    actual_balance = core_logic.get_stock_balance(stock_code)
    init_qty = actual_balance.get('quantity', 0) if actual_balance else 0
    init_avg_price = actual_balance.get('avg_buy_price', 0.0) if actual_balance else 0.0
    
    if init_qty > 0:
        logging.info(f"초기 강제 거래: 종목 {stock_code}의 기존 보유 수량 {init_qty}주, 평균 단가 {init_avg_price}원 반영.")
    
    # trade_state에 저장될 기본 파라미터 구성
    rule_params = active_rule_config.get('params', active_rule_config) # 'params' 키 아래에 있을 수도 있고, rule 자체가 파라미터일 수도 있음
    
    new_trade_state = {
        'active': True,
        'trade_id': f"{active_rule_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        'status': 'pending',
        'active_rule_name': active_rule_name, # 새로운 필드: 활성 규칙의 이름
        'original_trade_type': rule_params.get('trade_type', 'AUTO'), # 기존 필드 재활용
        'current_phase': 'BUYING' if rule_params.get('trade_type') == 'AUTO' else rule_params.get('trade_type'),
        'stock_code': stock_code,
        'total_amount': rule_params.get('amount', 0),
        'remaining_amount': rule_params.get('amount', 0),
        'total_quantity': rule_params.get('quantity', 0),
        'remaining_quantity': rule_params.get('quantity', 0) - init_qty,
        'price': rule_params.get('price', 0),
        'market': config.get('trading_market', 'KRX'), # 최상위 trading_market 사용
        'division_count': rule_params.get('division_count', 1),
        'divisions_done': 0,
        'bought_quantity': init_qty,
        'avg_buy_price': init_avg_price,
        'sell_profit_target_percent': rule_params.get('sell_profit_target_percent', 0.5),
        'last_action_timestamp': datetime.datetime.now().isoformat()
    }
    return save_trade_state(new_trade_state)


def load_trade_state():
    """`trade_state.json` 파일에서 전체 상태 딕셔너리를 로드합니다."""
    try:
        if os.path.exists(TRADE_STATE_FILE):
            with open(TRADE_STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                return state
        return {'active': False} # 파일이 없으면 기본 비활성 상태 반환
    except Exception as e:
        logging.error(f"거래 상태 로드 중 오류 발생: {e}")
        return {'active': False}

def save_trade_state(state_dict):
    """전달받은 상태 딕셔너리를 `trade_state.json` 파일에 저장합니다."""
    try:
        with open(TRADE_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, indent=4, ensure_ascii=False)
        logging.debug(f"거래 상태 저장됨: {state_dict}")
        return True
    except Exception as e:
        logging.error(f"거래 상태 저장 중 오류 발생: {e}")
        return False

def get_trade_state_value(key, default=None):
    """`trade_state`에서 특정 키의 값을 안전하게 읽어옵니다."""
    state = load_trade_state()
    return state.get(key, default)

def set_trade_state_value(key, value):
    """`trade_state`에서 특정 키의 값을 설정하고 즉시 파일에 저장합니다."""
    try:
        state = load_trade_state()
        state[key] = value
        return save_trade_state(state)
    except Exception as e:
        logging.error(f"'{key}' 값 설정 중 오류 발생: {e}")
        return False

# --- 복합 상태 계산 및 저장 함수 ---

def update_trade_state_after_buy(current_state, order_quantity, buy_price):
    """
    매수 성공 후, 파생되는 상태 값들을 계산하고 파일에 직접 저장합니다.
    성공 여부를 반환합니다.
    """
    try:
        new_state = current_state.copy()
        
        # 1. 새로운 총 보유 수량 및 평균 단가 계산
        bought_qty_before = new_state.get('bought_quantity', 0)
        avg_price_before = new_state.get('avg_buy_price', 0.0)
        
        new_bought_quantity = bought_qty_before + order_quantity
        if new_bought_quantity > 0:
            new_avg_price = ((avg_price_before * bought_qty_before) + (buy_price * order_quantity)) / new_bought_quantity
            new_state['avg_buy_price'] = new_avg_price

        new_state['bought_quantity'] = new_bought_quantity

        # 2. 남은 매수 목표 수량 및 분할 실행 횟수 업데이트
        new_state['remaining_quantity'] = new_state.get('remaining_quantity', 0) - order_quantity
        new_state['divisions_done'] = new_state.get('divisions_done', 0) + 1
        new_state['last_action_timestamp'] = datetime.datetime.now().isoformat()
        
        # 3. 매수 완료 여부 체크 및 상태 전환
        if new_state.get('original_trade_type') == 'AUTO':
            if new_state['divisions_done'] >= new_state['division_count'] or new_state['remaining_quantity'] <= 0:
                new_state['current_phase'] = 'SELLING'
                logging.info(f"AUTO 매매: 매수 단계 완료. 총 {new_state['bought_quantity']}주 보유(평단: {new_state['avg_buy_price']:.2f}). 매도 단계로 전환.")

        return save_trade_state(new_state)

    except Exception as e:
        logging.error(f"매수 후 상태 업데이트 중 오류: {e}")
        return False


def reset_trade_state_for_auto_cycle(current_state):
    """
    'AUTO' 모드에서 매도 성공 후, 다음 매수 사이클을 위해 상태를 초기화하고 직접 저장합니다.
    성공 여부를 반환합니다.
    """
    try:
        new_state = current_state.copy()

        # 1. 다음 사이클을 위한 값으로 리셋
        new_state['current_phase'] = 'BUYING'
        new_state['divisions_done'] = 0
        new_state['bought_quantity'] = 0
        new_state['avg_buy_price'] = 0.0
        # 목표 수량/금액으로 복원
        new_state['remaining_quantity'] = new_state.get('total_quantity', 0)
        new_state['remaining_amount'] = new_state.get('total_amount', 0)
        # 새로운 거래 ID 부여
        new_state['trade_id'] = f"AUTO_REPEATED_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        new_state['last_action_timestamp'] = datetime.datetime.now().isoformat()
        
        logging.info("AUTO 매매: 매도 완료. 새로운 매수 사이클을 위해 상태를 재설정합니다.")
        return save_trade_state(new_state)

    except Exception as e:
        logging.error(f"AUTO 사이클 상태 재설정 중 오류: {e}")
        return False