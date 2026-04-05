# Skill: Ô Kỳ Diệu

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_O_KY_DIEU |
| Name | Ô Kỳ Diệu |
| Trigger | UPGRADE phase — khi nâng cấp lên **L4** (nhà cấp 3) |

## Effect

Activation: `random(0, 100) < rate_at_star`

Nếu active → player di chuyển **32 bước** (1 vòng đầy đủ), kết thúc tại chính ô đang đứng.

- **Đi qua START** → nhận thưởng passing bonus bình thường
- Tile effect tại ô xuất phát (ô đang đứng) **không trigger lại** (chỉ về lại vị trí cũ)

```
player.move_forward(32)  # 32 bước = 1 vòng, về đúng ô cũ
# START bonus được xử lý trong MOVE phase như bình thường
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 19%         | +1%             | 23%         |
| S    | 1★       | 24%         | +2%             | 32%         |
| R    | —        | dùng config S | —             | 32% (S5★)  |

## Notes

- Chỉ trigger khi nâng đúng lên L4 (nhà cấp 3), không trigger ở các level khác
- Convention: nhà cấp 3 = building_level L4 trong code
- 32 bước = đúng 1 vòng bàn cờ 32 ô → player về lại vị trí ban đầu
- START bonus nhận như bình thường khi đi qua
- Stub AI: không cần logic đặc biệt
