# 🎲 Luật Chơi Cờ Tỷ Phú ZingPlay

## 1. Mục tiêu

Chiến thắng ván chơi bằng 1 trong 5 cách sau đây:
- Phá sản tất cả đối thủ
- Sở hữu tất cả ô Resort
- Sở hữu 3 cặp nhà đất cùng màu
- Sở hữu toàn bộ nhà đất và resort trên 1 hàng
- Sau 25 lượt chơi, bạn là người có tổng giá trị bất động sản lớn nhất

---

## 2. Thành phần chính

- Bàn chơi: các bàn chơi khác nhau có thể có số lượng ô, loại ô khác nhau (Cổ điển, Cổ tích, Wallstreet,...)
- Người chơi: 2-4 người
- Khi bắt đầu ván chơi, mỗi người chơi có:
    - Nhân vật: mang kỹ năng nv
    - Trang sức: mang kỹ năng trang sức
    - Pet: mang kỹ năng pet
    - Xúc xắc: tăng chỉ số khi đổ xúc xắc
    - Vật phẩm hỗ trợ: mua từ cửa hàng, dùng trong ván chơi để tạo lợi thế
    - Số tiền khởi đầu như nhau

---

## 3. Bắt đầu trò chơi

- Random 1 người chơi đi trước
- Nhận số tiền khởi đầu bằng nhau
- Tất cả bắt đầu tại ô khởi hành

---

## 4. Luật chơi cơ bản

### Game loop

- Chơi theo lượt từ người đi đầu, mỗi lượt gồm:
    1. Tung xúc xắc
    2. Di chuyển
    3. Thực hiện hành động tại ô dừng
    4. Kết thúc lượt, chuyển sang người chơi tiếp theo
    5. Lặp lại cho đến khi có người chiến thắng hoặc đạt 25 lượt chơi

### 🎯 Lượt chơi

- Tung 2 xúc xắc và di chuyển theo số ô tương ứng
- Thực hiện hành động tại ô dừng
- Nếu tung xúc xắc đôi, được chơi tiếp lượt nữa (tối đa 3 lần, nếu lần thứ 3 vẫn là đôi sẽ bị đi tù)

### Tung xúc xắc

- Số xúc xắc: 2
- Số mặt xúc xắc: 6
- Di chuyển theo tổng số mặt xúc xắc
- Căn lực: chọn các khoảng lực để tăng xác suất ra số mong muốn:
  - Khoảng lực 0: 2-4
  - Khoảng lực 1: 5-7
  - Khoảng lực 2: 7-9
  - Khoảng lực 3: 10-12
- Tỷ lệ "Điều kiển xúc xắc":
  - hệ số random quyết định kết quả xúc xắc có nằm trong khoảng lực đã chọn hay không.
  - Với xúc xắc cơ bản, tỷ lệ này là 15%, nghĩa là có 15% cơ hội kết quả xúc xắc sẽ nằm trong khoảng lực đã chọn, và 85% cơ hội sẽ là kết quả ngẫu nhiên bình thường.
  - Người chơi có thể tăng tỷ lệ này bằng cách sử dụng kỹ năng nhân vật, trang sức, pet hoặc vật phẩm hỗ trợ.
- Sử dụng vật phẩm để chi phối kết quả xúc xắc:
  - Vật phẩm đổ đôi: luôn đổ ra 2 số giống nhau
  - Vật phẩm chẵn lẻ: luôn đổ ra kết quả chẵn hoặc lẻ

### Di chuyển

- Người chơi di chuyển theo chiều kim đồng hồ trên bàn chơi
- Một số kỹ năng và hiệu ứng có thể cho phép di chuyển ngược chiều kim đồng hồ
- Một số kỹ năng và hiệu ứng có thể cho phép di chuyển thêm hoặc bớt số ô di chuyển
- Một số kỹ năng và hiệu ứng có thể cho phép chọn điểm đến thay vì di chuyển theo xúc xắc
- Một số kỹ năng và hiệu ứng có thể chặn người chơi dừng lại tại khi gặp phải
- Một số kỹ năng và hiệu ứng có thể đưa người chơi đến ô đất khác khi dừng lại: hố đen, bẫy băng,...

---

## 5. Các ô trên map

### Tổng quan

- Mỗi loại ô lại có hiệu ứng khác nhau, chủ yếu là hiệu ứng khi người chơi đi đến ô đó (check-in).
- Ngoài ra còn một số hiệu ứng đặc biệt khác: khi sở hữu ô, khi đi qua ô

### Các loại ô trên map

#### Ô CITY

"Ô CITY là ô tài sản cốt lõi của game, người chơi có thể đi đến và sở hữu, người khác đến tham quan sẽ phải trả phí, có 5 cấp độ và màu sắc khác nhau theo cặp"

- Mỗi ô đất có giá trị mua và giá trị nâng cấp khác nhau theo config bàn chơi
- Sở hữu ô đất: trả tiền mua cho ngân hàng, nhận được phí tham quan khi đối thủ đi đến ô đó
- Nâng cấp ô đất: Có 5 cấp độ từ cắm cờ đến nhà 1, nhà 2, nhà 3 và LANDMARK
- Giá mua, tham quan và mua lại tăng dần theo số nhà sở hữu, không thể mua lại LANDMARK
- Khi đi đến:
  - nếu chưa có chủ, có thể mua;
  - nếu đã có chủ, phải trả phí tham quan cho chủ, sau khi trả phí có quyền được mua lại nếu ô này chưa lên cấp LANDMARK;
  - nếu chủ là mình, có thể nâng cấp
- Sở hữu 3 cặp ô CITY cùng màu sẽ đạt điều kiện chiến thắng 3 cặp màu.

#### Ô RESORT

"Ô RESORT là ô tài sản đặc biệt có thể đi đến và sở hữu nhưng không được mua lại"

- Có 4 đến 5 ô RESORT phân bổ rải rác trên bàn chơi, giá trị ô thấp nhưng ko thể mua lại.
- Phí tham quan RESORT tăng theo số RESORT đã sở hữu hoặc số lần tham quan
- Khi đi đến:
  - nếu chưa có chủ, có thể mua;
  - nếu đã có chủ, phải trả phí tham quan cho chủ, không được mua lại
- Sở hữu tất cả RESORT sẽ đạt điều kiện chiến thắng du lịch

#### Ô Khí Vận

"Ô Khí Vận là ô bổ trợ có tính may rủi và giúp tăng tính ngẫu nhiên và replay của bàn chơi"

- Khi đi đến: Người chơi nhận được 1 trong khoảng 15-20 thẻ cơ hội ngẫu nhiên (mechanic giống monopoy)

#### Ô THUẾ

"Ô THUẾ là ô bổ trợ kiểu rubber-band giúp người chơi thu hẹp khoảng cách tài sản"

- Khi đi đến: Người chơi phải trả tiền thuế = 10% tổng tài sản đang sở hữu, nếu không đủ tiền trả, người chơi sẽ phải bán nhà hoặc bị phá sản.

#### Ô START

Ô neutral cho tất cả người chơi, giúp quá trình chơi tăng tiến

- Người chơi bắt đầu tại ô này
- Mỗi khi di chuyển được 1 vòng (đi qua ô START hoặc đi đến ô START), người chơi nhận được tiền thưởng = 15% tiền khởi đầu
- Khi đi đến: người chơi được chọn 1 trong ô CITY chưa nâng cấp max để thực hiện hành động nâng cấp

#### Ô TÙ

"Ô TÙ là ô bổ trợ mechanic di chuyển, trừng phạt người chơi di chuyển nhiều khi đổ đôi liên tiếp 3 lần"

- Khi đổ đôi 3 lần, người chơi bị ném vào tù.
- Khi vào tù, người chơi mất lượt hiện tại và phải đợi sang lượt sau để thoát tù
- Khi đang ở tù, người chơi có 3 lựa chọn để thoát tù:
  - Dùng thẻ "Thoát Tù"
  - Đổ xúc xắc ra kết quả đôi, nếu không sẽ vẫn đứng yên trong tù
  - Trả 5% tiền khởi đầu để được ra
- Sau khi ở tù 3 lượt đổ xúc xắc không ra kết quả đôi, người chơi được thả khỏi tù và di chuyển tiếp

#### Ô LỄ HỘI

"Ô LỄ HỘI là 1 ô phụ trợ giúp tăng phí của một ô CITY hoặc RESORT lên cao hơn"

- Khi đi đến: người chơi được chọn 1 trong các ô CITY hoặc RESORT của mình để tăng phí lên
- Sau mỗi lần tổ chức lễ hội, phí tăng dần: X2, X3, X4

#### Ô TRAVEL

"Ô TRAVEL là 1 ô phụ trợ giúp di chuyển thẳng đến ô mong muốn thay vì phải đổ xúc xắc ngẫu nhiên"

- Khi đi đến: người chơi dừng lượt chơi, ở lượt chơi tiếp theo người chơi được chọn 1 ô bất kì trên bàn chơi để di chuyển đến thay vì đổ xúc xắc

#### Ô MINI GAME

"Ô MINI GAME là 1 ô phụ trợ, người chơi đi vào chơi game để nhận thêm tiền"

- Khi đi đến: người chơi được đặt tiền vào chơi đỏ-đen, thắng nhận tiền, thua mất tiền

---

## 6. Phá sản

- Khi không đủ tiền trả phí tham quan, người chơi được chọn bán tài sản của mình cho ngân hàng với giá 50% để trả nợ
- Kể cả khi bán hết tài sản vẫn không đủ tiền, hoặc người chơi lựa chọn phá sản -> người chơi đó bị loại khỏi ván chơi
- Khi phá sản, tất cả ô đất của người chơi đó sẽ bị xóa đi, trở thành ô đất trống, không ai sở hữu, và có thể mua lại như bình thường

---

## 7. Hệ thống skill

### 7.1 Tổng quan

Skill là cơ chế cốt lõi tạo sự khác biệt giữa các người chơi. Mỗi skill hoạt động theo công thức cơ bản:

> **Nếu [điều kiện X] xảy ra → có [n%] xác suất → thực hiện [hệ quả Y] → cập nhật trạng thái game**

Ví dụ: "Khi người chơi tung xúc xắc → có 30% xác suất → kết quả xúc xắc tự động là đôi → người chơi được đi thêm 1 lượt"

Skill đến từ 4 nguồn: nhân vật, trang sức, pet, và clan skill. Tất cả đều hoạt động theo cơ chế **trigger**

---

### 7.2 Cấu trúc một skill

Mỗi skill được định nghĩa bởi 3 thành phần:

```
skill {
  trigger_event       // Sự kiện kích hoạt skill
  probability config  // Config xác suất xảy ra hay config hệ quả (n%)
  consequence         // Hệ quả tác động lên game state
}
```

**Ví dụ:**
```
skill: DKXX
  trigger_event:        người chơi tung xúc xắc
  probability config:   25%
  consequence:          tăng 25% tỉ lệ chính xác
```

---

### 7.4 Danh mục nhóm skill, tác dụng và tương tác của các skill

Tham khảo skill document @vunnt5

## 8. Kết thúc

- Trò chơi kết thúc sớm khi đạt 1 trong 4 điều kiện chiến thắng đầu tiên hoặc sau 25 lượt chơi, người chơi có tổng giá trị bất động sản lớn nhất sẽ chiến thắng.

---