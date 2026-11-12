# Thiết kế: Lưu dữ liệu runtime trong AppData

## Mục tiêu
Khi chạy bộ cài `dist\QuizAssistant.exe`, thư mục cài đặt chứa app `QuizAssistant.exe` và uninstaller; cấu hình/API key, logs, ảnh chụp và lịch sử câu trả lời mới được lưu tại `%APPDATA%\AI Quiz Assistant`. `dist` chỉ phân phối duy nhất `QuizAssistant.exe`, và file này là installer chứa app executable bên trong.

## Phạm vi
- Đổi thư mục dữ liệu runtime của app frozen từ thư mục chứa `.exe` sang `%APPDATA%\AI Quiz Assistant`.
- Giữ hành vi chạy từ source như hiện tại để không làm thay đổi môi trường phát triển.
- Tài nguyên chỉ đọc vẫn lấy từ PyInstaller bundle (`_MEIPASS`); không chuyển assets vào AppData.
- Installer chỉ chép app EXE và uninstaller vào thư mục đích; không chép tài liệu mẫu/assets thừa.
- Sửa build pipeline để build app/installer vào `build/`, bảo toàn bản phát hành `dist` hiện có nếu build mới thất bại, và chỉ sau khi installer mới sẵn sàng mới cập nhật `dist` thành một file `QuizAssistant.exe`. Không giữ app EXE riêng, portable folder/ZIP/checksum trong `dist`.

## Dữ liệu đã có
Không xóa hoặc di chuyển dữ liệu khỏi thư mục cài đặt. Khi app khởi chạy và AppData chưa có mục tương ứng, app sao chép `.env`, `config.json` và `logs/` từ thư mục cài app sang AppData để giữ API key/settings/lịch sử; bản gốc được giữ lại và dữ liệu đích hiện có không bị ghi đè. Việc này áp dụng với dữ liệu cũ nằm cạnh app đã cài, không phải folder tùy ý chứa file installer vừa tải về.

## Cách tiếp cận
- Phương án A (đề xuất): đổi điểm phân giải thư mục dữ liệu dùng chung trong `src/path_utils.py`, giữ source mode và resource lookup như cũ; ít điểm thay đổi, áp dụng thống nhất cho settings/config/logs.
- Phương án B: đổi đường dẫn riêng trong từng manager; dễ sót module và tạo nhiều quy tắc khác nhau nên không chọn.
- Phương án C: dùng thư mục executable để chứa dữ liệu; không đáp ứng yêu cầu thư mục cài đặt gọn nên không chọn.

## Kiểm chứng
- Kiểm tra path frozen trỏ đúng AppData và source trỏ về repository.
- Kiểm tra tài nguyên frozen vẫn tìm trong `_MEIPASS`.
- Kiểm tra migration từ thư mục app đã cài: chỉ copy khi đích tương ứng chưa tồn tại, giữ nguồn và không ghi đè AppData.
- Kiểm tra file install chỉ gồm executable và uninstaller.
- Kiểm tra build pipeline kết thúc với duy nhất `dist/QuizAssistant.exe` (installer), có thể build lại từ đầu.
- Chạy test phù hợp; build lại installer nếu môi trường/dependencies cho phép. Không cài đè hoặc chạy installer trên hệ thống thật để tránh tác động ngoài ý muốn.

## Giới hạn
Không chuyển hoặc xóa dữ liệu hiện hữu trong thư mục cài đặt; sao chép cấu hình cũ lần đầu chỉ được làm khi đích không tồn tại. Không giữ portable release hay zip/checksum trong `dist`, vì yêu cầu là một file installer duy nhất.