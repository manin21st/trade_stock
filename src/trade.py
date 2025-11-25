# -*- coding: utf-8 -*-
"""
trade.py - 주식 거래 실행 모듈

이 모듈은 `main_cmd.py`로부터 매매 실행 요청을 받아, `core_logic.py`를 통해
실제 주식 매수/매도 주문을 실행하는 역할을 담당합니다.

주요 기능:
1.  **매수 주문**: `order_buy` 함수를 통해 지정된 종목, 수량, 가격으로 매수 주문을 전송합니다.
2.  **매도 주문**: `order_sell` 함수를 통해 지정된 종목, 수량, 가격으로 매도 주문을 전송합니다.
3.  **사전 정보 로깅**: 주문 실행 직전의 계좌 현황(예수금 등)을 로그로 남겨 거래 전후 상황 파악을 용이하게 합니다.
"""

import logging
import core_logic

def _get_pre_trade_info(cycle_id):
    """거래 실행 전 예수금 정보를 조회하여 문자열로 반환합니다."""
    _, df_balance = core_logic.get_balance(cycle_id)
    if df_balance is not None and not df_balance.empty:
        cash = int(df_balance['dnca_tot_amt'].iloc[0])
        return f"(주문 전 예수금: {cash:,}원)"
    return "(주문 전 예수금 조회 실패)"

def order_buy(cycle_id, stock_code, quantity, price=0, market="KRX"):
    """
    1. 매수 주문: 지정된 종목, 수량, 가격으로 매수 주문을 실행합니다.
    실제 주문은 `core_logic.create_order` 함수를 통해 KIS API로 전송됩니다.
    """
    pre_trade_info = _get_pre_trade_info(cycle_id)
    price_info = "시장가" if price == 0 else f"{price:,}원"
    logging.info("매수 주문 요청: %s %s주 (가격: %s) %s", stock_code, quantity, price_info, pre_trade_info)
    
    success, result = core_logic.create_order(
        cycle_id=cycle_id,
        trade_type='BUY',
        stock_code=stock_code,
        quantity=quantity,
        price=price,
        market=market
    )
    # create_order 내부에서 성공/실패 로깅이 이미 수행되므로 여기서는 추가 로깅 불필요.
    return success

def order_sell(cycle_id, stock_code, quantity, price=0, market="KRX"):
    """
    2. 매도 주문: 지정된 종목, 수량, 가격으로 매도 주문을 실행합니다.
    실제 주문은 `core_logic.create_order` 함수를 통해 KIS API로 전송됩니다.
    """
    pre_trade_info = _get_pre_trade_info(cycle_id)
    price_info = "시장가" if price == 0 else f"{price:,}원"
    logging.info("매도 주문 요청: %s %s주 (가격: %s) %s", stock_code, quantity, price_info, pre_trade_info)

    success, result = core_logic.create_order(
        cycle_id=cycle_id,
        trade_type='SELL',
        stock_code=stock_code,
        quantity=quantity,
        price=price,
        market=market
    )
    # create_order 내부에서 성공/실패 로깅이 이미 수행되므로 여기서는 추가 로깅 불필요.
    return success