# Pendant: Mạng nhện

## Thông tin cơ bản

| Field | Value |
|-------|-------|
| ID | PT_MANG_NHEN |
| Name | Mạng nhện |
| Trigger | `ON_LAND_OPPONENT` — khi player dừng tại ô đất của đối thủ |

## Effect — 2 rate độc lập (cùng 1 trigger)

### Rate 1: Giảm 100% phí tham quan

```
# ON_LAND_OPPONENT
if random(0, 100) < rate1_at_rank:
    toll = 0  # miễn phí hoàn toàn lần này
```

### Rate 2: Cướp nhà đối thủ sau khi trả phí

```
# ON_LAND_OPPONENT (sau khi toll đã xử lý)
if random(0, 100) < rate2_at_rank:
    tile.owner_id = player.id   # đổi chủ sở hữu
    # building level giữ nguyên; resort chỉ đổi owner_id (D-28)
```

**Lưu ý thứ tự:**
- Rate1 check trước (miễn phí toll)
- Rate2 check sau (cướp nhà — bất kể rate1 có active hay không)
- Nếu cả hai active: miễn phí toll VÀ cướp nhà → combo mạnh nhất

Stub AI: cả hai — luôn active.

## Rank Config

| Rank | Rate 1 (miễn phí toll) | Rate 2 (cướp nhà) |
|------|------------------------|-------------------|
| B    | 3%                     | 5%                |
| A    | 5%                     | 7%                |
| S    | 8%                     | 10%               |
| R    | 20%                    | 15%               |
| SR   | 30%                    | 25%               |

## Activation Formula

```
r1_active = random(0, 100) < rate1_at_rank  # check trước
r2_active = random(0, 100) < rate2_at_rank  # check sau, độc lập
```

## Notes

- Cả 2 check đều xảy ra tại `ON_LAND_OPPONENT` — Rate2 check độc lập với Rate1
- Rate2 giống PT_CUOP_NHA về effect (cướp nhà), nhưng tỷ lệ thấp hơn và PT_MANG_NHEN có thêm Rate1 miễn phí toll
- Resort: chỉ đổi `owner_id`, không thay đổi level (D-28)
- Cả hai rate nhảy mạnh ở R/SR rank
