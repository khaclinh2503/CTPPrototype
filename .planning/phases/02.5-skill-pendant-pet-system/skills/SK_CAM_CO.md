# Skill: Cắm Cờ

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | SK_CAM_CO |
| Name | Cắm Cờ |
| Trigger | MOVE phase — mỗi khi đi **qua** ô CITY trống (chưa có chủ) |

## Trigger Conditions

Check khi di chuyển bằng:
- **Dice Walk** — đổ xúc xắc thường (bao gồm lượt thêm từ SK_HQXX, SK_JOKER)
- **Sweep Walk** — SK_O_KY_DIEU (đi 32 bước, 1 vòng)

**Không check** khi di chuyển bằng: Travel Walk, Teleport, Skill Walk miễn nhiễm (xem D-54).

## Effect

Activation: `random(0, 100) < current_rate`

Nếu active → lấy sở hữu ô CITY trống đó miễn phí (`tile.owner_id = player.player_id`, level giữ nguyên L0).

## Rate Decay (trong 1 lượt)

Mỗi lần skill active trong lượt đó, rate giảm theo chuỗi cố định:

| Lần active | Giảm thêm | Tổng giảm |
|------------|-----------|-----------|
| 1st        | −1%       | −1%       |
| 2nd        | −3%       | −4%       |
| 3rd        | −5%       | −9%       |
| 4th        | −7%       | −16%      |
| 5th+       | 0%        | −16% (giữ nguyên) |

**Reset:** Về `rate_at_star` gốc vào đầu lượt tiếp theo của player.

```
# Đầu mỗi lượt
player.cam_co_decay_index = 0
player.cam_co_current_rate = rate_at_star

# Mỗi khi qua ô CITY trống
if random(0, 100) < player.cam_co_current_rate:
    tile.owner_id = player.player_id
    decay = [1, 3, 5, 7]
    if player.cam_co_decay_index < len(decay):
        player.cam_co_current_rate -= decay[player.cam_co_decay_index]
        player.cam_co_decay_index += 1
```

## Rank Config

| Rank | Min Star | Rate (base) | Chance (+/star) | Rate tại 5★ |
|------|----------|-------------|-----------------|-------------|
| C    | —        | —           | —               | Không có    |
| D    | —        | —           | —               | Không có    |
| B    | —        | —           | —               | Không có    |
| A    | 1★       | 6%          | +1%             | 10%         |
| S    | 1★       | 11%         | +1%             | 15%         |
| R    | —        | dùng config S | —             | 15% (S5★)  |

## Notes

- Check mỗi bước đi qua (không chỉ ô dừng lại)
- **Chain với SK_PHA_HUY**: khi PhaHuy phá nhà đối thủ → tile trở thành trống → CắmCờ check ngay lập tức tại tile đó
- Cần track `cam_co_decay_index` và `cam_co_current_rate` trên Player trong lượt
- Tile level giữ nguyên 0 khi cắm cờ (player chưa xây gì)
- Stub AI: không cần logic đặc biệt
