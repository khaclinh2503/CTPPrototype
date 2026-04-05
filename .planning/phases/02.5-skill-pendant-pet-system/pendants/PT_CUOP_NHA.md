# Pendant: Cướp nhà

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_CUOP_NHA |
| Name | Cướp nhà |
| Trigger | `ON_LAND_OPPONENT` — khi player dừng tại ô đất của đối thủ (sau khi trả toll) |

## Effect

Sau khi trả toll xong, nếu pendant active → player **cướp ô đất đó** khỏi đối thủ.

```
# ON_LAND_OPPONENT (sau khi toll đã được xử lý)
if random(0, 100) < rate_at_rank:
    tile.owner_id = player.id   # đổi chủ sở hữu
    # building level giữ nguyên nếu là CITY
    # nếu là RESORT: chỉ đổi owner_id (D-28)
```

Stub AI: luôn active (cướp nhà nếu có cơ hội).

## Rank Config

| Rank | Rate |
|------|------|
| B    | 5%   |
| A    | 7%   |
| S    | 10%  |
| R    | 15%  |
| SR   | 25%  |

## Activation Formula

```
active = random(0, 100) < rate_at_rank
```

## Notes

- Trigger **sau khi trả toll** — toll = 0 (do SK_BUA_SET, PT_MANG_NHEN, v.v.) vẫn được coi là đã trả toll → CướpNhà vẫn check bình thường
- **Không bị PT_CHONG_MUA_NHA block**: cướp nhà là cơ chế riêng, không phải "mua lại"
- Resort khi cướp: chỉ đổi `owner_id`, không thay đổi level (D-28)
- Tương tự effect của PT_MANG_NHEN R2 nhưng PT_CUOP_NHA là single-rate pendant
- Kết hợp cực mạnh với các pendant tăng toll như PT_KET_VANG (trả ít hơn rồi cướp)
