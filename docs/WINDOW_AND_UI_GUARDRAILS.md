# Window And UI Guardrails

Tài liệu này chỉ tập trung vào khu vực cửa sổ app, topbar, logout dialog, dropdown.

## 1. Những hành vi phải giữ nguyên

- Chỉ có 2 trạng thái cửa sổ:
  - `windowed`
  - `maximized`
- Nút vuông maximize của Windows phải dùng được.
- Không được để rê chuột vào mép/góc hiện icon resize/scale.
- Không được thêm nút maximize custom vào topbar nếu user không yêu cầu.
- Không được làm hỏng nút `X`.
- Không được làm hỏng dialog `Log out`.
- Không được làm hỏng dropdown `Work Schedule`.

## 2. File nào chịu trách nhiệm

- `main.py`
  - tạo app root
  - window geometry
  - native window style
  - `WM_DELETE_WINDOW`
- `main_app.py`
  - topbar
  - `Log out`
  - `Work Schedule` dropdown
  - `handle_click_outside`

## 3. Những điều không được làm nếu chưa có yêu cầu rõ

- không đổi cơ chế window handling
- không thêm nút topbar mới
- không sửa lại spacing topbar
- không refactor toàn bộ `handle_click_outside`
- không đổi flow `Log out -> Yes/No`
- không đổi chữ `Version: 0.0.1`

## 4. Rủi ro đã từng gặp

### Khi sửa sai `main.py`

Có thể gây ra:
- nút vuông Windows chết
- vẫn resize được
- còn icon resize
- nút `X` không đóng app
- dialog hệ thống bấm không ăn
- lỗi callback `ctypes`

### Khi sửa sai `main_app.py`

Có thể gây ra:
- lỗi `bad window path name`
- dropdown bị destroy rồi nhưng callback vẫn gọi `place_forget()`
- spam lỗi terminal
- logout/dialog nhìn như bị đơ

## 5. Rule kỹ thuật khi chạm vào dropdown

- luôn kiểm tra widget còn tồn tại với `winfo_exists()`
- chỉ `place_forget()` khi widget còn sống
- cẩn thận với callback root bind kiểu click-outside vì nó vẫn có thể chạy sau khi frame đã bị destroy

## 6. Checklist test nhanh

1. Mở app.
2. Bấm nút vuông Windows.
3. Bấm lại để về `windowed`.
4. Rê chuột vào mép/góc cửa sổ.
5. Bấm `Log out`.
6. Bấm `No`.
7. Bấm `Log out` lại.
8. Bấm `Yes`.
9. Mở dropdown `Work Schedule`.
10. Click ra ngoài để đóng.
11. Xem terminal có lỗi mới không.

## 7. Nếu buộc phải sửa vùng này

- sửa ít nhất có thể
- đổi một chỗ, test ngay
- nếu vừa sửa window vừa sửa logout/dropdown trong cùng turn, rủi ro rất cao
- nếu không chắc, nên dừng ở mức giải thích và xin xác nhận của user trước
