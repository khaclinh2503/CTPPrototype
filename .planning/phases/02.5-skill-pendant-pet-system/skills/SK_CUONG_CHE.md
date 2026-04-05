# Skill: Cưỡng Chế

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_CUONG_CHE |
| Name | Cưỡng Chế |
| Trigger | RESOLVE_TILE phase (reactive) — khi **đối thủ di chuyển đến ô player đang đứng** |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → ném đối thủ đến **Biểu Tượng (L5)** của player.
- Tile effect (toll) tại Biểu Tượng **xảy ra bình thường**
- Nếu player có nhiều Biểu Tượng → chọn ô **đắt nhất** (highest invested build cost)

```
landmarks = [
    board.get_tile(pos) for pos in player.owned_properties
    if board.get_tile(pos).building_level == 5
]
if landmarks:
    target = max(landmarks, key=lambda t: calc_invested_build_cost(board, t.position))
    opponent.move_to(target.position)
    resolve_tile(opponent, target)  # toll bình thường
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 50%         | +2%             | 58%         |
| S    | 1★       | 60%         | +3%             | 72%         |
| R    | —        | dùng config S | —             | 72% (S5★)  |

## Notes

- Nếu player chưa có Biểu Tượng nào → skill fail silently
- Đối thủ vẫn có thể dùng thẻ/skill để counter toll tại Biểu Tượng
- **Priority với SK_NGOI_SAO**: CướngChế check trước → nếu active, đối thủ bị ném đến L5, NgôiSao tại ô hiện tại **không check**. NgôiSao chỉ có thể trigger tại ô đích (L5) nếu player cũng sở hữu ô đó
- Stub AI: không cần logic đặc biệt
