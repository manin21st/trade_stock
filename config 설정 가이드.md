# config.json 설정 가이드

이 파일은 `config.json`의 각 항목을 상세하게 설명하여, 자동매매 엔진의 동작을 정확하게 제어할 수 있도록 돕습니다.

---

## 1. 전역 설정 (Global Settings)

프로그램 전체의 동작을 제어하는 최상위 설정입니다.

- `simulation_mode`
  - `true`: 실제 API를 호출하지 않고 `simulation_logic.py`의 가상 함수를 사용하여 매매 과정을 시뮬레이션합니다.
  - `false`: 실제 KIS API 서버와 통신하여 실전 또는 모의투자를 진행합니다.

- `trading_mode`
  - `"paper"`: 모의투자 계좌를 사용합니다.
  - `"real"`: 실전투자 계좌를 사용합니다. **금전적 손실이 발생할 수 있으니 매우 주의해야 합니다.**

- `loop_interval_seconds`
  - 매매 조건 확인 사이클의 간격(초)입니다. 예를 들어 `10`으로 설정하면, 10초마다 한 번씩 `rules`를 평가합니다. KIS API는 초당 요청 횟수 제한이 있으므로 너무 짧게 설정하지 않는 것이 좋습니다.

---

## 2. 강제 매매 (Forced Trade)

이 설정은 **모든 `rules`보다 우선하여 즉시 실행**되는 일회성 명령입니다. GUI의 '강제 실행' 버튼과 연동됩니다.

- `enabled`
  - `true`로 설정하면 엔진이 이 명령을 즉시 실행합니다. 실행 후에는 자동으로 `false`로 변경됩니다.

- `trade_type`
  - `"BUY"`: 강제 매수
  - `"SELL"`: 강제 매도
  - `"AUTO"`: 자동 매수/매도 사이클. 아래 'AUTO 모드 상세' 참고.

- `stock_code`: 거래할 종목의 코드 (예: `"005930"`)

- `price`: 지정가. `0`으로 설정하면 시장가로 주문합니다.

- `market`: 거래 시장. `"KRX"` (정규장)가 기본값입니다.

- `division_count`: 분할 매매 횟수. `1`이면 한 번에 전량 주문, `3`이면 3회에 걸쳐 분할 주문합니다.

### 강제 매매 유형별 파라미터

#### A) `BUY` 또는 `SELL` (단순 강제 매매)

- `quantity`: 매매할 주식 수.
- `amount`: 매매할 총액 (원). `quantity`와 `amount` 중 하나만 사용합니다. `amount`를 지정하면 현재가 기준으로 수량이 자동 계산됩니다.

**예시: 삼성전자 10주를 시장가로 즉시 매수**
```json
"forced_trade": {
    "enabled": true,
    "trade_type": "BUY",
    "stock_code": "005930",
    "quantity": 10,
    "price": 0,
    "market": "KRX",
    "division_count": 1 
}
```

#### B) `AUTO` (자동 순환 매매)

매수와 매도를 자동으로 반복하는 사이클입니다. `BUYING` -> `SELLING` -> `BUYING`...

- `quantity` 또는 `amount`: **매수 단계의 총 목표 수량/금액**을 설정합니다.
- `sell_profit_target_percent`: **목표 수익률(%)**. 매수 평균 단가 대비 이 수익률에 도달하면 전량 매도합니다. (예: `5.0`은 5% 수익)

**`AUTO` 모드 핵심 로직:**
1.  **시작**: `BUYING` 단계로 시작하며, **이미 보유 중인 수량을 자동으로 인식**합니다.
2.  **매수**: (목표 수량 - 기존 보유 수량) 만큼만 추가로 분할 매수합니다.
3.  **매도 전환**: 매수가 완료되면 `SELLING` 단계로 전환됩니다.
4.  **매도**: 보유한 전체 수량의 평균 단가 대비 수익률이 `sell_profit_target_percent`에 도달하면 **전량 시장가 매도**합니다.
5.  **종료**: 매도가 완료되면 강제 매매 상태가 종료됩니다.

**예시: 삼성전자 총 50주를 확보하고, 평균 단가 대비 5% 수익에서 전량 매도 (2회 분할 매수)**
- 만약 이미 20주를 보유 중이라면, 30주만 추가로 2회에 걸쳐 분할 매수 (회당 15주)하고, 총 50주에 대해 5% 수익 시 매도합니다.
```json
"forced_trade": {
    "enabled": true,
    "trade_type": "AUTO",
    "stock_code": "005930",
    "quantity": 50,
    "price": 0,
    "market": "KRX",
    "division_count": 2,
    "sell_profit_target_percent": 5.0
}
```

---

## 3. 규칙 기반 자동 매매 (Rules)

강제 매매가 비활성화(`enabled: false`)되어 있을 때, `loop_interval_seconds` 간격마다 아래 `rules` 목록을 위에서부터 순서대로 평가합니다. **조건을 충족하는 첫 번째 규칙 하나만 실행**하고 해당 사이클을 마칩니다.

각 규칙은 **"만약 `conditions`(조건)이 모두 참(AND)이면, `strategy`(전략)를 실행하라"**는 구조입니다.

### 세부 항목

#### A) `conditions` (조건 목록 - IF)

- `name`: 실행할 조건 함수의 이름. 아래 목록 참조.
- `params`: 해당 조건 함수에 전달할 파라미터.

**사용 가능한 조건 함수:**
- `is_trading_hours`: 정규장 시간(09:00~15:30)인지 확인.
  - `check_enabled: true`일 때만 작동.
- `is_price_below_target`: 현재가가 지정한 목표가보다 낮은지 확인.
  - `stock_code`, `target_price` 필요.
- `has_sufficient_cash`: 계좌에 최소 현금이 있는지 확인.
  - `min_cash_amount` 필요.
- `is_target_profit_reached`: 보유 종목이 목표 수익률에 도달했는지 확인.
  - `stock_code`, `target_profit_percent` 필요.
- `is_stop_loss_reached`: 보유 종목이 손절매 손실률에 도달했는지 확인.
  - `stock_code`, `stop_loss_percent` 필요. (예: -3.0은 -3% 손실)

#### B) `strategy` (전략 - THEN)

- `name`: 실행할 전략 함수의 이름. 아래 목록 참조.
- `params`: 해당 전략 함수에 전달할 파라미터.

**사용 가능한 전략 함수:**
- `simple_buy`: 주식 매수.
  - `stock_code`, `market` 필요.
  - `amount`: 지정된 금액만큼 시장가로 매수. 수량은 자동 계산.
  - `quantity`: 지정된 수량만큼 매수.
- `simple_sell`: 주식 매도.
  - `stock_code`, `market` 필요.
  - `sell_all: true`: 해당 종목 보유 수량 전량 매도.
  - `quantity`: 지정된 수량만큼 매도.

**규칙 예시: 삼성전자가 8만원 아래이고, 계좌에 10만원 이상 있으면 5만원어치 시장가 매수**
```json
{
    "rule_name": "삼성전자 저점 분할 매수",
    "conditions": [
        {
            "name": "is_price_below_target",
            "params": { "stock_code": "005930", "target_price": 80000 }
        },
        {
            "name": "has_sufficient_cash",
            "params": { "min_cash_amount": 100000 }
        }
    ],
    "strategy": {
        "name": "simple_buy",
        "params": {
            "stock_code": "005930",
            "amount": 50000,
            "market": "KRX"
        }
    }
}
```
