# config.json 설정 가이드 (간결 버전)

이 파일은 `config.json`의 각 항목을 간단하게 설명합니다.

---

### [전체 설정]

- `trading_mode`: `paper`는 모의투자, `real`은 실전투자입니다. **주의해서 사용하세요.**
- `loop_interval_seconds`: 몇 초마다 한 번씩 매매 조건을 확인할지 정합니다. (예: `60`)

---

### [강제 매매: forced_trade]

이 설정은 **최우선으로 실행**되는 수동 명령입니다. `enabled`를 `true`로 바꾸면 즉시 실행되고, 실행된 후에는 자동으로 `false`로 돌아갑니다.

- `enabled`: `true`로 설정하면 이 기능을 켭니다.
- `trade_type`: `BUY` (사기) 또는 `SELL` (팔기).
- `stock_code`: 거래할 종목의 코드 (예: "005930").
- `quantity`: 거래할 주식 수.
- `price`: 지정할 가격. `0`이면 시장가로 바로 체결.
- `market`: 거래할 시장. `KRX`는 정규장, `NXT`는 시간외 거래.

**예시: 삼성전자 1주를 시간외 시장에서 시장가로 즉시 매수**
```json
"forced_trade": {
    "enabled": true,
    "trade_type": "BUY",
    "stock_code": "005930",
    "quantity": 1,
    "price": 0,
    "market": "NXT"
}
```

---

### [자동 매매 규칙: rules]

강제 매매가 꺼져있을 때, 여기에 설정된 규칙들을 위에서부터 순서대로 확인합니다. **조건이 맞는 첫 번째 규칙 하나만 실행**됩니다.

각 규칙은 **"만약 conditions(조건)이 모두 맞으면, strategy(전략)를 실행하라"** 는 뜻입니다.

#### 1. 조건 (conditions) - IF

규칙이 실행될지 말지를 결정하는 `IF` 문입니다.

- `is_trading_hours`: 정규장 시간(09:00~15:30)일 때만 `true`.
- `is_price_below_target`: 현재가가 정해둔 목표가보다 낮을 때 `true`.
- `has_sufficient_cash`: 계좌에 돈이 충분할 때 `true`.
- `is_target_profit_reached`: 가진 주식이 목표 수익률에 도달했을 때 `true`.
- `is_stop_loss_reached`: 가진 주식이 손절 라인에 도달했을 때 `true`.

#### 2. 전략 (strategy) - THEN

조건이 맞았을 때 실행할 `THEN` 행동입니다.

- `simple_buy`: 주식을 삽니다.
  - `order_amount_krw`: 정해진 금액만큼 삽니다. (수량은 알아서 계산됨)
  - `quantity`: 정해진 수량만큼 삽니다.
- `simple_sell`: 주식을 팝니다.
  - `sell_all: true`: 가진 주식을 전부 팝니다.
  - `quantity`: 정해진 수량만큼 팝니다.

**예시: 삼성전자를 8만원 밑으로 내려가면 10만원어치 매수하는 규칙**
```json
{
    "rule_name": "삼성전자 저점 매수",
    "conditions": [
        { "name": "is_price_below_target", "params": { "stock_code": "005930", "target_price": 80000 } }
    ],
    "strategy": {
        "name": "simple_buy",
        "params": {
            "stock_code": "005930",
            "order_amount_krw": 100000
        }
    }
}
```