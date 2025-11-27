# -*- coding: utf-8 -*-
"""
core_logic.py - KIS API 핵심 로직 및 데이터 처리

이 모듈은 한국투자증권(KIS) Open API와의 모든 통신 및 핵심 비즈니스 로직을 담당합니다.
'simulation_mode'가 비활성화된 경우 실제 API를 호출하며, `simulation_mode`가 활성화된 경우
`simulation_logic.py`에 정의된 가상 함수들을 호출하여 시뮬레이션을 수행합니다.
"""

import sys
import os
import logging
import json
import time
import pandas as pd
import io
from main_cmd import thread_local

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'open-trading-api', 'examples_user'))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'open-trading-api', 'examples_user', 'domestic_stock'))

import kis_auth as ka
from domestic_stock_functions import inquire_price, inquire_balance, inquire_daily_itemchartprice, order_cash

import simulation_logic as sl

# --- 전역 변수 및 상수 ---
_is_authenticated = False
_current_env_dv = None
CONFIG_FILE_PATH = 'json/config.json'

# --- 내부 헬퍼 함수 ---
def _load_config():
    """`config.json` 파일을 로드합니다."""
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    config_full_path = os.path.join(project_root, CONFIG_FILE_PATH)
    try:
        with open(config_full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"심각: {CONFIG_FILE_PATH} 파일을 로드하거나 파싱하는 데 실패했습니다: {e}")
        return {}

def suppress_external_logging():
    """외부 라이브러리에서 발생하는 로그를 억제합니다."""
    logging.getLogger('kis_auth').setLevel(logging.CRITICAL)
    logging.getLogger('domestic_stock_functions').setLevel(logging.CRITICAL)

# --- 실제 API 호출 래퍼 ---
def _call_kis_api(api_func, cycle_id, is_order=False, **kwargs):
    """KIS API 호출을 위한 범용 래퍼 함수입니다."""
    global _is_authenticated, _current_env_dv
    if not _is_authenticated or _current_env_dv is None:
        logging.error("API 호출 전 인증이 필요합니다.")
        return None, "인증 필요."

    old_thread_local_cycle_id = getattr(thread_local, 'cycle_id', None)
    thread_local.cycle_id = cycle_id

    result, error_message = None, None
    try:
        if 'env_dv' in api_func.__code__.co_varnames:
            kwargs['env_dv'] = _current_env_dv
        result = api_func(**kwargs)
    except Exception as e:
        error_message = f"API 함수({api_func.__name__}) 호출 중 예외 발생: {e}"
        logging.error(error_message)
        result = None
    finally:
        thread_local.cycle_id = old_thread_local_cycle_id
        # 사용자의 요청에 따라 API 호출 속도를 조절합니다.
        # 주문(order)의 경우 0.1초, 그 외(조회)는 0.3초 대기합니다.
        sleep_time = 0.1 if is_order else 0.3
        time.sleep(sleep_time)
        
    return result, error_message

# --- 공용 API 함수 ---
def authenticate(cycle_id=None):
    """API 인증을 수행합니다."""
    global _is_authenticated, _current_env_dv
    config = _load_config()
    if config.get("simulation_mode", False):
        logging.info("시뮬레이션 모드 활성화. API 인증을 건너뜁니다.")
        _is_authenticated = True
        return True
    
    suppress_external_logging()
    if _is_authenticated:
        logging.debug("이미 인증되었습니다.")
        return True

    try:
        trading_mode = config.get('trading_mode', 'real') 
        svr_mode = "vps" if trading_mode == "paper" else "prod"
        _current_env_dv = "demo" if trading_mode == "paper" else "real"
        logging.info("'%s' 모드 (svr=%s, env_dv=%s)로 인증 시도 중...", trading_mode, svr_mode, _current_env_dv)
        ka.auth(svr=svr_mode)
        _is_authenticated = True
        logging.info("API 인증 성공.")
        return True
    except Exception as e:
        logging.error("API 인증 실패: %s", e)
        _is_authenticated = False
        return False

def get_price(cycle_id, stock_code: str):
    """지정된 종목의 현재가 정보를 조회합니다."""
    config = _load_config()
    if config.get("simulation_mode", False):
        return sl.get_price(cycle_id, stock_code)

    logging.debug("실시간 시세 조회: %s", stock_code)
    df_price, err_price = _call_kis_api(inquire_price, cycle_id, fid_cond_mrkt_div_code="J", fid_input_iscd=stock_code)
    if err_price:
        logging.error("시세 조회 실패: %s", err_price)
        return None
    if df_price is None or df_price.empty:
        logging.warning("%s에 대한 시세 데이터가 반환되지 않았습니다.", stock_code)
        return None
    logging.debug("시세 조회가 완료되었습니다.")
    return df_price

def get_balance(cycle_id):
    """계좌 잔고를 조회합니다."""
    config = _load_config()
    if config.get("simulation_mode", False):
        return sl.get_balance(cycle_id)

    global _current_env_dv
    if not _is_authenticated or _current_env_dv is None:
        logging.error("잔고 조회 전 인증이 필요합니다.")
        return None, None

    try:
        logging.debug("계좌 잔고 조회 중...")
        trenv = ka.getTREnv()
        balance_data, err_msg = _call_kis_api(inquire_balance, cycle_id, cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod, afhr_flpr_yn="N", inqr_dvsn="02", unpr_dvsn="01", fund_sttl_icld_yn="N", fncg_amt_auto_rdpt_yn="N", prcs_dvsn="00")
        if err_msg:
            logging.error("잔고 조회 실패: %s", err_msg)
            return None, None
        if balance_data is None:
            logging.error("잔고 데이터가 None입니다.")
            return None, None
        df1 = balance_data[0] if isinstance(balance_data, tuple) and len(balance_data) > 0 else pd.DataFrame()
        df2 = balance_data[1] if isinstance(balance_data, tuple) and len(balance_data) > 1 else pd.DataFrame()
        logging.debug("계좌 잔고 조회가 완료되었습니다.")
        return df1, df2
    except Exception as e:
        logging.error("계좌 잔고 조회 중 예외 발생: %s", e)
        return None, None

def get_stock_balance(stock_code: str):
    """
    지정된 종목코드에 대한 보유 수량 및 평균 매입 단가를 조회합니다.
    (main_cmd.py의 _initialize_trade_state에서 cycle_id 없이 호출될 수 있으므로,
    cycle_id는 이 함수 내에서 새로 생성하거나 None으로 처리합니다.)
    """
    # get_stock_balance는 내부적으로 get_balance를 호출하며, 이 때 cycle_id가 필요합니다.
    # main_cmd.py의 _initialize_trade_state에서는 cycle_id가 아직 생성되지 않았을 수 있으므로,
    # 여기서는 임시 cycle_id를 사용하거나, 로그 시스템이 None을 처리하도록 합니다.
    # 현재 logging 설정은 'Program'을 기본 cycle_id로 사용하므로 None을 전달합니다.
    holdings_df, _ = get_balance(None) # cycle_id=None 전달

    if holdings_df is not None and not holdings_df.empty:
        # 'pdno' (상품번호, 종목코드) 컬럼으로 필터링
        stock_holding = holdings_df[holdings_df['pdno'] == stock_code]
        if not stock_holding.empty:
            quantity = int(stock_holding['hldg_qty'].iloc[0]) # 보유 수량
            avg_buy_price = float(stock_holding['pchs_avg_pric'].iloc[0]) # 평균 매입 단가
            total_buy_amount = float(stock_holding['pchs_amt'].iloc[0]) # 매입 금액
            
            return {
                "has_stock": True,
                "quantity": quantity,
                "avg_buy_price": avg_buy_price,
                "total_buy_amount": total_buy_amount
            }
    
    return {"has_stock": False, "quantity": 0, "avg_buy_price": 0.0, "total_buy_amount": 0.0}

def create_order(cycle_id, trade_type, stock_code, quantity, price, market="KRX"):
    """주문 API를 사용하여 매수 또는 매도 주문을 생성합니다."""
    config = _load_config()
    if config.get("simulation_mode", False):
        return sl.create_order(cycle_id, trade_type, stock_code, quantity, price)

    global _is_authenticated, _current_env_dv
    if not _is_authenticated or _current_env_dv is None:
        logging.error("주문 생성 전 API 인증이 필요합니다.")
        return False, None

    try:
        trenv = ka.getTREnv()
        ord_dv = 'buy' if trade_type == 'BUY' else 'sell'
        ord_dvsn = '01' if price == 0 else '00'
        res_df, err_msg = _call_kis_api(order_cash, cycle_id, is_order=True, ord_dv=ord_dv, cano=trenv.my_acct, acnt_prdt_cd=trenv.my_prod, pdno=stock_code, ord_dvsn=ord_dvsn, ord_qty=str(quantity), ord_unpr=str(price), excg_id_dvsn_cd=market)
        
        if err_msg:
            logging.error("주문 API 함수 호출 중 오류 발생: %s", err_msg)
            return False, None

        if res_df is not None and not res_df.empty:
            # API 응답의 rt_cd가 '0'이 아니면 실패로 간주
            if 'rt_cd' in res_df.columns and res_df['rt_cd'].iloc[0] != '0':
                api_msg = res_df.get('msg1', pd.Series(['API 응답 메시지 없음']))[0]
                msg_cd = res_df.get('msg_cd', pd.Series(['N/A']))[0]
                logging.error("주문 실패: %s (rt_cd: %s, msg_cd: %s)", api_msg, res_df['rt_cd'].iloc[0], msg_cd)
                return False, res_df
            
            # 성공 응답에서 주문번호(ODNO) 확인
            if 'ODNO' in res_df.columns and res_df['ODNO'].iloc[0]:
                order_no = res_df['ODNO'].iloc[0]
                logging.info("주문 요청 성공: %s %s %s주 (가격: %s, 주문번호: %s)", trade_type, stock_code, quantity, "시장가" if price == 0 else f"{price:,}원", order_no)
                logging.debug("체결 여부 및 체결가는 별도 조회를 통해 확인해야 합니다.")
                return True, res_df
            else:
                # rt_cd가 '0'이지만 주문번호가 없는 예외적인 경우
                logging.error("주문 실패: API가 성공을 반환했으나 주문번호를 찾을 수 없습니다.")
                return False, res_df
        else:
            logging.error("주문 실패: API로부터 유효한 응답을 받지 못했습니다.")
            return False, None
    except Exception as e:
        logging.error("주문 처리 중 예외 발생: %s", e)
        return False, None
		