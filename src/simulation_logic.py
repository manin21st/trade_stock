# -*- coding: utf-8 -*-
"""
simulation_logic.py - KIS API 시뮬레이션 모듈

이 모듈은 자동매매 프로그램의 시뮬레이션 모드에서 사용되는 가상(mock) API 함수들을 제공합니다.
실제 KIS API 대신 가상의 계좌 정보(`mock_account.json`)를 관리하고, 가상의 주식 시세 및
주문 처리를 시뮬레이션하여 실제 시장이 열리지 않은 시간에도 매매 로직을 테스트할 수 있게 합니다.

주요 기능:
1.  **가상 계좌 관리**: `mock_account.json` 파일을 통해 현금 잔고, 보유 주식, 평균 매수 단가 등
    가상의 계좌 상태를 로드하고 저장합니다.
2.  **가상 시세 제공**: `get_price` 함수를 통해 지정된 종목에 대한 가상의 현재가 데이터를 생성하여 반환합니다.
3.  **가상 잔고 조회**: `get_balance` 함수를 통해 `mock_account.json`의 정보를 기반으로
    가상의 계좌 잔고 및 보유 종목 DataFrame을 생성하여 반환합니다.
4.  **가상 주문 처리**: `create_order` 함수를 통해 매수/매도 주문을 시뮬레이션하고,
    `mock_account.json`의 가상 계좌 상태를 업데이트합니다.
"""

import logging
import json
import time
import random
import pandas as pd
import os

# Define constants for file paths relative to the project root
# SCRIPT_DIR is src/, so two levels up is project root.
_SCRIPT_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
MOCK_ACCOUNT_FILE_PATH = os.path.join(_PROJECT_ROOT, 'json', 'mock_account.json')

def load_account():
    """가상 계좌 정보(`mock_account.json`)를 로드합니다."""
    try:
        if os.path.exists(MOCK_ACCOUNT_FILE_PATH):
            with open(MOCK_ACCOUNT_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"cash": 10000000, "stocks": []} # 파일이 없으면 초기값 반환
    except Exception as e:
        logging.error(f"가상 계좌 로드 실패: {e}")
        return {"cash": 10000000, "stocks": []} # 오류 발생 시 기본값 반환

def save_account(account_data):
    """가상 계좌 정보를 `mock_account.json`에 저장합니다."""
    try:
        with open(MOCK_ACCOUNT_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(account_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"가상 계좌 저장 실패: {e}")

def get_price(cycle_id, stock_code: str):
    """가상의 주식 현재가 정보를 생성하여 DataFrame으로 반환합니다."""
    logging.info("[시뮬레이션] 가상 시세 조회: %s", stock_code, extra={'cycle_id': cycle_id})
    mock_account = load_account()
    
    base_price = 75000 # 기본 가격
    # 보유 종목이 있다면, 해당 종목의 매수단가를 기준으로 가격 변동을 시뮬레이션
    for stock in mock_account.get('stocks', []):
        if stock['stock_code'] == stock_code:
            # AUTO 모드 테스트를 위해 매수단가보다 높은 가격이 나올 확률을 높임
            base_price = stock['avg_buy_price'] * random.uniform(1.005, 1.03) 
            break
            
    # 현재가에 약간의 무작위 변동 추가
    price = base_price + random.randint(-100, 100) * 10
    
    price_data = {
        'stck_prpr': [str(int(price))],
        'prdy_vrss': [str(random.randint(-1000, 1000))],
        'prdy_vrss_sign': [str(random.choice(['1', '2', '3', '4', '5']))],
        'prdy_ctrt': [f"{random.uniform(-3, 3):.2f}"],
        'acml_vol': [str(random.randint(100000, 5000000))]
    }
    return pd.DataFrame(price_data)

def get_balance(cycle_id):
    """가상 계좌 정보를 기반으로 잔고 DataFrame들을 생성하여 반환합니다."""
    logging.info("[시뮬레이션] 가상 계좌 잔고 조회 중...", extra={'cycle_id': cycle_id})
    mock_account = load_account()
    if mock_account is None:
        return None, None
        
    # 보유 종목 DataFrame (df1) 생성
    holdings = []
    for stock in mock_account.get("stocks", []):
        # 가상 시세를 통해 현재 평가액 계산
        current_price = int(get_price(cycle_id, stock['stock_code'])['stck_prpr'].iloc[0]) 
        pchs_amt = stock['avg_buy_price'] * stock['quantity']
        evlu_amt = current_price * stock['quantity']
        evlu_pfls_amt = evlu_amt - pchs_amt
        evlu_pfls_rt = (evlu_pfls_amt / pchs_amt) * 100 if pchs_amt > 0 else 0
        
        holdings.append({
            'pdno': stock['stock_code'],
            'prdt_name': f'가상 {stock["stock_code"]}',
            'hldg_qty': stock['quantity'],
            'ord_psbl_qty': stock['quantity'], # 단순화를 위해 보유수량 = 주문가능수량
            'pchs_avg_pric': stock['avg_buy_price'],
            'pchs_amt': pchs_amt,
            'prpr': current_price,
            'evlu_amt': evlu_amt,
            'evlu_pfls_amt': evlu_pfls_amt,
            'prts_rate': evlu_pfls_rt # condition.py에서 사용하는 수익률 필드
        })
    df1 = pd.DataFrame(holdings)

    # 총 잔고 DataFrame (df2) 생성
    tot_evlu_amt = sum(h['evlu_amt'] for h in holdings)
    tot_pchs_amt = sum(h['pchs_amt'] for h in holdings)
    
    df2_data = {
        'dnca_tot_amt': [mock_account.get('cash', 0)], # 예수금 총금액
        'nxdy_excc_amt': [mock_account.get('cash', 0)], # D+2 예수금 (단순화를 위해 동일하게 설정)
        'tot_evlu_amt': [tot_evlu_amt], # 총 평가금액
        'nass_amt': [mock_account.get('cash', 0) + tot_evlu_amt], # 순자산금액
        'pchs_amt_smtl_amt': [tot_pchs_amt], # 매입금액 합계
        'evlu_pfls_smtl_amt': [tot_evlu_amt - tot_pchs_amt] # 평가손익 합계
    }
    df2 = pd.DataFrame(df2_data)
    
    return df1, df2

def create_order(cycle_id, trade_type, stock_code, quantity, price):
    """가상 주문을 처리하고 `mock_account.json` 상태를 업데이트합니다."""
    logging.info("[시뮬레이션] 가상 주문 처리 (유형: %s, 종목: %s, 수량: %s)", trade_type, stock_code, quantity, extra={'cycle_id': cycle_id})
    mock_account = load_account()
    
    current_price_df = get_price(cycle_id, stock_code) # 여기서 자체 get_price 호출
    current_price = int(current_price_df['stck_prpr'].iloc[0])
    trade_price = price if price > 0 else current_price
    trade_cost = trade_price * quantity

    if trade_type == 'BUY':
        if mock_account['cash'] < trade_cost:
            logging.error("[시뮬레이션] 현금 부족. 주문 실패.")
            return False, None
            
        mock_account['cash'] -= trade_cost
        
        # 보유 종목 업데이트
        found = False
        for stock in mock_account['stocks']:
            if stock['stock_code'] == stock_code:
                new_quantity = stock['quantity'] + quantity
                # 평균 매수 단가 재계산
                new_avg_price = (stock['avg_buy_price'] * stock['quantity'] + trade_cost) / new_quantity
                stock['quantity'] = new_quantity
                stock['avg_buy_price'] = new_avg_price
                found = True
                break
        if not found:
            mock_account['stocks'].append({
                "stock_code": stock_code,
                "quantity": quantity,
                "avg_buy_price": trade_price
            })
        
    elif trade_type == 'SELL':
        found = False
        for stock in mock_account['stocks']:
            if stock['stock_code'] == stock_code:
                if stock['quantity'] < quantity:
                    logging.error("[시뮬레이션] 보유 수량 부족. 주문 실패.")
                    return False, None
                
                stock['quantity'] -= quantity
                mock_account['cash'] += trade_cost
                found = True
                if stock['quantity'] == 0:
                    mock_account['stocks'].remove(stock)
                break
        if not found:
            logging.error("[시뮬레이션] 매도할 종목 없음. 주문 실패.")
            return False, None

    save_account(mock_account)
    
    # 성공 응답 DataFrame 생성
    res_df = pd.DataFrame([{"ODNO": f"mock-{int(time.time())}", "msg1": "가상 주문이 성공적으로 처리되었습니다."}])
    return True, res_df