---
status: complete
phase: 02-player-property-rules
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md]
started: 2026-04-03T00:00:00Z
updated: 2026-04-03T00:00:00Z
---

## Current Test

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Chạy `python main.py --headless` từ đầu (không có state cũ). Game khởi động không có exception, chạy đến khi kết thúc (bankruptcy hoặc max_turns), in ra kết quả.
result: pass

### 2. Starting Cash Đúng
expected: Mỗi player bắt đầu ván với đúng 1,000,000 cash (không phải 200 hay giá trị cũ). Log hoặc output hiển thị cash ban đầu của từng player là 1,000,000.
result: pass

### 3. Auto-buy Đất Chưa Có Chủ
expected: Khi player dừng ở ô CITY chưa có chủ và đủ tiền → tự động mua. Cash của player giảm đúng giá (build_level1 × 1000), property được gán cho player đó. Không cần hỏi xác nhận.
result: pass

### 4. Rent Transfer Khi Dừng Đất Đối Thủ
expected: Khi player A dừng ở ô CITY của player B → A mất tiền toll (đúng level hiện tại × 1000), B nhận được đúng số tiền đó. Hai chiều cash flow đều đúng.
result: pass

### 5. Tax Space Tính 10% Invested
expected: Khi player dừng ô TAX → bị trừ đúng 10% tổng giá trị đã đầu tư vào các property đang sở hữu (tổng build cost của các level đã build, × BASE_UNIT). Không phải 10% cash.
result: blocked
blocked_by: other
reason: "Log không in chi tiết cách tính tax — không thể verify số tiền đúng hay chưa"

### 6. Start Bonus 150,000
expected: Khi player đi qua hoặc dừng ô START → nhận đúng 150,000 (= 15% × 1,000,000 starting_cash). Không phải % cash hiện tại, là fixed 150k.
result: pass

### 7. Forced Acquisition (Mua Đất Đối Thủ)
expected: Khi player A dừng ô CITY của B (đã qua toll) → A có thể mua với giá acquisition (build_level1 × 1000 × acquireRate). Ownership chuyển sang A, B nhận tiền, A mất tiền đúng giá.
result: pass

### 8. Upgrade Property
expected: Sau mỗi turn, player tự động upgrade các CITY property mình sở hữu nếu đủ tiền và chưa max level 5. Cash của player giảm đúng build cost của level tiếp theo.
result: pass

### 9. MiniGame Red/Black
expected: Khi player dừng ô GAME → chơi MiniGame. Stub AI: đặt cược min (50,000), round 1. Thắng → nhận 50,000 × 2 = 100,000 net. Thua → mất 50,000. Kết quả được emit qua event MINIGAME_RESULT.
result: issue
reported: "[MiniGame] B: 100000, cuoc $50,000, nhan lai $0 — nhan lai luôn là $0, có thể payout không được tính đúng khi thắng"
severity: major

### 10. Bankruptcy Resolution — Bán Property Trả Nợ
expected: Khi player không đủ tiền trả toll/tax → tự động bán property rẻ nhất trước (50% giá đầu tư). Bán từng cái cho đến khi đủ tiền hoặc hết property → khai phá sản. Player bị loại khỏi game.
result: issue
reported: "A nợ $160,000, bán đủ sau o 16 ($305,500 collected) nhưng vẫn tiếp tục bán o 28, 23, 32 — không dừng khi đã đủ tiền trả nợ"
severity: major

### 11. FSM 7 Phases Per Turn
expected: Mỗi turn chạy đúng 7 giai đoạn: ROLL → MOVE → RESOLVE_TILE → ACQUIRE → UPGRADE → CHECK_BANKRUPTCY → END_TURN. Không bỏ phase nào, không lặp phase nào.
result: skipped
reason: Sẽ kiểm tra khi có UI (Phase 4)

## Summary

total: 11
passed: 7
issues: 2
pending: 0
skipped: 1
blocked: 1

## Gaps

- truth: "MiniGame thắng → nhận net 50,000 (bet × 2); thua → mất 50,000. nhan lai phản ánh đúng kết quả."
  status: failed
  reason: "User reported: [MiniGame] B: 100000, cuoc $50,000, nhan lai $0 — nhan lai luôn là $0, có thể payout không được tính đúng khi thắng"
  severity: major
  test: 9
  root_cause: "main.py:250 đọc event.data.get('gain', 0) nhưng game.py emit key là 'result' → gain luôn = 0. Game logic đúng, chỉ log sai key."
  artifacts:
    - path: "main.py"
      issue: "line 250: event.data.get('gain', 0) nên là event.data.get('result', 0)"
  missing:
    - "Sửa key từ 'gain' → 'result' trong log_event MINIGAME_RESULT handler"
  debug_session: ""

- truth: "Bankruptcy: bán property rẻ nhất trước, dừng ngay khi cash đủ cover debt, không bán thêm."
  status: failed
  reason: "User reported: A nợ $160,000, bán đủ sau o 16 ($305,500 collected) nhưng vẫn tiếp tục bán o 28, 23, 32 — không dừng khi đã đủ tiền trả nợ"
  severity: major
  test: 10
  root_cause: "bankruptcy.py:32 dùng 'while player.owned_properties:' cho creditor path → bán HẾT property. Phải là 'while player.cash < 0 and player.owned_properties:' và không mark bankrupt nếu cash >= 0 sau khi bán đủ."
  artifacts:
    - path: "ctp/controller/bankruptcy.py"
      issue: "line 32: 'while player.owned_properties:' phải là 'while player.cash < 0 and player.owned_properties:'; thêm điều kiện không mark bankrupt nếu cash đã đủ"
  missing:
    - "Sửa creditor path: chỉ bán đủ để cover debt, không bán tất cả"
    - "Nếu cash >= 0 sau khi bán đủ: không mark is_bankrupt = True, không transfer cho creditor"
  debug_session: ""
