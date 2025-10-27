# -*- coding: utf-8 -*-

"""
Core business logic for the KIS Trading Program.
This module handles API authentication and data fetching, independent of the GUI.
"""

import sys
import os
import logging
import pandas as pd

# Add the specific library directories to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user', 'domestic_stock'))

import kis_auth as ka
from domestic_stock_functions import inquire_price, inquire_balance, search_stock_info

# --- State ---
_is_authenticated = False

def authenticate():
    """Authenticates with the KIS API."""
    global _is_authenticated
    if _is_authenticated:
        logging.info("Already authenticated.")
        return True
    
    try:
        ka.auth() # This sets up the environment in the kis_auth module
        _is_authenticated = True
        logging.info("Authentication successful.")
        return True
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        _is_authenticated = False
        return False

def get_price(stock_code: str):
    """Fetches the current price and stock info for a given stock code."""
    if not _is_authenticated:
        logging.error("Authentication required before fetching price.")
        return None

    try:
        logging.info(f"Fetching price for {stock_code}...")
        df_price = inquire_price(env_dv="real", fid_cond_mrkt_div_code="J", fid_input_iscd=stock_code)
        
        logging.info(f"Fetching stock info for {stock_code}...")
        df_info = search_stock_info(prdt_type_cd="300", pdno=stock_code)

        if df_price is not None and df_info is not None:
            # To avoid duplicate columns, drop columns from df_info that are already in df_price
            df_info_filtered = df_info.loc[:, ~df_info.columns.isin(df_price.columns)]
            # Concatenate the two dataframes horizontally
            combined_df = pd.concat([df_price, df_info_filtered], axis=1)
            return combined_df
        else:
            return df_price # Return at least the price if info fails

    except Exception as e:
        logging.error(f"Failed to fetch price or stock info: {e}")
        return None

def get_balance():
    """Fetches the account balance, returning two DataFrames."""
    if not _is_authenticated:
        logging.error("Authentication required before fetching balance.")
        return None, None

    try:
        logging.info("Fetching account balance...")
        trenv = ka.getTREnv()
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
        logging.info("Account balance data fetched successfully.")
        return df1, df2
    except Exception as e:
        logging.error(f"Failed to fetch account balance: {e}")
        return None, None