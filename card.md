# Card Mapping - Item.json

Mapping toàn bộ card trong game với effect tương ứng trong code.

- Config: `conf/json/Item.json` + `conf/json/Effect.json`
- Logic xử lý: `src/business/system/LogicSystem.java`
- Enum effect: `src/business/constant/EffectEnum.java`
- Hằng số card: `src/business/constant/ItemConst.java`

---

## Card Active (isActive = 1)

### IT_CA_1 — Angel (`eff_angel`)
- **Effect:** `EF_20` → `EF_SUPER_DEFEND`
- **Rate:** 5
- **Mô tả:** Lá bài phòng thủ mạnh nhất. Khi player dừng trên đất của đối thủ và phải trả tiền thuê, thẻ tự động kích hoạt miễn toàn bộ tiền (discount 100%). Có thể bị phá bởi skill `ON_OTHER_PAY_USE_ANGEL_DESTROY_ANGEL` của chủ đất. Cùng được nhận dạng là "defend card" với IT_CA_3.
- **Code:** `LogicSystem.java` → `case EF_SUPER_DEFEND` | `Player.java` → `isHasCardDefend()`, `getDefendCard()`

---

### IT_CA_2 — Giảm tiền thuê (`eff_discount_toll`)
- **Effect:** `EF_2` → `EF_DISCOUNT_TOLL` (value=50)
- **Rate:** 5
- **Mô tả:** Giảm 50% tiền thuê đất phải trả ngay tại lần dừng hiện tại. Áp dụng tức thì cho player đang dùng thẻ.
- **Code:** `LogicSystem.java` → `case EF_DISCOUNT_TOLL` → `player.discountToll(0.5)`

---

### IT_CA_3 — Khiên (`eff_shield`)
- **Effect:** `EF_3` → `EF_DEFEND`
- **Rate:** 10
- **Mô tả:** Lá bài phòng thủ thụ động. Khi bị đối thủ dùng card tấn công (ép bán, đổi thành phố, v.v.), player có thể dùng thẻ này để chặn. Logic chặn được kích hoạt qua `tryDefendAttack()`.
- **Code:** `Player.java` → `tryDefendAttack()`, `isHasCardDefend()`

---

### IT_CA_21 — Thoát ngục (`eff_escape`)
- **Effect:** `EF_19` → `EF_ESCAPE`
- **Rate:** 5
- **Mô tả:** Cho phép thoát khỏi nhà tù ngay lập tức khi đang bị giam. Được mua từ lobby (`LOBBY_ITEM_PRISON_BREAK`) và lưu vào danh sách `keepingCard` của player.
- **Code:** `Player.java` → `isHasCardPrisonBreak()` | Lobby: `case LOBBY_ITEM_PRISON_BREAK`

---

### IT_CA_23 — Chong chóng (`eff_pinwheel`)
- **Effect:** `EF_22` → `EF_GO_THOURH_LIFT_TILE` (value=100)
- **Rate:** 10
- **mapNotAvail:** 1, 3, 4, 5, 7
- **Mô tả:** Khi player dừng trên ô có thang/cầu tuột, thẻ này bỏ qua toàn bộ hiệu ứng dịch chuyển và di chuyển bình thường theo số bước đã đi. Nếu player có thẻ này mà không dùng, sẽ di chuyển bình thường qua `doNotUsingKeepingCard()`.
- **Code:** `LogicSystem.java` → `case EF_GO_THOURH_LIFT_TILE` → `player.moveByPinWheel(true)` | `Player.java` → `isHasCardPinwheel()`

---

### IT_CA_27 — Chống đá (`eff_anti_kick`)
- **Effect:** `EF_27` → `EF_ANTI_KICK`
- **Rate:** 0 (không rút ngẫu nhiên, chỉ mua từ lobby)
- **mapNotAvail:** 1, 2, 3, 4, 5, 7
- **Mô tả:** Bảo vệ player khỏi bị đá văng ra vị trí khác trên map đua (`checkKickMapRace`). Khi có người đứng cùng ô và điều kiện kick thỏa mãn, thẻ tự tiêu hủy và player ở lại vị trí thay vì bị đẩy ra.
- **Code:** `Player.java` → `checkKickMapRace()`, `isHasCardAntiKickAndDefendDeath()` | Lobby: `case LOBBY_ITEM_ANTI_KICK`

---

## Card Inactive (isActive = 0)

### Tấn công (category = CT_ATTACK)

---

### IT_CA_4 — Ép bán (`eff_force_sell`)
- **Effect:** `EF_4` → `EF_SELL` (target: TG_E_LAND, value=100)
- **Rate:** 5
- **Mô tả:** Bắt buộc đối thủ bán 1 lô đất họ đang sở hữu với 100% giá trị. Player chọn target là đất của đối thủ. Đối thủ có thể dùng IT_CA_1 hoặc IT_CA_3 để chặn.
- **Code:** `LogicSystem.java` → `case EF_SELL` → `owner.sellLand(land, 1.0)`

---

### IT_CA_5 — Đổi thành phố (`eff_change_city`)
- **Effect:** `EF_5` → `EF_EXCHANGE` (target: TG_S_LAND + TG_E_LAND)
- **Rate:** 5
- **Mô tả:** Hoán đổi quyền sở hữu giữa 1 lô đất của mình và 1 lô đất của đối thủ. Không thể hoán đổi Landmark. Đối thủ có thể dùng DEFEND để chặn.
- **Code:** `LogicSystem.java` → `case EF_EXCHANGE` → `match.exchange(land1, land2)`

---

### IT_CA_6 — Xâm lược ngoài hành tinh (`eff_alien_invaion`)
- **Effect:** `EF_6` → `EF_DES_BUILDING` (target: TG_E_BUILD_ADJ, value=1)
- **Rate:** 5
- **Mô tả:** Phá hủy 1 level tòa nhà trên lô đất kề cạnh của đối thủ. Chọn target trong danh sách các lô đất kề có nhà của đối thủ.
- **Code:** `LogicSystem.java` → `case EF_DES_BUILDING` → `landing.destroyByLevel(1)`

---

### IT_CA_7 — Động đất (`eff_earth_quake`)
- **Effect:** `EF_6` → `EF_DES_BUILDING` (target: TG_E_BUILD_ADJ, value=1)
- **Rate:** 5
- **Mô tả:** Tương tự IT_CA_6 (Alien Invasion). Phá hủy 1 level nhà trên đất kề cạnh của đối thủ. Dùng cùng effect EF_6.
- **Code:** `LogicSystem.java` → `case EF_DES_BUILDING` → `landing.destroyByLevel(1)`

---

### IT_CA_8 — Virus (`eff_virus`)
- **Effect:** `EF_7` → `EF_DISCOUNT_TOLL` (target: TG_E_LAND_ADJ, value=100, turn=5)
- **Rate:** 5
- **Mô tả:** Giảm tiền thuê các lô đất kề cạnh của đối thủ về 0% trong 5 lượt. Tấn công kinh tế dài hạn.
- **Code:** `LogicSystem.java` → `case EF_DISCOUNT_TOLL` → `player.discountToll(1.0)` áp lên đất đối thủ

---

### IT_CA_9 — Cát vàng / Bão cát (`eff_yellow_sand`)
- **Effect:** `EF_8` → `EF_DISCOUNT_TOLL` (target: TG_E_LAND_ADJ, value=50, turn=5)
- **Rate:** 5
- **Mô tả:** Giảm 50% tiền thuê các lô đất kề cạnh của đối thủ trong 5 lượt.
- **Code:** `LogicSystem.java` → `case EF_DISCOUNT_TOLL`

---

### IT_CA_10 — Mất điện thành phố (`eff_city_black_out`)
- **Effect:** `EF_7` → `EF_DISCOUNT_TOLL` (target: TG_E_LAND_ADJ, value=100, turn=5)
- **Rate:** 5
- **Mô tả:** Tương tự IT_CA_8 (Virus). Giảm thuê đất kề của đối thủ về 0 trong 5 lượt. Dùng cùng EF_7.
- **Code:** `LogicSystem.java` → `case EF_DISCOUNT_TOLL`

---

### IT_CA_22 — Bàn tay thần (`eff_god_hand`)
- **Effect:** `EF_21` → `EF_MOVE_TO_GOD_HAND` (target: TG_GH_LAND)
- **Rate:** 10
- **mapNotAvail:** 1, 3, 4, 5, 7
- **Mô tả:** Dịch chuyển player đến vị trí ô "God Hand" trên bản đồ. Player chọn target là ô God Hand.
- **Code:** `LogicSystem.java` → `case EF_MOVE_TO_GOD_HAND` → `player.moveTo(godPos, true)`

---

### IT_CA_26 — Chiếm đất (`eff_get_house`)
- **Effect:** `EF_23` → `EF_GET_HOUSE` (target: TG_E_LAND, value=100)
- **Rate:** 0
- **mapNotAvail:** 1, 2, 3, 4, 5, 7
- **Mô tả:** Lấy quyền sở hữu 1 lô đất của đối thủ. Nếu không chọn target cụ thể thì tự động mua đất thường (`doLogicNormalAcquireHouse`).
- **Code:** `LogicSystem.java` → `case EF_GET_HOUSE` → `player.doLogicGetLand(land)`

---

### IT_CA_28 — Chiếm đất 1 (`eff_get_house_1`)
- **Effect:** `EF_28` → `EF_GET_HOUSE_1` (target: TG_E_LAND, value=100)
- **Rate:** 0
- **mapNotAvail:** 1, 2, 3, 4, 5, 7
- **Mô tả:** Phiên bản thứ hai của chiếm đất, dùng `doGetLandFromOther()` thay vì `doLogicGetLand()`. Khác biệt logic nội bộ khi lấy đất từ đối thủ.
- **Code:** `LogicSystem.java` → `case EF_GET_HOUSE_1` → `player.doGetLandFromOther(land)`

---

### IT_CA_29 — Cờ (`eff_flag`)
- **Effect:** `EF_29` → `EF_MOVE_TO_FLAG`
- **Rate:** 10
- **mapNotAvail:** 1, 2, 3, 4, 7
- **Mô tả:** Di chuyển player đến cột cờ gần nhất trên bản đồ (có tính tiền qua START).
- **Code:** `LogicSystem.java` → `case EF_MOVE_TO_FLAG` → `player.moveToNearestFlagPole()`

---

### Di chuyển / Hỗ trợ bản thân

---

### IT_CA_12 — Lễ hội (`eff_festival`)
- **Effect:** `EF_10` → `EF_MOVE_TO_SPACE` (value=1)
- **Rate:** 10
- **Mô tả:** Di chuyển đến ô space type=1 gần nhất (thường là ô Start/lễ hội). Đi qua các ô giữa, có thể nhận tiền qua START.
- **Code:** `LogicSystem.java` → `case EF_MOVE_TO_SPACE` → `player.moveTo(targetPos, true)`

---

### IT_CA_13 — Du lịch lễ hội (`eff_festival_tour`)
- **Effect:** `EF_11` → `EF_MOVE_TO_FESTIVAL`
- **Rate:** 5
- **Mô tả:** Di chuyển đến lô đất đang có lễ hội được đặt. Nếu không có lễ hội nào đang diễn ra trên bản đồ, kết thúc lượt ngay.
- **Code:** `LogicSystem.java` → `case EF_MOVE_TO_FESTIVAL` → `player.moveToFestivalBuildByCardFortune()`

---

### IT_CA_14 — Khám phá (`eff_exploring`)
- **Effect:** `EF_13` → `EF_JUMP_TO_SPACE` (value=5)
- **Rate:** 5
- **Mô tả:** Nhảy tức thời đến ô type=5 mà không đi qua các ô giữa (không nhận tiền qua START, không kích hoạt hiệu ứng đường đi).
- **Code:** `LogicSystem.java` → `case EF_JUMP_TO_SPACE` → `player.updateNewPos(targetPos)`

---

### IT_CA_15 — Du lịch (`eff_travel`)
- **Effect:** `EF_12` → `EF_MOVE_TO_SPACE` (value=9)
- **Rate:** 5
- **Mô tả:** Di chuyển đến ô space type=9. Đi qua các ô giữa, có thể nhận tiền qua START.
- **Code:** `LogicSystem.java` → `case EF_MOVE_TO_SPACE` → `player.moveTo(targetPos, true)`

---

### IT_CA_16 — Về Start (`eff_start`)
- **Effect:** `EF_14` → `EF_MOVE_TO_SPACE` (value=7)
- **Rate:** 5
- **Mô tả:** Di chuyển đến ô START (type=7). Đi qua các ô giữa, nhận tiền qua START.
- **Code:** `LogicSystem.java` → `case EF_MOVE_TO_SPACE` → `player.moveTo(targetPos, true)`

---

### IT_CA_24 — Ngân hàng (`eff_bank`)
- **Effect:** `EF_24` → `EF_MOVE_TO_BANK`
- **Rate:** 10
- **mapNotAvail:** 1, 2, 4, 5, 7
- **Mô tả:** Di chuyển đến ô ngân hàng gần nhất trên bản đồ.
- **Code:** `LogicSystem.java` → `case EF_MOVE_TO_BANK` → `player.moveToNearestSpecialTile(BANK_SPACE_ID)`

---

### IT_CA_25 — Văn phòng (`eff_agency`)
- **Effect:** `EF_25` → `EF_MOVE_TO_AGENCY`
- **Rate:** 10
- **mapNotAvail:** 1, 2, 4, 5, 7
- **Mô tả:** Di chuyển đến ô Agency (văn phòng môi giới bất động sản) gần nhất trên bản đồ.
- **Code:** `LogicSystem.java` → `case EF_MOVE_TO_AGENCY` → `player.moveToNearestSpecialTile(AGENCY_SPACE_ID)`

---

### Kinh tế / Tương tác

---

### IT_CA_11 — Thuế (`eff_tax`)
- **Effect:** `EF_26` → `EF_MOVE_TO_TAX`
- **Rate:** 10
- **mapNotAvail:** 2, 5, 7
- **Mô tả:** Di chuyển player đến ô thu thuế gần nhất trên bản đồ.
- **Code:** `LogicSystem.java` → `case EF_MOVE_TO_TAX` → `player.moveToNearestSpecialTile(TAX_SPACE_ID)`

---

### IT_CA_17 — Tổ chức lễ hội xúc xắc (`eff_host_dice_festival`)
- **Effect:** `EF_15` → `EF_HOLD_FESTIVAL` (target: TG_S_LAND)
- **Rate:** 10
- **Mô tả:** Đặt lễ hội lên 1 lô đất của bản thân (player chọn target). Nếu đang có lễ hội ở ô khác, lễ hội cũ sẽ bị xóa. Lễ hội giúp tăng tiền thuê khi đối thủ dừng vào.
- **Code:** `LogicSystem.java` → `case EF_HOLD_FESTIVAL` → `match.setFestival(targetLand)`

---

### IT_CA_18 — Phí (`eff_fee`)
- **Effect:** `EF_16` → `EF_DISCOUNT_TOLL` (value=-100, turn=1)
- **Rate:** 5
- **Mô tả:** Tăng gấp đôi tiền thuê đất của bản thân (value âm = tăng giá) trong 1 lượt kế tiếp. Dùng khi đối thủ sắp dừng vào đất của mình.
- **Code:** `LogicSystem.java` → `case EF_DISCOUNT_TOLL` → `player.discountToll(-1.0)` cho turn=1

---

### IT_CA_19 — Tặng thành phố (`eff_city_donate`)
- **Effect:** `EF_17` → `EF_DONATE` (target: TG_S_LAND + TG_E_PLAYER)
- **Rate:** 10
- **Mô tả:** Tặng 1 lô đất của mình cho 1 người chơi khác (thường là đồng đội trong 2v2). Không thể tặng Landmark. Không thể tặng cho người đã phá sản.
- **Code:** `LogicSystem.java` → `case EF_DONATE` → `player.donateLand(donatingLand, luckyPlayer)`

---

### IT_CA_20 — Từ thiện (`eff_charity`)
- **Effect:** `EF_18` → `EF_CHARITY` (value=5)
- **Rate:** 5
- **mapNotAvail:** 5
- **Mô tả:** Mỗi người chơi đang có nhiều tiền hơn người nghèo nhất phải nộp 5% gold vào cho người nghèo nhất. Áp dụng cho tất cả người chơi trong trận cùng lúc.
- **Code:** `LogicSystem.java` → `case EF_CHARITY` → tính `poorestPlayer`, thu `5% * match.getGold()` từ mỗi người và chuyển cho người nghèo nhất

---

## Tóm tắt phân loại

| Nhóm | Card |
|------|------|
| **Phòng thủ** | IT_CA_1 (Angel), IT_CA_3 (Shield), IT_CA_21 (Thoát ngục), IT_CA_27 (Chống đá) |
| **Tấn công** | IT_CA_4 (Ép bán), IT_CA_5 (Đổi đất), IT_CA_6 (Alien), IT_CA_7 (Động đất), IT_CA_8 (Virus), IT_CA_9 (Cát vàng), IT_CA_10 (Mất điện), IT_CA_22 (God Hand), IT_CA_26 (Chiếm đất), IT_CA_28 (Chiếm đất 1), IT_CA_29 (Cờ) |
| **Di chuyển** | IT_CA_12 (Lễ hội), IT_CA_13 (Du lịch lễ hội), IT_CA_14 (Khám phá), IT_CA_15 (Du lịch), IT_CA_16 (Về Start), IT_CA_24 (Ngân hàng), IT_CA_25 (Văn phòng) |
| **Kinh tế / Tương tác** | IT_CA_11 (Thuế), IT_CA_17 (Tổ chức lễ hội), IT_CA_18 (Phí), IT_CA_19 (Tặng đất), IT_CA_20 (Từ thiện) |
| **Đặc biệt** | IT_CA_23 (Chong chóng - bỏ qua thang/bẫy) |
