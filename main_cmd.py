# -*- coding: utf-8 -*-

"""
클라우드 서버 환경에서 자동매매를 수행하는 메인 프로그램입니다.

[리눅스 서버 실행 가이드]
1. 백그라운드 실행:
   - 터미널을 종료해도 프로그램이 계속 실행되게 하려면 아래 명령어를 사용하세요.
     $ nohup python -u main_cmd.py > main_cmd.log 2>&1 &
   - '-u' 옵션은 버퍼링 없이 로그를 즉시 파일에 쓰도록 보장합니다.
   - 모든 로그(표준 출력 및 오류)는 'main_cmd.log' 파일에 저장됩니다.

2. 프로세스 상태 확인:
   - 프로그램이 현재 실행 중인지 확인하려면 아래 명령어를 사용하세요.
     $ ps -ef | grep main_cmd.py

3. 실시간 로그 확인:
   - 생성되는 로그를 실시간으로 보려면 아래 명령어를 사용하세요.
     $ tail -f main_cmd.log

4. 프로세스 종료:
   - 먼저 'ps' 명령어로 프로세스 ID(PID)를 찾습니다.
   - 찾은 PID를 사용하여 아래 명령어로 프로세스를 종료합니다.
     $ kill [PID]
"""

import logging
import time
import sys
import json
import datetime
import threading

import core_logic
import condition
import trade

CONFIG_FILE = 'config.json'
LOG_FILE = 'main_cmd.log'

thread_local = threading.local()

class CycleIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'cycle_id'):
            if hasattr(thread_local, 'cycle_id') and thread_local.cycle_id:
                record.cycle_id = thread_local.cycle_id
            else:
                record.cycle_id = 'Program' # Default for logs without a specific cycle_id
        return True

class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Provide a default value for cycle_id if it's not set or is None/empty
        if not hasattr(record, 'cycle_id') or record.cycle_id is None or record.cycle_id == '':
            record.cycle_id = 'Program'
        return super().format(record)

def setup_logging():
    """Sets up logging to file and console in a robust way."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove any existing handlers to ensure a clean setup
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    # Add the custom filter to ensure all records have a cycle_id
    logger.addFilter(CycleIdFilter())

    # Create new handlers
    formatter = CustomFormatter('[%(cycle_id)s] %(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a') # Use 'a' to append
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # Add new handlers to the root logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

def _load_config():
    """Loads the shared configuration file."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f: # Added encoding for safety
            return json.load(f)
    except Exception as e:
        logging.error(f"Fatal: Failed to load or parse {CONFIG_FILE}: {e}")
        return None

def _save_config(config_data):
    """Saves the configuration file."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Fatal: Failed to save {CONFIG_FILE}: {e}")

# --- Main Execution Loop ---
def main_loop():
    """The main orchestrator loop."""
    while True:
        cycle_id = f"#{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        thread_local.cycle_id = cycle_id

        config = _load_config()
        if not config:
            logging.error("Could not load config, sleeping for 60 seconds.", extra={'cycle_id': cycle_id})
            time.sleep(60)
            continue
        
        sleep_duration = config.get('loop_interval_seconds', 60)

        # Let the condition module decide what to do
        action_to_take = condition.find_action_to_take(cycle_id, config)

        if action_to_take:
            action_type = action_to_take.get('type')
            stock_code = action_to_take.get('stock_code')
            strategy_name = action_to_take.get('strategy_name')
            trade_successful = False

            if action_type == 'BUY':
                quantity = action_to_take.get('quantity')
                price = action_to_take.get('price', 0)
                market = action_to_take.get('market', "KRX") # Get market from action
                logging.info("[%s] 매수 결정 (전략: '%s')", stock_code, strategy_name, extra={'cycle_id': cycle_id})
                trade_successful = trade.order_buy(cycle_id, stock_code, quantity=quantity, price=price, market=market) # Pass market

            elif action_type == 'SELL':
                quantity = action_to_take.get('quantity')
                price = action_to_take.get('price', 0)
                market = action_to_take.get('market', "KRX") # Get market from action
                logging.info("[%s] 매도 결정 (전략: '%s')", stock_code, strategy_name, extra={'cycle_id': cycle_id})
                trade_successful = trade.order_sell(cycle_id, stock_code, quantity=quantity, price=price, market=market) # Pass market
            
            if trade_successful:
                logging.info("최종 거래 결과: 성공", extra={'cycle_id': cycle_id})
            else:
                logging.error("최종 거래 결과: 실패", extra={'cycle_id': cycle_id})

            # The 'is_forced_trade' flag is now only for logging/distinction purposes
            # The program will no longer automatically disable it.
            # The user must manually set "enabled": false in config.json to stop it.
            if action_to_take.get('is_forced_trade', False):
                logging.info("강제 거래 명령이 처리되었습니다.", extra={'cycle_id': cycle_id})
        else:
            logging.info("이번 사이클에서는 거래 행동이 없습니다.", extra={'cycle_id': cycle_id})

        thread_local.cycle_id = None
        logging.info("", extra={'cycle_id': cycle_id})
        logging.info("", extra={'cycle_id': cycle_id})
        time.sleep(sleep_duration)

if __name__ == "__main__":
    setup_logging()
    
    try:
        thread_local.cycle_id = 'Program'
        logging.info("Authenticating with API...")
        if core_logic.authenticate(cycle_id=None):
            logging.info("Authentication successful.")
            thread_local.cycle_id = None # Clear after successful auth
            main_loop()
        else:
            logging.error("Authentication failed. Exiting program.")
            sys.exit(1)
    finally:
        logging.info("Shutting down logging.")
        thread_local.cycle_id = None # Ensure it's cleared on shutdown
        logging.shutdown() # Ensure logs are flushed on exit
