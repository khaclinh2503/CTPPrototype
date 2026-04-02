# Requirements: CTPPrototype — Cờ Tỷ Phú AI Simulator

**Defined:** 2026-04-01
**Core Value:** AI tự động hoàn chỉnh một ván đấu, lưu kết quả, và dùng lịch sử đó để chơi tốt hơn ở ván tiếp theo.

## v1 Requirements

### Game Core — Bàn cờ & Game Loop

- [x] **CORE-01**: Game khởi tạo ván đấu với 2-4 người chơi AI
- [x] **CORE-02**: Người chơi lần lượt tung xúc xắc (2d6) và di chuyển theo số ô tương ứng
- [x] **CORE-03**: Vòng lặp turn kết thúc khi chỉ còn 1 người chơi không phá sản (hoặc đạt `max_turns`)
- [x] **CORE-04**: Điều kiện phá sản: tiền < 0, bán/mất hết tài sản không đủ bù nợ
- [x] **CORE-05**: Hỗ trợ `max_turns` trong config để ngăn game vô tận

### Config System — Đọc dữ liệu từ file

- [x] **CONF-01**: Map board đọc từ file JSON/YAML (danh sách ô, loại ô, thuộc tính)
- [x] **CONF-02**: Skill definitions đọc từ file config riêng (JSON/YAML), validate schema
- [x] **CONF-03**: Pendant definitions đọc từ file config riêng (schema khác skill)
- [x] **CONF-04**: Pet definitions đọc từ file config riêng (schema khác skill và pendant)
- [x] **CONF-05**: Game rules đọc từ file config (tiền khởi đầu, giá xây nhà, lãi suất thuê, v.v.)
- [x] **CONF-06**: Config validation bắt lỗi schema sai trước khi game start

### Player System — Skill / Pendant / Pet

- [ ] **PLAY-01**: Mỗi người chơi có slot: 5 skills, 3 pendants, 1 pet (đọc từ config)
- [ ] **PLAY-02**: Skills là passive buffs — áp dụng tự động, không cần activation
- [ ] **PLAY-03**: Pendants là passive buffs — schema config riêng, effect có thể overlap skills
- [ ] **PLAY-04**: Pet là passive buff — 1 pet/player, schema config riêng
- [ ] **PLAY-05**: Buff stacking: tất cả StatDelta từ skills + pendants + pet được cộng dồn khi resolve
- [ ] **PLAY-06**: AI nhận bộ skill/pendant/pet ngẫu nhiên từ pool config khi bắt đầu ván

### Tile System — Loại ô trên bàn cờ

- [x] **TILE-01**: Ô đất (property): có giá mua, cấp độ nâng cấp (1→max), tiền thuê theo cấp
- [x] **TILE-02**: Ô tù / góc phạt: người chơi mất N lượt (N định nghĩa trong config)
- [x] **TILE-03**: Ô thuế: trả tiền cố định cho bank
- [x] **TILE-04**: Ô du lịch: teleport người chơi đến ô đích (đích định nghĩa trong config)
- [x] **TILE-05**: Ô lễ hội (góc): nhận thưởng hoặc hiệu ứng đặc biệt theo config
- [x] **TILE-06**: Ô Cơ hội: rút thẻ ngẫu nhiên từ deck, áp dụng effect của thẻ

### Property & Trading — Mua bán đất

- [x] **PROP-01**: Người chơi dừng ở ô đất chưa có chủ → AI quyết định mua hay bỏ qua
- [x] **PROP-02**: Người chơi dừng ở ô đất của đối thủ → trả tiền thuê theo cấp hiện tại
- [x] **PROP-03**: Nếu property chưa đạt max upgrade → người chơi dừng có thể mua từ chủ theo giá config (acquisition price)
- [x] **PROP-04**: AI quyết định có bán property hay không khi bị offer giá acquisition
- [x] **PROP-05**: Nâng cấp property: AI quyết định upgrade khi đủ tiền và điều kiện

### AI Engine — Ra quyết định

- [ ] **AI-01**: Mỗi quyết định (mua/bỏ qua, bán/giữ, upgrade/không) được đánh giá qua heuristic scoring
- [ ] **AI-02**: Heuristic tính điểm dựa trên: tiền hiện tại, vị trí ô, tài sản đang sở hữu, trạng thái đối thủ
- [ ] **AI-03**: Monte Carlo rollout: simulate N lượt giả định để đánh giá quyết định quan trọng
- [ ] **AI-04**: AI cân nhắc passive buff từ skills/pendant/pet khi tính toán expected value
- [ ] **AI-05**: Mỗi AI player có `personality` (aggressive / balanced / defensive) đọc từ config

### History & Learning — Lưu trữ và cải thiện

- [ ] **HIST-01**: Mỗi ván đấu lưu game log vào SQLite (lượt, quyết định, tài sản, kết quả)
- [ ] **HIST-02**: Sau ván, tính win-rate và expected income theo strategy type
- [ ] **HIST-03**: AI đọc lịch sử để điều chỉnh heuristic weights (thưởng/phạt theo outcome)
- [ ] **HIST-04**: Export kết quả dưới dạng CSV/JSON để phân tích ngoài game

### Visualization — Hiển thị Pygame

- [ ] **VIZ-01**: Board render đúng layout tùy chỉnh từ config (tile positions, labels)
- [ ] **VIZ-02**: Quân cờ hiển thị vị trí hiện tại của từng player trên board
- [ ] **VIZ-03**: Panel thông tin: tiền, tài sản, skills/pet của mỗi player
- [ ] **VIZ-04**: Log panel hiển thị hành động vừa xảy ra (mỗi lượt)
- [ ] **VIZ-05**: Speed control: pause, step-by-step, 1x, 5x, 10x, max (headless)
- [ ] **VIZ-06**: Khi game kết thúc: màn hình kết quả với thống kê ván đấu

## v2 Requirements

### Analytics Dashboard

- **ANLT-01**: Biểu đồ wealth timeline theo từng player trong ván đã chơi
- **ANLT-02**: So sánh win-rate giữa các strategy/personality type qua nhiều ván
- **ANLT-03**: Heatmap ô nào được mua nhiều nhất / sinh lời nhất

### Advanced AI

- **ADAI-01**: Coalition detection: AI phát hiện khi 1 player sắp thống trị, điều chỉnh để counter
- **ADAI-02**: Reinforcement learning upgrade path (thay heuristic weights bằng trained model)

### Map Editor

- **MAPE-01**: UI editor để tạo/sửa board config trực quan (không cần sửa JSON thủ công)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Online multiplayer | Project là offline simulator; network adds complexity không cần thiết |
| Human player input | Toàn bộ AI, không cần UI input during game |
| Mobile / web platform | Python + Pygame = desktop only |
| Luật Monopoly chuẩn Hasbro | Dùng luật tự thiết kế, không cần compatibility |
| Negotiation AI (free-form bargaining) | Quá phức tạp cho v1; thay bằng structured acquisition rule |
| Sound / music | Không ảnh hưởng simulation value |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 – CORE-05 | Phase 1 | Pending |
| CONF-01 – CONF-06 | Phase 1 | Pending |
| TILE-01 – TILE-06 | Phase 1 | Pending |
| PLAY-01 – PLAY-06 | Phase 2 | Pending |
| PROP-01 – PROP-05 | Phase 2 | Pending |
| AI-01 – AI-05 | Phase 3 | Pending |
| HIST-01 – HIST-04 | Phase 3 | Pending |
| VIZ-01 – VIZ-06 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after initial definition*
