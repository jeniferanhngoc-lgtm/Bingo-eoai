# Bingo · IELTS Listening & Reading

Ứng dụng Streamlit dùng cá nhân, có màn hình mật khẩu, kho đề theo VOL, xem PDF/Word có hình, nghe audio, phiếu trả lời 40 câu, hẹn giờ, chấm điểm, lịch sử và sao lưu JSON.

## Chạy trên máy

Python 3.12 hoặc mới hơn:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Tạo `.streamlit/secrets.toml` theo `secrets.toml.example`. Ứng dụng yêu cầu `BINGO_PASSWORD`, không có mật khẩu mặc định công khai. Không đưa secrets lên GitHub.

## Triển khai Streamlit Community Cloud

1. Đưa các file mã nguồn lên repository `jeniferanhngoc-lgtm/Bingo-eoai`, nhánh `main`.
2. Tại https://share.streamlit.io/, chọn **Create app**, repository trên, branch `main`, main file `app.py`.
3. Trong **Advanced settings**, chọn Python 3.12 và nhập các trường dưới đây vào **Secrets**. Giá trị thật nằm trong file `.streamlit/secrets.toml` trên máy chủ sở hữu ứng dụng; không commit file này.

```toml
BINGO_PASSWORD = "your-own-password"
DATA_REPOSITORY = "jeniferanhngoc-lgtm/Bingo-eoai"
DATA_RELEASE = "bingo-data-v1"
DATA_KEY = "key-generated-by-pack-data"
```

4. Đưa toàn bộ file `.bingo` đã mã hóa từ `data/packs/` lên **GitHub Releases**, tag `bingo-data-v1`. Chúng là file đính kèm release, không phải file trong nhánh Git. Nếu repo public, không cần GitHub token. Nếu repo private, thêm `GITHUB_TOKEN` chỉ có quyền đọc Contents của repo này.
5. Deploy. Mở web, đăng nhập rồi chọn bài. Ứng dụng chỉ tải gói dữ liệu của bài đang xem và lưu cache trên ổ đĩa máy chủ.

Giữ nguyên cấu trúc thư mục của repo khi triển khai. Giao diện dùng `assets/dreamy/`, catalog ở `data/catalog.json`, và trình highlight dùng `reader.py` cùng `components/reader/index.html`. Không chỉ tải riêng app.py.

## Dữ liệu

Đã lập danh mục từ hai ZIP do chủ ứng dụng cung cấp:

- 88 bài Reading, 58 bài Listening.
- 56 bài có khóa chấm tự động đủ 40 câu; các bài khác hiển thị rõ số câu có thể chấm, không tính band toàn bài nếu thiếu khóa.
- 57 bài Listening có audio; bài chưa có audio được gắn cảnh báo.
- Nhiều bài chỉ có audio một số phần. Bingo hiển thị các phần còn thiếu theo tên file và sắp xếp bản ghi theo số phần.
- Một số PDF chứa cả Listening và Reading: chọn đúng trang/phần theo kỹ năng.
- Giữ nguyên file đề, đáp án và lời giải. Chưa chuyển mọi câu hỏi thành dạng tương tác trực tiếp trong văn bản; trả lời bằng phiếu bên cạnh.
- Đáp án được trích tự động, chưa được giáo viên kiểm định. Luôn có tài liệu gốc để đối chiếu. Band chỉ là tham khảo; bảng Reading áp dụng cho Academic.
- Tham khảo bảng điểm trung bình của [IDP Listening](https://ielts.idp.com/vietnam/results/scores/listening/en-gb) và [IELTS scoring](https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail); ngưỡng thực tế có thể thay đổi theo phiên bản đề.
- Các file WMA có nút tải xuống vì hỗ trợ trình duyệt không đồng nhất.

Chỉ chủ ứng dụng được cung cấp tài liệu có quyền sử dụng. Giấy phép giao diện không cấp quyền với đề thi/audio.

## Nhập lại tài liệu và tạo gói dữ liệu

Trong bản mã nguồn đầy đủ trên máy:

```sh
python scripts/import_materials.py /path/Reading.zip /path/Listening.zip
python scripts/pack_data.py
python -m unittest discover -s tests -v
```

`data/local_sources.json` trỏ đến ZIP trên máy và được gitignore. File gốc không bị thay đổi. `pack_data.py` tạo khóa AES-256-GCM một lần trong secrets, sau đó tạo gói theo từng bài. Giữ bản sao khóa ở nơi riêng tư; mất khóa thì phải đóng gói và tải lại dữ liệu. Không công khai `.streamlit/secrets.toml`, `.bingo/`, ZIP gốc hoặc gói dữ liệu chưa mã hóa.

## Tiến độ và hẹn giờ

Câu trả lời tự lưu sau khi rời ô nhập. Đồng hồ cần bấm Bắt đầu; có thể tạm dừng khi luyện. Hết giờ tự nộp khi trang đang mở. Nếu đóng trang lúc đồng hồ đang chạy, thời gian vẫn trôi.

Ứng dụng dành cho một người, tiến độ nằm trong `.bingo/progress.json`. Streamlit Cloud có ổ đĩa tạm: lịch sử có thể mất sau khi reboot/redeploy. Dùng **Sao lưu & hướng dẫn → Tải bản sao lưu** sau buổi học và khôi phục khi cần. Không có cơ sở dữ liệu đồng bộ nhiều thiết bị.

## Giao diện và ghi công

Giao diện hiện tại thích nghi từ **Dreamy / Ginger Ninja!** của [Donny Burnside](http://www.ginger-ninja.net/). Banner bầu trời, nền xanh và thanh menu xanh lá lấy từ mẫu Dreamy, được điều chỉnh để dùng trên Streamlit và màn hình nhỏ. Phần giao diện phái sinh được phân phối theo giấy phép Attribution–ShareAlike kèm mẫu; xem `assets/DREAMY-LICENSE.txt` và bản CSS gốc trong `assets/dreamy/original.css`. Ghi công được giữ ở chân trang. Tài nguyên Basic trước đây được lưu lại kèm giấy phép gốc, nhưng không còn được tải vào giao diện.

## Bổ sung audio ngày 28/10/2026

- VOL 7: Test 1–11 có bản ghi đầy đủ của bài.
- VOL 8: Test 1–8 có bản ghi đầy đủ của bài.
- VOL 5 Test 2: đủ phần 1–4; WMA phần 3 được chuyển thành MP3 để phát trên trình duyệt.
- Gói bổ sung dùng tên có mã nội dung; cache và các gói cũ không bị ghi đè. App tải đúng tên gói trong thuộc tính `pack` của catalog. Khóa giải mã giữ nguyên.
- `scripts/supplement_materials.py` thực hiện ghép theo VOL/Test; `scripts/convert_wma.py` dùng gói phát triển imageio-ffmpeg để chuyển audio; `scripts/pack_data.py --test <id> --refresh` tạo bản gói mới. ZIP nguồn không bị thay đổi.

## Highlight bài đọc và câu hỏi

- Word: bôi chọn bất kỳ đoạn chữ nào trong bài hoặc câu hỏi, chọn màu, bấm **Tô đoạn đã chọn**.
- PDF: chọn trang rồi kéo vùng highlight trên trang gốc, kể cả bản scan và hình/sơ đồ. Với PDF có chữ, có thể đổi sang **Văn bản · bôi chọn chữ**.
- Có bốn màu, xóa từng nét, hoàn tác và xóa hết highlight trên trang/tài liệu đang xem.
- Dấu tô được lưu theo tài liệu và trang trong tiến độ và file sao lưu JSON. Trình duyệt giữ thêm bản localStorage và tự khôi phục bản mới hơn nếu cloud reboot. Chuyển trình duyệt hoặc xóa dữ liệu trình duyệt cần dùng bản sao lưu để khôi phục.
- Khi đổi kiểu xem PDF, dấu tô vùng và dấu tô chữ được lưu riêng để tọa độ không bị sai lệch.
