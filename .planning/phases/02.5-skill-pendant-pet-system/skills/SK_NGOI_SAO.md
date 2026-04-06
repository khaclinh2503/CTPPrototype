# Skill: Ngôi Sao

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_NGOI_SAO |
| Name | Ngôi Sao |
| Trigger | RESOLVE_TILE phase (reactive) — khi đối thủ dừng tại property của player |

## Effect Flow

```
Đối thủ dừng tại ô của player
    ↓
Skill check: random(0,100) < rate_at_star?
    ↓ active
Toll × 2 (luôn xảy ra)
    ↓
Đối thủ có thẻ Thiên Thần (IT_CA_1 / EF_20)?
    ↓ có
Đối thủ dùng thẻ → check hủy:
    - 70%: thẻ bị hủy (held_card = None), đối thủ vẫn trả toll × 2
    - 30%: thẻ hoạt động bình thường (toll được miễn)
```

### Chi tiết

- **Effect 1:** Toll × 2 — luôn xảy ra khi skill active (không check thêm)
- **Effect 2:** Chỉ check khi đối thủ **chủ động dùng** thẻ Thiên Thần để counter:
  - 70%: `opponent.held_card = None`, đối thủ vẫn trả đủ toll × 2
  - 30%: thẻ hoạt động, toll được miễn hoàn toàn

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 14%         | +3%             | 26%         |
| S    | 1★       | 29%         | +4%             | 45%         |
| R    | —        | dùng config S | —             | 45% (S5★)  |

## Notes

- **Priority với SK_CUONG_CHE**: CướngChế check trước — nếu CướngChế active, đối thủ bị ném đến ô khác, NgôiSao tại ô này không check. NgôiSao chỉ trigger tại ô đích nếu player sở hữu ô đó
- Effect 2 chỉ trigger nếu đối thủ **có** Thiên Thần và **cố dùng** — không ảnh hưởng thẻ khác
- Nếu đối thủ không có Thiên Thần → chỉ effect 1 (toll × 2) xảy ra
- Stub AI: luôn dùng thẻ Thiên Thần nếu có (bị hủy 70% hay không)
