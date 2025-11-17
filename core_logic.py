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
from main_cmd import thread_local

# Add the specific library directories to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user', 'domestic_stock'))

import kis_auth as ka
from domestic_stock_functions import inquire_price, inquire_balance, search_stock_info, inquire_daily_itemchartprice

def suppress_external_logging():
    """Suppresses INFO/WARNING logs from external libraries."""
    logging.getLogger('kis_auth').setLevel(logging.CRITICAL)
    logging.getLogger('domestic_stock_functions').setLevel(logging.CRITICAL)

# --- State ---
_is_authenticated = False

def authenticate(cycle_id=None):
    """Authenticates with the KIS API based on the mode in config.json."""
    suppress_external_logging()
    global _is_authenticated
    if _is_authenticated:
        logging.info("Already authenticated.", extra={'cycle_id': cycle_id})
        return True

    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        trading_mode = config.get('trading_mode', 'real') # Default to 'real'
        svr_mode = "vps" if trading_mode == "paper" else "prod"
        
        logging.info("Authenticating in '%s' mode (svr=%s)...", trading_mode, svr_mode, extra={'cycle_id': cycle_id})
        
        ka.auth(svr=svr_mode) # Set environment based on config
        
        _is_authenticated = True
        logging.info("Authentication successful.", extra={'cycle_id': cycle_id})
        return True
    except Exception as e:
        logging.error("Authentication failed: %s", e, extra={'cycle_id': cycle_id})
        _is_authenticated = False
        return False

def get_price(cycle_id, stock_code: str):
    """Fetches the current price and stock info for a given stock code."""
    if not _is_authenticated:
        logging.error("Authentication required before fetching price.", extra={'cycle_id': cycle_id})
        return None

    try:
        logging.info("Fetching price for %s...", stock_code, extra={'cycle_id': cycle_id})
        thread_local.cycle_id = cycle_id # Set cycle_id for external logs
        df_price = inquire_price(env_dv="real", fid_cond_mrkt_div_code="J", fid_input_iscd=stock_code)
        thread_local.cycle_id = None # Clear after call
        
        logging.info("Fetching stock info for %s...", stock_code, extra={'cycle_id': cycle_id})
        thread_local.cycle_id = cycle_id # Set cycle_id for external logs
        df_info = search_stock_info(prdt_type_cd="300", pdno=stock_code)
        thread_local.cycle_id = None # Clear after call
        logging.info("Price and stock info data fetched successfully.", extra={'cycle_id': cycle_id})

        if df_price is not None and df_info is not None:
            # To avoid duplicate columns, drop columns from df_info that are already in df_price
            df_info_filtered = df_info.loc[:, ~df_info.columns.isin(df_price.columns)]
            # Concatenate the two dataframes horizontally
            combined_df = pd.concat([df_price, df_info_filtered], axis=1)
            return combined_df
        else:
            return df_price # Return at least the price if info fails

    except Exception as e:
        logging.error("Failed to fetch price or stock info: %s", e, extra={'cycle_id': cycle_id})
        return None

def get_balance(cycle_id):
    """Fetches the account balance, returning two DataFrames."""
    if not _is_authenticated:
        logging.error("Authentication required before fetching balance.", extra={'cycle_id': cycle_id})
        return None, None

    try:
        logging.info("Fetching account balance...", extra={'cycle_id': cycle_id})
        trenv = ka.getTREnv()
        thread_local.cycle_id = cycle_id # Set cycle_id for external logs
        df1, df2 = inquire_balance(
            env_dv="real",
            cano=trenv.my_acct, 
            acnt_prdt_cd=trenv.my_prod,
            afhr_flpr_yn="N",
            inqr_dvsn="02", # 종목별
            unpr_dvsn="01",
            fund_sttl_icld_yn="N",
            fncg_amt_auto_rdpt_yn="N",
            prcs_dvsn="00"
        )
        thread_local.cycle_id = None # Clear after call
        logging.info("Account balance data fetched successfully.", extra={'cycle_id': cycle_id})
        return df1, df2
    except Exception as e:
        logging.error("Failed to fetch account balance: %s", e, extra={'cycle_id': cycle_id})
        return None, None

def get_daily_history(cycle_id, stock_code: str, days: int):
    """Fetches the daily price history for a given stock code for a number of days."""
    if not _is_authenticated:
        logging.error("Authentication required before fetching history.", extra={'cycle_id': cycle_id})
        return None

    try:
        logging.info("Fetching daily history for %s for %d days...", stock_code, days, extra={'cycle_id': cycle_id})
        thread_local.cycle_id = cycle_id # Set cycle_id for external logs
        
        # KIS API 'inquire-daily-itemchartprice'는 최근 데이터를 기준으로 조회합니다.
        # 'D'는 일봉, 'W'는 주봉, 'M'은 월봉을 의미합니다.
        df_history = inquire_daily_itemchartprice(
            env_dv="real",
            fid_cond_mrkt_div_code="J",
            fid_input_iscd=stock_code,
            fid_period_div_code="D", # D: 일봉
            fid_org_adj_prc="1" # 1: 수정주가
        )
        
        thread_local.cycle_id = None # Clear after call
        
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