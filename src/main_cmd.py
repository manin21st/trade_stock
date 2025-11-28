# -*- coding: utf-8 -*-
"""
main_cmd.py - 클라우드 기반 자동매매 엔진

이 스크립트는 한국투자증권(KIS) Open API를 활용한 자동매매 시스템의 핵심 엔진입니다.
클라우드 서버 환경에서 헤드리스(Headless) 모드로 동작하며, `config.json`에 정의된
전략에 따라 주식 매매를 자동으로 실행합니다.

주요 기능:
1.  **API 인증**: 프로그램 시작 시 KIS API에 접속하여 거래를 준비합니다.
2.  **전략 실행**: `config.json`의 전략을 로드하고, `condition.py`를 호출하여 현재 조건에 맞는 매매 행동을 결정합니다.
3.  **거래 실행**: `condition.py`가 반환한 매매 행동에 따라 `trade.py`를 통해 실제 주식 주문을 실행합니다.
"""

import logging
import time
import sys
import json
import datetime
import threading
import os

import core_logic
import condition
import trade
import state

# 이 스크립트(main_cmd.py)는 src 폴더 안에 있으므로, 상위 폴더가 프로젝트 루트가 됩니다.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# JSON 파일 및 로그 파일 경로를 프로젝트 루트 기준으로 설정
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'json', 'config.json')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'main_cmd.log')

thread_local = threading.local()

class CycleIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'cycle_id'):
            if hasattr(thread_local, 'cycle_id') and thread_local.cycle_id:
                record.cycle_id = thread_local.cycle_id
            else:
                record.cycle_id = 'Program'
        return True

class CustomFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, 'cycle_id') or not record.cycle_id:
            record.cycle_id = 'Program'
        return super().format(record)

def setup_logging():
    """로깅 설정을 초기화하고 파일 및 콘솔로 로그를 출력하도록 구성합니다."""
    # 로그 디렉토리가 없으면 생성
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger()
    # DEBUG 레벨로 설정하여 모든 레벨의 로그를 핸들러로 전달
    logger.setLevel(logging.DEBUG) 

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    logger.addFilter(CycleIdFilter())
    formatter = CustomFormatter('[%(cycle_id)s] %(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    # 파일 핸들러는 DEBUG 레벨부터 모든 로그를 기록
    file_handler.setLevel(logging.DEBUG)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    # 콘솔 핸들러는 INFO 레벨부터 중요한 정보만 표시
    stream_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

def _load_config():
    """config.json 파일을 로드합니다."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"심각: {CONFIG_FILE} 파일을 로드하거나 파싱하는 데 실패했습니다: {e}")
        return None

def main_loop():
    """자동매매 시스템의 메인 오케스트레이터 루프입니다."""
    while True:
        cycle_id = f"#{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        thread_local.cycle_id = cycle_id

        config = _load_config()
        if not config:
            logging.error("설정 파일을 로드할 수 없습니다. 60초 후 재시도합니다.")
            time.sleep(60)
            continue
        
        sleep_duration = config.get('loop_interval_seconds', 60)

        # 1. 매매 로직 실행 전, 대기 사이클인지 먼저 확인 (로그 생성 안함)
        if condition.is_wait_cycle(cycle_id, config):
            thread_local.cycle_id = None
            time.sleep(sleep_duration)
            continue # 대기 사이클이면 여기서 바로 다음 루프로 넘어감 (로그 생성 안됨)

        # 2. 대기 사이클이 아니면, 본격적인 로직과 로그 기록 시작
        logging.debug("새로운 사이클 시작...") # INFO -> DEBUG
        
        # 기본 조건 체크 (거래 시간 등)
        if not condition.check_basics():
            logging.info("기본 실행 조건(거래 시간 등)을 충족하지 않아 대기합니다.")
            thread_local.cycle_id = None
            time.sleep(sleep_duration)
            continue

        # 3. 매매 결정 (API 조회 포함)
        action_to_take, market_data = condition.find_action_to_take(cycle_id, config)

        # 4. 결정에 따른 거래 실행 및 상태 업데이트
        if action_to_take:
            action_type = action_to_take.get('type')
            
            if action_type in ['BUY', 'SELL']:
                logging.info("%s 결정 (전략: '%s')", action_type, action_to_take.get('strategy_name'))
                
                trade_successful = False
                trade_result = None

                # API 중복 호출 방지를 위해 조회해 둔 balance_df 전달
                balance_df = market_data.get('balance_df')

                if action_type == 'BUY':
                    trade_successful, trade_result = trade.order_buy(
                        cycle_id,
                        stock_code=action_to_take['stock_code'], 
                        quantity=action_to_take['quantity'], 
                        price=action_to_take.get('price', 0), 
                        market=action_to_take.get('market', "KRX"),
                        balance_df=balance_df
                    )
                elif action_type == 'SELL':
                    trade_successful, trade_result = trade.order_sell(
                        cycle_id,
                        stock_code=action_to_take['stock_code'],
                        quantity=action_to_take['quantity'],
                        price=action_to_take.get('price', 0),
                        market=action_to_take.get('market', "KRX"),
                        balance_df=balance_df
                    )

                # 5. 거래 성공 시 상태 업데이트
                if trade_successful:
                    current_state = state.load_trade_state()
                    if action_to_take.get('is_forced_trade'):
                        if action_type == 'BUY':
                            buy_price = action_to_take.get('price', 0)
                            if buy_price == 0: # 시장가 매수
                                buy_price = action_to_take.get('current_price', 0)
                            state.update_trade_state_after_buy(current_state, action_to_take['quantity'], buy_price)
                        
                        elif action_type == 'SELL':
                            if current_state.get('original_trade_type') == 'AUTO':
                                state.reset_state_for_auto_cycle(current_state)
                            else: # 단순 강제 매도
                                state.save_trade_state({'active': False}) # 거래 비활성화

        else:
            logging.debug("이번 사이클에서는 실행할 거래가 없습니다.") # INFO -> DEBUG

        logging.debug("새로운 사이클을 시작합니다. %s초 후 재시도합니다.\n", sleep_duration) # INFO -> DEBUG
        thread_local.cycle_id = None
        time.sleep(sleep_duration)

if __name__ == "__main__":
    setup_logging()
    
    try:
        thread_local.cycle_id = 'Program'
        logging.info("자동매매 프로그램을 시작합니다.")
        
        if core_logic.authenticate(cycle_id=None):
            config = _load_config()
            if not config:
                logging.error("초기 설정 파일을 로드할 수 없습니다. 프로그램을 종료합니다.")
                sys.exit(1)

            state.init_trade_state(config) # Call the new function once

            main_loop()
        else:
            logging.error("API 인증 실패. 프로그램을 종료합니다.")
            sys.exit(1)
    except KeyboardInterrupt:
        logging.info("사용자에 의해 프로그램이 중단되었습니다.")
    finally:
        logging.info("자동매매 프로그램을 종료합니다.")
        thread_local.cycle_id = None
        logging.shutdown()
