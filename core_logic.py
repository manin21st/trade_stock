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
            logging.error("Captured API output from %s: %s", api_func.__name__, captured_output.strip(), extra={'cycle_id': cycle_id})

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
    logging.info("Fetching price for %s (env_dv=%s)...", stock_code, _current_env_dv, extra={'cycle_id': cycle_id})
    
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
    logging.info("Price data fetched successfully. (Stock info disabled)", extra={'cycle_id': cycle_id})

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
        logging.info("Fetching account balance (env_dv=%s)...", _current_env_dv, extra={'cycle_id': cycle_id})
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

        logging.info("Account balance data fetched successfully.", extra={'cycle_id': cycle_id})
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
        logging.info("Fetching daily history for %s for %d days (env_dv=%s)...", stock_code, days, _current_env_dv, extra={'cycle_id': cycle_id})
        
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
            logging.info("Daily history data fetched successfully. Shape: %s", df_history.shape, extra={'cycle_id': cycle_id})
            return df_history
        else:
            logging.warning("No daily history data returned for %s.", stock_code, extra={'cycle_id': cycle_id})
            return None

    except Exception as e:
        logging.error("Failed to fetch daily history: %s", e, extra={'cycle_id': cycle_id})
        return None

def create_order(cycle_id, trade_type, stock_code, quantity, price, market="KRX"):
    """
    Creates a buy or sell order using the order_cash function.
    """
    global _is_authenticated, _current_env_dv
    if not _is_authenticated or _current_env_dv is None:
        logging.error("Authentication required and env_dv must be set before creating an order.", extra={'cycle_id': cycle_id})
        return False, None

    try:
        trenv = ka.getTREnv()
        
        ord_dv = 'buy' if trade_type == 'BUY' else 'sell'
        ord_dvsn = '02' if price == 0 else '01' # 01: 지정가, 02: 시장가
        
        # Get current price for logging purposes
        current_price_str = "N/A"
        try:
            # Call get_price directly, as it's already a wrapper for API calls
            price_df = get_price(cycle_id, stock_code)
            if price_df is not None and not price_df.empty:
                current_price_str = price_df['stck_prpr'].iloc[0]
        except Exception:
            logging.warning("Could not fetch current price for logging.", extra={'cycle_id': cycle_id})

        logging.info("Submitting %s order: Stock=%s, Qty=%s, Price=%s, Market=%s, CurrentPrice=%s", 
                     trade_type, stock_code, quantity, "Market" if price == 0 else price, market, current_price_str,
                     extra={'cycle_id': cycle_id})

        # Debug log for order_cash parameters
        order_params_log = {
            "env_dv": _current_env_dv,
            "ord_dv": ord_dv,
            "cano": trenv.my_acct,
            "acnt_prdt_cd": trenv.my_prod,
            "pdno": stock_code,
            "ord_dvsn": ord_dvsn,
            "ord_qty": str(quantity),
            "ord_unpr": str(price),
            "excg_id_dvsn_cd": market
        }
        logging.debug(f"Calling order_cash with parameters: {order_params_log}", extra={'cycle_id': cycle_id})

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
            do_smart_sleep=True # Smart sleep after the order call
        )
        
        if captured_err_output: # This means an exception occurred in _call_kis_api
            logging.error("Order submission failed due to API call error: %s", captured_err_output, extra={'cycle_id': cycle_id})
            return False, None

        # Check if the returned DataFrame is valid and contains data
        if res_df is not None and not res_df.empty:
            msg = res_df.get('msg1', [''])[0]
            # A successful order usually returns a non-empty msg1.
            if msg and ("정상" in msg or "처리완료" in msg or "주문" in msg):
                logging.info("Order submission response: %s", msg, extra={'cycle_id': cycle_id})
                logging.info("Order submitted successfully.", extra={'cycle_id': cycle_id})
                return True, res_df
            else:
                # Even if the df is not empty, if the message is not indicative of success, treat as failure.
                logging.error("Order submission failed. API Response: %s", res_df.to_dict('records'), extra={'cycle_id': cycle_id})
                return False, res_df
        else:
            # This path is taken if the API call itself fails and returns an empty DataFrame from the wrapper.
            logging.error("Order submission failed. No valid response data received from API.", extra={'cycle_id': cycle_id})
            return False, None

    except Exception as e:
        logging.error("Exception occurred while creating order: %s", e, extra={'cycle_id': cycle_id})
        return False, None