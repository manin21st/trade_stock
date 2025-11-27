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
    current_app_state = load_trade_state()
    forced_trade_config = config.get('forced_trade', {})

    if forced_trade_config.get('enabled'):
        logging.info("강제 거래 활성화됨. 새로운 강제 거래 상태를 초기화합니다.")
        stock_code = forced_trade_config.get('stock_code')
        
        # 실제 보유 수량을 조회하여 초기 상태에 반영
        actual_balance = core_logic.get_stock_balance(stock_code)
        init_qty = actual_balance.get('quantity', 0) if actual_balance else 0
        init_avg_price = actual_balance.get('avg_buy_price', 0.0) if actual_balance else 0.0
        
        if init_qty > 0:
            logging.info(f"초기 강제 거래: 종목 {stock_code}의 기존 보유 수량 {init_qty}주, 평균 단가 {init_avg_price}원 반영.")
        
        new_trade_state = {
            'active': True,
            'trade_id': f"FORCED_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            'status': 'pending',
            'original_trade_type': forced_trade_config.get('trade_type', 'BUY'),
            'current_phase': 'BUYING' if forced_trade_config.get('trade_type') == 'AUTO' else forced_trade_config.get('trade_type'),
            'stock_code': stock_code,
            'total_amount': forced_trade_config.get('amount', 0),
            'remaining_amount': forced_trade_config.get('amount', 0),
            'total_quantity': forced_trade_config.get('quantity', 0),
            'remaining_quantity': forced_trade_config.get('quantity', 0) - init_qty,
            'price': forced_trade_config.get('price', 0),
            'market': forced_trade_config.get('market', 'KRX'),
            'division_count': forced_trade_config.get('division_count', 1),
            'divisions_done': 0,
            'bought_quantity': init_qty,
            'avg_buy_price': init_avg_price,
            'sell_profit_target_percent': forced_trade_config.get('sell_profit_target_percent', 0.5),
            'last_action_timestamp': datetime.datetime.now().isoformat()
        }
        return save_trade_state(new_trade_state)
    else:
        # 강제 거래가 비활성화된 경우, 기존 상태를 유지하거나, active=False로 초기화
        if not current_app_state.get('active'):
            return save_trade_state({'active': False})
        else:
            logging.info("강제 거래가 비활성화되었지만, 기존 활성 상태를 유지합니다.")
            return save_trade_state(current_app_state)


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