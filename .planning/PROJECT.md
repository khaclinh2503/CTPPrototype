# CTPPrototype — Cờ Tỷ Phú AI Simulator

## What This Is

Một game cờ tỷ phú (Monopoly-style) chạy trên desktop (Windows/Mac), nơi toàn bộ 2-4 người chơi đều do AI điều khiển tự động. Mỗi người chơi được trang bị hệ thống Skills, Pendant, và Pet (đều là passive buff, đọc từ file JSON/YAML config). AI vừa simulate nước đi tối ưu vừa học từ lịch sử các ván đã chơi để cải thiện chiến lược theo thời gian.

## Core Value

AI tự động hoàn chỉnh một ván đấu, lưu kết quả, và dùng lịch sử đó để chơi tốt hơn ở ván tiếp theo.

## Requirements

### Validated

- [x] Bàn cờ tùy chỉnh: ô đất, ô sự kiện, luật riêng đọc từ config (CONF-01 to CONF-06) — Validated in Phase 1: headless-core
- [x] Game loop hoàn chỉnh: xúc xắc, di chuyển, mua đất, thu tiền thuê, phá sản (CORE-01 to CORE-05, TILE-01 to TILE-06) — Validated in Phase 1: headless-core

### Active

- [ ] Bàn cờ tùy chỉnh: ô đất, ô sự kiện, luật riêng đọc từ config
- [ ] Hệ thống người chơi với Skills (passive, JSON/YAML)
- [ ] Hệ thống Pendant (passive, config riêng biệt với skill)
- [ ] Hệ thống Pet (passive, config riêng biệt với skill và pendant)
- [ ] AI engine: simulate nước đi + ra quyết định tối ưu mỗi lượt
- [ ] AI học từ lịch sử: lưu ván đấu, rút kinh nghiệm cho ván sau
- [ ] Visualization: board hiển thị real-time, tốc độ điều chỉnh được (step-by-step / fast-forward)
- [ ] 2-4 người chơi AI trong cùng một ván
- [ ] Game loop hoàn chỉnh: xúc xắc, di chuyển, mua đất, thu tiền thuê, phá sản

### Out of Scope

- Multiplayer online — dự án này là offline simulation, không cần network
- Thao tác thủ công của người dùng trong lúc chơi — toàn bộ do AI
- Mobile / web platform — chỉ desktop Python
- Luật Monopoly chuẩn Hasbro — dùng luật tự thiết kế

## Context

- Game engine: Python + Pygame (hoặc Tkinter nếu ưu tiên đơn giản)
- Config-driven: map, skills, pendants, pets đều đọc từ file JSON/YAML → dễ thêm/sửa không cần đụng code
- AI approach: rule-based simulation (evaluate possible actions) kết hợp với history-based learning (lưu game logs, điều chỉnh weights/strategy)
- Lịch sử ván đấu cần được persist (JSON hoặc SQLite) để AI cải thiện giữa các session

## Constraints

- **Tech Stack**: Python + Pygame/Tkinter — không dùng game engine khác
- **Offline only**: Không có server, không có network dependency
- **Config-first**: Mọi game data (map, skills, pendant, pet, rules) phải đọc từ file config — không hard-code
- **AI tự chủ**: Không có human input trong lúc game chạy

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| All players AI-controlled | Mục tiêu là benchmark và simulate, không cần human interaction | — Pending |
| Skills/Pendant/Pet đều là passive | Đơn giản hóa game loop, AI không cần quản lý activation timing | — Pending |
| Config-driven data | Dễ thêm nội dung mới mà không sửa code | — Pending |
| Simulate + history learning | Cân bằng giữa greedy optimization và long-term improvement | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-02 after phase 1 completion*
