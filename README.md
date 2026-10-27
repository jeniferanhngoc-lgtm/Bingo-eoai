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

Repo triển khai có thể để cấu trúc phẳng: `app.py`, `core.py`, `catalog.json`, `bingo.css`, `requirements.txt`, `BASIC-LICENSE.txt`, `README.md`. Cấu trúc thư mục đầy đủ với `data/catalog.json` và `assets/bingo.css` cũng được hỗ trợ.

## Dữ liệu

Đã lập danh mục từ hai ZIP do chủ ứng dụng cung cấp:

- 88 bài Reading, 51 bài Listening.
- 51 bài có khóa chấm tự động đủ 40 câu; các bài khác hiển thị rõ số câu có thể chấm, không tính band toàn bài nếu thiếu khóa.
- 40 bài Listening có audio; bài chưa có audio được gắn cảnh báo.
- Nhiều bài chỉ có audio một số phần. Bingo hiển thị các phần còn thiếu theo tên file và sắp xếp bản ghi theo số phần.
- Một số PDF chứa cả Listening và Reading: chọn đúng trang/phần theo kỹ năng.
- Giữ nguyên file đề, đáp án và lời giải. Chưa chuyển mọi câu hỏi thành dạng tương tác trực tiếp trong văn bản; trả lời bằng phiếu bên cạnh.
- Đáp án được trích tự động, chưa được giáo viên kiểm định. Luôn có tài liệu gốc để đối chiếu. Band chỉ là tham khảo; bảng Reading áp dụng cho Academic.
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

Giao diện thích nghi từ **Basic** của [WebThemez](https://webthemez.com/), giấy phép CC BY 3.0; backlink được giữ ở chân trang. Xem `assets/BASIC-LICENSE.txt` (hoặc `BASIC-LICENSE.txt` ở bản triển khai). Không sử dụng ảnh demo của template. Không tải Bootstrap/jQuery cũ vào ứng dụng Streamlit.
