# -*- coding: utf-8 -*-
"""
state.py - 애플리케이션 상태 관리 모듈

이 모듈은 `trade_state.json`과 같은 애플리케이션의 다양한 영속적인 상태(persistent state)들을
로드하고 저장하는 역할을 담당합니다. 이를 통해 프로그램 재시작 후에도 이전 상태를 유지하거나,
복잡한 거래 로직의 중간 단계를 저장할 수 있습니다.

주요 기능:
1.  **거래 상태 로드**: `trade_state.json` 파일에서 현재 거래의 상태를 로드합니다.
2.  **거래 상태 저장**: 현재 거래의 상태를 `trade_state.json` 파일에 저장합니다.
"""

import json
import os
import logging

# 이 스크립트(state.py)는 src 폴더 안에 있으므로, 상위 폴더가 프로젝트 루트가 됩니다.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# JSON 파일 경로를 프로젝트 루트 기준으로 설정
TRADE_STATE_FILE = os.path.join(PROJECT_ROOT, 'json', 'trade_state.json')

def load_trade_state():
    """`trade_state.json` 파일에서 현재 거래의 상태를 로드합니다."""
    try:
        if os.path.exists(TRADE_STATE_FILE):
            with open(TRADE_STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logging.debug(f"거래 상태 로드됨: {state}")
                return state
        return {'active': False} # 파일이 없으면 비활성 상태 반환
    except Exception as e:
        logging.error(f"거래 상태 로드 중 오류 발생: {e}")
        return {'active': False} # 오류 발생 시 비활성 상태 반환

def save_trade_state(state):
    """현재 거래의 상태를 `trade_state.json` 파일에 저장합니다."""
    try:
        with open(TRADE_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
        logging.debug(f"거래 상태 저장됨: {state}")
    except Exception as e:
        logging.error(f"거래 상태 저장 중 오류 발생: {e}")
