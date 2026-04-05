# Pendant: Chống mua nhà

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_CHONG_MUA_NHA |
| Name | Chống mua nhà |
| Trigger | `ON_OPPONENT_LAND_YOURS` — khi đối thủ dừng tại ô của player và có thể thực hiện acquisition |

## Effect

Khi đối thủ cố gắng mua lại ô đất của player, pendant có thể **block acquisition** đó.

```
# ON_OPPONENT_LAND_YOURS (tại thời điểm check acquisition)
block_rate = active_factor[building_level] * rate_at_rank / 100
if random(0, 100) < block_rate * 100:
    acquisition_blocked = True   # đối thủ không mua được
```

**active_factor theo building_level:**
| Level | active_factor |
|-------|--------------|
| L1    | 15%          |
| L2    | 35%          |
| L3    | 60%          |
| L4+   | 100%         |

Stub AI (player): luôn block nếu có thể.

## Rank Config

| Rank | rate_at_rank (base pendant rate) |
|------|----------------------------------|
| B    | 10%                              |
| A    | 20%                              |
| S    | 43%                              |
| R    | 62%                              |
| SR   | 70%                              |

## Activation Formula

```
block_rate = active_factor[building_level] * pendant_rate_per_rank
acquisition_blocked = random(0, 100) < block_rate * 100
```

Ví dụ: Pendant SR (70%) tại nhà L3 (60%): block_rate = 0.70 × 0.60 = 42% → random(0,100) < 42

## Notes

- Ô đất level ảnh hưởng trực tiếp đến xác suất block — nhà cấp cao hơn được bảo vệ tốt hơn
- `building_level` trong code: L1=1, L2=2, L3=3, L4=4 (nhà cấp 3), L5=5 (biểu tượng)
- L4+ (bao gồm Biểu Tượng): active_factor = 100% → block_rate = pendant_rate đầy đủ
- Nếu acquisition bị block: đối thủ vẫn phải trả toll bình thường, chỉ không mua được nhà
- Tham chiếu D-26 (PT_CHONG_MUA_NHA): `block_rate = active_factor[level] × pendant_rate`
