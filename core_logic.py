# -*- coding: utf-8 -*-

"""
Core business logic for the KIS Trading Program.
This module handles API authentication and data fetching, independent of the GUI.
"""

import sys
import os
import logging
import pandas as pd
from main_cmd import thread_local

# Add the specific library directories to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user', 'domestic_stock'))

import kis_auth as ka
from domestic_stock_functions import inquire_price, inquire_balance, search_stock_info

def suppress_external_logging():
    """Suppresses INFO/WARNING logs from external libraries."""
    logging.getLogger('kis_auth').setLevel(logging.CRITICAL)
    logging.getLogger('domestic_stock_functions').setLevel(logging.CRITICAL)

# --- State ---
_is_authenticated = False

def authenticate(cycle_id=None):
    """Authenticates with the KIS API."""
    suppress_external_logging() # Suppress external logs early
    global _is_authenticated
    if _is_authenticated:
        logging.info("Already authenticated.", extra={'cycle_id': cycle_id})
        return True
    
    try:
        ka.auth() # This sets up the environment in the kis_auth module
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