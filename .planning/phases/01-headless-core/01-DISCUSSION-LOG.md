# Phase 1: Headless Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 01-headless-core
**Areas discussed:** Schema nâng cấp ô đất, Effect thẻ sự kiện, Output headless runner, Cấu trúc thư mục project

---

## Schema nâng cấp ô đất

| Option | Description | Selected |
|--------|-------------|----------|
| 3 cấp | Cấp 0→3, đơn giản, dễ balance | |
| 5 cấp | Giống Monopoly chuẩn hơn, AI có nhiều quyết định hơn | ✓ |
| Tùy config mỗi ô | max_level per tile, linh hoạt nhất | |

**User's choice:** 5 cấp  
**Notes:** Sau khi xem Board.json thực tế, schema đã có sẵn dạng dict `{"1": {"build": X, "toll": Y}}` — giữ nguyên format này cho Pydantic schema.

---

## Effect thẻ sự kiện

| Option | Description | Selected |
|--------|-------------|----------|
| Chỉ implement 5 thẻ isActive | EF_3, EF_19, EF_20, EF_22, EF_27 | |
| Implement theo nhóm loại | Tiền + Di chuyển trước, stub còn lại | |
| Stub tất cả | Mọi EF_X trả no-op Phase 1 | |
| Phase 1 chỉ cần 7 tile types | Land, Resort, Prison, Travel, Tax, Start, Festival | ✓ |

**User's choice:** Phase 1 chỉ init bàn cờ 32 ô với 7 loại tile. FortuneSpace stub.  
**Notes:** Card.json có 29 thẻ (IT_CA_1→IT_CA_29), 5 đang isActive. Toàn bộ card effects để Phase 3 implement.

---

## Output của headless runner

| Option | Description | Selected |
|--------|-------------|----------|
| Console log từng lượt | In mỗi turn: ai di chuyển, tile gì, tiền thay đổi | ✓ |
| Chỉ tóm tắt cuối ván | Kết quả cuối: winner, turns, tiền mỗi player | |
| Cả hai — verbose flag riêng | --headless tóm tắt, --headless --verbose từng lượt | |

**User's choice:** Console log từng lượt  
**Notes:** Cuối ván vẫn in summary.

---

## Cấu trúc thư mục project

| Option | Description | Selected |
|--------|-------------|----------|
| Feature folders | ctp/core/, ctp/config/, ctp/tiles/, ctp/events/ | ✓ |
| Flat trong src/ | src/game_model.py, src/config_loader.py, ... | |
| Single package ctp/ | ctp/model.py, ctp/config.py, ctp/tiles.py | |

**Config location:**

| Option | Description | Selected |
|--------|-------------|----------|
| Giữ config/ ở root | config/Board.json — đường dẫn ngắn | |
| Dời vào trong package | ctp/config/Board.json — package tự chứa config | ✓ |

**User's choice:** Feature folders + config dời vào `ctp/config/`

---

## Claude's Discretion

- Tên Pydantic model classes
- EventBus implementation detail
- Test framework (pytest)
- Log format chi tiết

## Deferred Ideas

- FortuneSpace card effects → Phase 3
- Buff system → Phase 2
- Multi-map support → sau Phase 4
- ResortSpace mini-game → sau Phase 4
