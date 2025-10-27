import sys
import os
import logging
import pandas as pd

# --- Setup ---
# Add the specific library directories to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'open-trading-api', 'examples_user', 'domestic_stock'))

import kis_auth as ka
from domestic_stock_functions import inquire_balance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# --- Main Test ---

logging.info("Authenticating...")
ka.auth()

logging.info("Fetching account balance...")
try:
    df1, df2 = inquire_balance(
        env_dv="real",
        cano=ka.getTREnv().my_acct, 
        acnt_prdt_cd=ka.getTREnv().my_prod,
        afhr_flpr_yn="N",
        inqr_dvsn="02", # 01: 대출일별, 02: 종목별
        unpr_dvsn="01",
        fund_sttl_icld_yn="N",
        fncg_amt_auto_rdpt_yn="N",
        prcs_dvsn="00" # 00: 전일매매포함
    )

    logging.info("--- 보유 주식 (df1) Raw Data ---")
    print(df1)

    logging.info("--- 계좌 평가 (df2) Raw Data ---")
    print(df2)

except Exception as e:
    logging.error(f"An error occurred: {e}")
