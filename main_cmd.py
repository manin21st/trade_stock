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
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Fatal: Failed to load or parse {CONFIG_FILE}: {e}")
        return None

# --- Strategy A: Logic ---
def should_sell(cycle_id, stock_code):
    """Checks all detailed sell conditions for Strategy A."""
    # For now, we only have placeholder sell conditions
    logging.info("[%s] Checking sell conditions...", stock_code, extra={'cycle_id': cycle_id})
    cond1 = condition.is_target_profit_reached(cycle_id, stock_code)
    cond2 = condition.is_stop_loss_reached(cycle_id, stock_code)
    # In a real scenario, you'd check if you actually own the stock
    return any([cond1, cond2])

def should_buy(cycle_id, stock_code):
    """Checks all detailed buy conditions for Strategy A."""
    logging.info("[%s] Checking buy conditions...", stock_code, extra={'cycle_id': cycle_id})
    cond1 = condition.is_trading_hours(cycle_id)
    cond2 = condition.is_price_below_target(cycle_id, stock_code)
    cond3 = condition.has_sufficient_cash(cycle_id)
    
    logging.info("[%s] Buy condition check: TradingHours(%s), PriceBelowTarget(%s), SufficientCash(%s)", stock_code, cond1, cond2, cond3, extra={'cycle_id': cycle_id})
    return all([cond1, cond2, cond3])

def decide_action(cycle_id, stock_code):
    """Decides and executes an action (buy/sell/hold) for a stock based on Strategy A."""
    # Selling has priority. If we own the stock, check if we should sell.
    if should_sell(cycle_id, stock_code):
        logging.info("[%s] Sell condition met. Executing sell order.", stock_code, extra={'cycle_id': cycle_id})
        trade.order_market_sell(cycle_id, stock_code, quantity=1) # Placeholder quantity
        return

    # If not selling, check if we should buy.
    if should_buy(cycle_id, stock_code):
        logging.info("[%s] Buy condition met. Executing buy order.", stock_code, extra={'cycle_id': cycle_id})
        trade.order_market_buy(cycle_id, stock_code, quantity=1) # Placeholder quantity
        return

    # If neither, hold.
    logging.info("[%s] No action taken. Holding.", stock_code, extra={'cycle_id': cycle_id})

# --- Main Execution Loop ---
def main_loop():
    """The main orchestrator loop."""
    while True:
        cycle_id = f"#{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        config = _load_config()
        if not config:
            logging.error("Could not load config, sleeping for 60 seconds.", extra={'cycle_id': cycle_id})
            time.sleep(60)
            continue

        strategy_config = config.get('strategy_A', {})
        target_stock = strategy_config.get('target_stock')
        sleep_duration = strategy_config.get('loop_interval_seconds', 300)

        if not target_stock:
            logging.error("Fatal: 'target_stock' not found in config. Sleeping for 60 seconds.", extra={'cycle_id': cycle_id})
            time.sleep(60)
            continue

        logging.info("------------------- New Cycle Start -------------------", extra={'cycle_id': cycle_id})
        
        # Log a single-line summary of the configured strategy
        summary_msg = (
            f"Strategy A Config: Stock={target_stock}, Interval={sleep_duration}s, "
            f"BuyPrice={strategy_config.get('buy_conditions', {}).get('target_price')}, "
            f"MinCash={strategy_config.get('buy_conditions', {}).get('min_cash_amount')}, "
            f"CheckHours={strategy_config.get('buy_conditions', {}).get('check_trading_hours')}, "
            f"SellProfit={strategy_config.get('sell_conditions', {}).get('target_profit_percent')}%, "
            f"StopLoss={strategy_config.get('sell_conditions', {}).get('stop_loss_percent')}%"
        )
        logging.info(summary_msg, extra={'cycle_id': cycle_id})
        
        thread_local.cycle_id = cycle_id
        decide_action(cycle_id, target_stock)
        thread_local.cycle_id = None
        
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
