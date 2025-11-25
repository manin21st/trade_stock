# -*- coding: utf-8 -*-
"""
strategy.py - 구체적인 매매 전략 라이브러리

이 모듈은 `condition.py`의 조건 평가 결과에 따라 실제로 수행될 구체적인
매매 행동(전략)들을 함수 형태로 정의하는 라이브러리입니다.
예를 들어, '얼마나 많은 수량을 살 것인가' 또는 '전량 매도할 것인가'와 같은
세부적인 거래 로직을 구현합니다.
"""

import logging
import core_logic

def simple_buy(cycle_id, params, price_df, **kwargs):
    """
    1. 단순 매수 전략: 제공된 파라미터를 기반으로 간단한 매수 전략을 실행합니다.
    `main_cmd.py`가 처리할 매수 행동 딕셔너리를 반환합니다.
    """
    stock_code = params.get('stock_code')
    amount = params.get('amount')
    quantity = params.get('quantity')
    price = params.get('price', 0)
    market = params.get('market', "KRX")

    if not stock_code:
        logging.error("simple_buy 전략: 파라미터에 'stock_code'가 누락되었습니다.")
        return None

    if amount and not quantity:
        if price_df is None or price_df.empty:
            logging.error("simple_buy 전략: 수량 계산을 위한 현재가 데이터가 없습니다.")
            return None
        current_price = int(price_df['stck_prpr'].iloc[0])
        
        if current_price > 0:
            quantity = amount // current_price
            if quantity == 0:
                logging.warning("simple_buy 전략: 주문 금액 %s원으로는 %s 주식 1주도 살 수 없습니다 (현재가 %s원).", amount, stock_code, current_price)
                return None
            logging.debug("simple_buy 전략: %s원 기준 %s주 매수 수량 %s 계산됨.", current_price, stock_code, quantity)
        else:
            logging.error("simple_buy 전략: %s의 현재가가 0이므로 수량을 계산할 수 없습니다.", stock_code)
            return None

    elif not quantity:
        logging.error("simple_buy 전략: 'amount' 또는 'quantity' 중 하나는 제공되어야 합니다.")
        return None
    
    return {
        'type': 'BUY',
        'stock_code': stock_code,
        'quantity': quantity,
        'price': price,
        'market': market,
        'strategy_name': 'simple_buy'
    }

def simple_sell(cycle_id, params, holdings_df, **kwargs):
    """
    2. 단순 매도 전략: 제공된 파라미터를 기반으로 간단한 매도 전략을 실행합니다.
    `main_cmd.py`가 처리할 매도 행동 딕셔너리를 반환합니다.
    """
    stock_code = params.get('stock_code')
    sell_all = params.get('sell_all', False)
    quantity = params.get('quantity')
    price = params.get('price', 0)
    market = params.get('market', "KRX")

    if not stock_code:
        logging.error("simple_sell 전략: 파라미터에 'stock_code'가 누락되었습니다.")
        return None

    if sell_all:
        held_qty = 0
        if holdings_df is not None and not holdings_df.empty and 'pdno' in holdings_df.columns:
            holding = holdings_df[holdings_df['pdno'] == stock_code]
            if not holding.empty:
                held_qty = int(holding['hldg_qty'].iloc[0])

        if held_qty > 0:
            quantity = held_qty
            logging.info("simple_sell 전략: 'sell_all'이 참이므로, 보유 수량 %s주 전체를 매도합니다.", quantity)
        else:
            logging.warning("simple_sell 전략: 'sell_all'이 참이지만 %s에 대한 보유 종목이 없습니다.", stock_code)
            return None
            
    elif not quantity or quantity <= 0:
        logging.error("simple_sell 전략: 'sell_all'이 참이거나 유효한 'quantity'가 제공되어야 합니다.")
        return None

    return {
        'type': 'SELL',
        'stock_code': stock_code,
        'quantity': quantity,
        'price': price,
        'market': market,
        'strategy_name': 'simple_sell'
    }
