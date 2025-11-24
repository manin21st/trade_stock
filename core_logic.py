# -*- coding: utf-8 -*-

"""
Core business logic for the KIS Trading Program.
This module handles API authentication and data fetching, independent of the GUI.
"""

import sys
import os
import logging
import json
import pandas as pd
import io # Import io module
from main_cmd import thread_local

# Add the specific library directories to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user', 'domestic_stock'))

import kis_auth as ka
from domestic_stock_functions import inquire_price, inquire_balance, search_stock_info, inquire_daily_itemchartprice, order_cash

def suppress_external_logging():
    """Suppresses INFO/WARNING logs from external libraries."""
    logging.getLogger('kis_auth').setLevel(logging.CRITICAL)
    logging.getLogger('domestic_stock_functions').setLevel(logging.CRITICAL)

_is_authenticated = False
_current_env_dv = None

def authenticate(cycle_id=None):
    """Authenticates with the KIS API based on the mode in config.json."""
    suppress_external_logging()
    global _is_authenticated, _current_env_dv
    if _is_authenticated:
        logging.info("Already authenticated.", extra={'cycle_id': cycle_id})
        return True

    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        trading_mode = config.get('trading_mode', 'real') # Default to 'real'
        svr_mode = "vps" if trading_mode == "paper" else "prod"
        _current_env_dv = "demo" if trading_mode == "paper" else "real"
        
        logging.info("Authenticating in '%s' mode (svr=%s, env_dv=%s)...", trading_mode, svr_mode, _current_env_dv, extra={'cycle_id': cycle_id})
        
        ka.auth(svr=svr_mode) # Set environment based on config
        
        _is_authenticated = True
        # logging.info("Authentication successful.", extra={'cycle_id': cycle_id}) # Removed duplicate log
        return True
    except Exception as e:
        logging.error("Authentication failed: %s", e, extra={'cycle_id': cycle_id})
        _is_authenticated = False
        return False

def _call_kis_api(api_func, cycle_id, do_smart_sleep=True, **kwargs):
    """
    Generic wrapper for KIS API calls, handling authentication, logging, and rate limiting.
    Captures stdout for API functions that print errors directly.
    """
    global _is_authenticated, _current_env_dv
    if not _is_authenticated or _current_env_dv is None:
        logging.error("Authentication required and env_dv must be set before calling API.", extra={'cycle_id': cycle_id})
        return None, "Authentication required."

    # Set cycle_id for external logs
    old_thread_local_cycle_id = getattr(thread_local, 'cycle_id', None)
    thread_local.cycle_id = cycle_id

    # Redirect stdout to capture print statements (e.g., res.printError)
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output

    result = None
    error_message = None
    
    try:
        # Add env_dv if the API function expects it
        if 'env_dv' in api_func.__code__.co_varnames:
            kwargs['env_dv'] = _current_env_dv
        
        result = api_func(**kwargs)
        
        # Capture and log any output printed directly to stdout
        captured_output = redirected_output.getvalue()
        if captured_output:
            # We don't want to log this as ERROR unless it truly is an error
            # For now, just debug log it. The caller will decide if it's an error.
            logging.debug("Captured API output from %s: %s", api_func.__name__, captured_output.strip(), extra={'cycle_id': cycle_id})

    except Exception as e:
        error_message = f"Exception calling {api_func.__name__}: {e}"
        logging.error(error_message, extra={'cycle_id': cycle_id})
        result = None
    finally:
        sys.stdout = old_stdout # Restore stdout
        thread_local.cycle_id = old_thread_local_cycle_id # Restore previous cycle_id
        if do_smart_sleep:
            ka.smart_sleep()
            
    return result, error_message
def _call_kis_api(api_func, cycle_id, stock_code=None, do_smart_sleep=True, **kwargs):
    """
    Generic wrapper for KIS API calls, handling authentication, logging, and rate limiting.
    Captures stdout for API functions that print errors directly.
    """
    global _is_authenticated, _current_env_dv
    if not _is_authenticated or _current_env_dv is None:
        logging.error("Authentication required and env_dv must be set before calling API.", extra={'cycle_id': cycle_id})
        return None, "Authentication required."

    # Set cycle_id for external logs
    old_thread_local_cycle_id = getattr(thread_local, 'cycle_id', None)
    thread_local.cycle_id = cycle_id

    # Redirect stdout to capture print statements (e.g., res.printError)
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output

    result = None
    error_message = None
    
    try:
        # Add env_dv if the API function expects it
        if 'env_dv' in api_func.__code__.co_varnames:
            kwargs['env_dv'] = _current_env_dv
        
        result = api_func(**kwargs)
        
        # Capture and log any output printed directly to stdout
        captured_output = redirected_output.getvalue()
        if captured_output:
            logging.warning("API 호출 중 경고: %s (함수: %s)", captured_output.strip(), api_func.__name__, extra={'cycle_id': cycle_id})

    except Exception as e:
        error_message = f"Exception calling {api_func.__name__}: {e}"
        logging.error(error_message, extra={'cycle_id': cycle_id})
        result = None
    finally:
        sys.stdout = old_stdout # Restore stdout
        thread_local.cycle_id = old_thread_local_cycle_id # Restore previous cycle_id
        if do_smart_sleep:
            ka.smart_sleep()
            
    return result, error_message

def get_price(cycle_id, stock_code: str):
    """Fetches the current price and stock info for a given stock code."""
    logging.info("실시간 시세 조회: %s", stock_code, extra={'cycle_id': cycle_id})
    
    df_price, err_price = _call_kis_api(
        inquire_price,
        cycle_id,
        fid_cond_mrkt_div_code="J",
        fid_input_iscd=stock_code,
        do_smart_sleep=True # Always smart_sleep after price inquiry
    )
    if err_price:
        logging.error("Failed to inquire price: %s", err_price, extra={'cycle_id': cycle_id})
        return None
    if df_price is None or df_price.empty:
        logging.warning("No price data returned for %s.", stock_code, extra={'cycle_id': cycle_id})
        return None

    # logging.info("Fetching stock info for %s...", stock_code, extra={'cycle_id': cycle_id})
    # df_info, err_info = _call_kis_api(
    #     search_stock_info,
    #     cycle_id,
    #     prdt_type_cd="300", # TODO: Verify correct prdt_type_cd for all stocks.
    #     pdno=stock_code,
    #     do_smart_sleep=True # Always smart_sleep after stock info inquiry
    # )
    # if err_info:
    #     logging.error("Failed to search stock info: %s", err_info, extra={'cycle_id': cycle_id})
    #     return None
    df_info = pd.DataFrame() # Temporarily disable search_stock_info
    logging.info("시세 조회가 완료되었습니다.", extra={'cycle_id': cycle_id})

    if df_price is not None and df_info is not None:
        # To avoid duplicate columns, drop columns from df_info that are already in df_price
        # If df_info is empty, this step effectively does nothing.
        df_info_filtered = df_info.loc[:, ~df_info.columns.isin(df_price.columns)]
        # Concatenate the two dataframes horizontally
        combined_df = pd.concat([df_price, df_info_filtered], axis=1)
        return combined_df
    else:
        return df_price # Return at least the price if info fails

def get_balance(cycle_id):
    """Fetches the account balance, returning two DataFrames."""
    global _current_env_dv
    if not _is_authenticated or _current_env_dv is None:
        logging.error("Authentication required and env_dv must be set before fetching balance.", extra={'cycle_id': cycle_id})
        return None, None

    try:
        logging.info("계좌 잔고 조회 중...", extra={'cycle_id': cycle_id})
        trenv = ka.getTREnv()
        
        balance_data, err_msg = _call_kis_api(
            inquire_balance,
            cycle_id,
            cano=trenv.my_acct, 
            acnt_prdt_cd=trenv.my_prod,
            afhr_flpr_yn="N",
            inqr_dvsn="02", # 종목별
            unpr_dvsn="01",
            fund_sttl_icld_yn="N",
            fncg_amt_auto_rdpt_yn="N",
            prcs_dvsn="00"
        )
        if err_msg:
            logging.error("Failed to inquire balance: %s", err_msg, extra={'cycle_id': cycle_id})
            return None, None
        
        if balance_data is None:
            logging.error("Balance data is None.", extra={'cycle_id': cycle_id})
            return None, None

        # inquire_balance returns a tuple of DataFrames (df1, df2)
        # So balance_data will be (df1, df2)
        df1 = balance_data[0] if isinstance(balance_data, tuple) and len(balance_data) > 0 else pd.DataFrame()
        df2 = balance_data[1] if isinstance(balance_data, tuple) and len(balance_data) > 1 else pd.DataFrame()

        logging.info("계좌 잔고 조회가 완료되었습니다.", extra={'cycle_id': cycle_id})
        return df1, df2
    except Exception as e:
        logging.error("Failed to fetch account balance: %s", e, extra={'cycle_id': cycle_id})
        return None, None

def get_daily_history(cycle_id, stock_code: str, days: int):
    """Fetches the daily price history for a given stock code for a number of days."""
    global _current_env_dv
    if not _is_authenticated or _current_env_dv is None:
        logging.error("Authentication required and env_dv must be set before fetching history.", extra={'cycle_id': cycle_id})
        return None

    try:
        logging.info("일별 시세 내역 조회: %s (%d일)", stock_code, days, extra={'cycle_id': cycle_id})
        
        df_history, err_msg = _call_kis_api(
            inquire_daily_itemchartprice,
            cycle_id,
            fid_cond_mrkt_div_code="J",
            fid_input_iscd=stock_code,
            fid_period_div_code="D", # D: 일봉
            fid_org_adj_prc="1" # 1: 수정주가
        )
        if err_msg:
            logging.error("Failed to fetch daily history: %s", err_msg, extra={'cycle_id': cycle_id})
            return None
        
        if df_history is not None and not df_history.empty:
            # API는 요청한 기간보다 많은 데이터를 반환할 수 있으므로, 필요한 만큼만 잘라 사용합니다.
            df_history = df_history.tail(days).reset_index(drop=True)
            logging.info("일별 시세 내역 조회가 완료되었습니다.", extra={'cycle_id': cycle_id})
            return df_history
        else:
            logging.warning("No daily history data returned for %s.", stock_code, extra={'cycle_id': cycle_id})
            return None

    except Exception as e:
        logging.error("Failed to fetch daily history: %s", e, extra={'cycle_id': cycle_id})
        return None

def create_order(cycle_id, trade_type, stock_code, quantity, price, market="KRX"):
    """
    주문(현금) API를 사용하여 매수 또는 매도 주문을 생성하고 관련 정보를 로깅합니다.
    """
    global _is_authenticated, _current_env_dv
    if not _is_authenticated or _current_env_dv is None:
        logging.error("API 인증이 필요합니다.", extra={'cycle_id': cycle_id})
        return False, None

    try:
        # 1. Get and log current balance
        _, df_balance = get_balance(cycle_id)
        if df_balance is not None and not df_balance.empty:
            current_cash = int(df_balance['dnca_tot_amt'].iloc[0])
            logging.info(f"- 주문 전 현금 잔고: {current_cash:,}원", extra={'cycle_id': cycle_id})
        else:
            logging.warning("- 주문 전 잔고를 조회하지 못했습니다.", extra={'cycle_id': cycle_id})

        # 2. Prepare and log the order action
        trenv = ka.getTREnv()
        trade_type_kor = "매수" if trade_type == 'BUY' else "매도"
        price_kor = "시장가" if price == 0 else f"{price:,}원"
        logging.info(f"- KIS API로 {trade_type_kor} 주문 전송 (종목: {stock_code}, 수량: {quantity}, 가격: {price_kor})", extra={'cycle_id': cycle_id})
        
        ord_dv = 'buy' if trade_type == 'BUY' else 'sell'
        ord_dvsn = '01' if price == 0 else '00' # 00: 지정가, 01: 시장가

        # 3. Call the API
        res_df, captured_err_output = _call_kis_api(
            order_cash,
            cycle_id,
            ord_dv=ord_dv,
            cano=trenv.my_acct,
            acnt_prdt_cd=trenv.my_prod,
            pdno=stock_code,
            ord_dvsn=ord_dvsn,
            ord_qty=str(quantity),
            ord_unpr=str(price),
            excg_id_dvsn_cd=market,
            do_smart_sleep=True
        )
        
        if captured_err_output:
            logging.error("주문 API 호출 중 오류 발생: %s", captured_err_output, extra={'cycle_id': cycle_id})
            return False, None

        # 4. Process the result and log it
        if res_df is not None and not res_df.empty:
            if 'ODNO' in res_df.columns and res_df['ODNO'].iloc[0]:
                order_no = res_df['ODNO'].iloc[0]
                logging.info(f"- 주문 성공 (주문번호: {order_no})", extra={'cycle_id': cycle_id})
                # 체결가는 별도 조회가 필요하므로, 여기서는 체결 확인이 필요함을 로깅
                logging.info("- 체결 여부 및 체결가는 별도 조회를 통해 확인해야 합니다.", extra={'cycle_id': cycle_id})
                return True, res_df
            else:
                api_msg = res_df.get('msg1', pd.Series(['API 응답 메시지 없음']))[0]
                logging.error("주문 실패: %s", api_msg, extra={'cycle_id': cycle_id})
                return False, res_df
        else:
            logging.error("주문 실패: API로부터 유효한 응답을 받지 못했습니다.", extra={'cycle_id': cycle_id})
            return False, None

    except Exception as e:
        logging.error("주문 처리 중 예외 발생: %s", e, extra={'cycle_id': cycle_id})
        return False, None