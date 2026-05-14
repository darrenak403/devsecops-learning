# 🎯 NGÀY 7: REVIEW TUẦN 1 — DỌN DẸP HẠ TẦNG & NGHỈ NGƠI

> **Chủ đề:** Week 1 Review, Terraform Cleanup, Cost Safety
>
> **Nền tảng:** DigitalOcean
>
> **Công cụ:** Terraform, Git, tfsec, Trivy
>
> **Độ khó:** 🟢 Beginner
>
> **Thư mục lưu:** `01_Terraform_Code`
>
> **Mục tiêu:** Tổng kết toàn bộ Tuần 1, kiểm tra lại hạ tầng Terraform, đảm bảo không còn tài nguyên DigitalOcean gây tốn phí, commit code sạch, lưu troubleshooting, và nghỉ ngơi trước khi bước sang Tuần 2 Docker Security.

---

# 🎯 Kết Quả Cần Đạt Sau Bài Học

Sau bài này, tôi có thể:

- [ ] Review lại toàn bộ nội dung Tuần 1.
- [ ] Biết kiểm tra Terraform đang quản lý resource nào.
- [ ] Biết chạy `terraform destroy` an toàn.
- [ ] Biết xác nhận hạ tầng đã được xóa thật.
- [ ] Biết kiểm tra Git không track file nhạy cảm.
- [ ] Biết tổng kết lỗi đã gặp trong tuần.
- [ ] Biết chuẩn bị tinh thần và folder cho Tuần 2 Docker Security.
- [ ] Nghỉ ngơi mà không lo DigitalOcean tiếp tục tính phí.

---

# ✅ Yêu Cầu Trước Khi Bắt Đầu

Trước khi review Ngày 7, cần đảm bảo:

- [ ] Đã học Ngày 1: Terraform basic và tạo Droplet đầu tiên.
- [ ] Đã học Ngày 2: VPC & Cloud Firewall.
- [ ] Đã học Ngày 3: Terraform State.
- [ ] Đã học Ngày 4: Refactor `main.tf` thành `variables.tf`, `outputs.tf`.
- [ ] Đã học Ngày 5: Cài và chạy `tfsec`.
- [ ] Đã học Ngày 6: Fix/harden firewall rules theo cảnh báo scanner.
- [ ] Đang đứng trong đúng thư mục Terraform cần dọn dẹp.

Kiểm tra thư mục hiện tại:

```bash
pwd
ls -la
```

---

# 🧠 1. Tư Duy Ngày 7

## 🎭 Ẩn dụ: Rời công trường phải tắt điện, khóa cửa, dọn dụng cụ

Tuần 1 giống như bạn vừa xây xong một công trường nhỏ:

- Terraform code là bản thiết kế.
- Droplet là căn nhà thật.
- VPC là khu đất riêng.
- Firewall là cổng bảo vệ.
- tfsec/Trivy là đội kiểm tra an ninh.
- Terraform State là hồ sơ quản lý công trình.

Ngày 7 là lúc bạn không xây thêm gì mới.

Ngày 7 là lúc:

```text
Kiểm tra lại
Dọn dẹp
Ghi chép
Khóa cửa
Nghỉ ngơi
```

Trong DevSecOps, biết tạo hạ tầng là chưa đủ.  
Phải biết **xóa đúng, xóa sạch, và kiểm tra lại sau khi xóa**.

---

# 💥 2. Vì Sao Ngày 7 Quan Trọng?

Nếu không review và destroy tài nguyên, bạn có thể gặp các vấn đề:

| ❌ Vấn đề                      | 🚨 Hậu quả                |
| ------------------------------ | ------------------------- |
| Quên destroy Droplet           | Tiếp tục bị tính phí      |
| Quên Firewall/VPC              | Hạ tầng rác tồn tại       |
| Commit nhầm `terraform.tfvars` | Lộ token                  |
| Commit nhầm `.tfstate`         | Lộ thông tin hạ tầng      |
| Không ghi lỗi đã gặp           | Tuần sau gặp lại lỗi cũ   |
| Không nghỉ                     | Dễ burnout, học không bền |

DigitalOcean tính phí khi tài nguyên còn tồn tại, kể cả nếu bạn chỉ power off Droplet; nguyên tắc học của bạn là học xong thì dùng `terraform destroy` để dọn dẹp.

---

# 🏗️ 3. Review Nội Dung Tuần 1

## Ngày 1 — Terraform Basic

Tôi đã học:

- `provider` là gì.
- `resource` là gì.
- `terraform init`, `plan`, `apply`, `destroy`.
- Terraform dùng code để tạo hạ tầng thay vì click tay.

Checklist:

- Chạy được `terraform init`.
- Chạy được `terraform plan`.
- Chạy được `terraform apply`.
- Chạy được `terraform destroy`.

---

## Ngày 2 — VPC & Cloud Firewall

Tôi đã học:

- VPC là mạng riêng.
- CIDR như `10.10.10.0/24` là dải IP private tự quy hoạch.
- Inbound là traffic đi vào server.
- Outbound là traffic đi ra khỏi server.
- Cloud Firewall nằm ngoài server, khác với UFW trong OS.
- Chỉ mở port cần thiết: `22`, `80`, `443`.

Checklist:

- Hiểu VPC là gì.
- Hiểu CIDR `/24` là gì.
- Hiểu inbound/outbound.
- SSH `22` chỉ mở cho IP cá nhân.
- Web `80/443` có thể public nếu là web server.
- Port lạ như `3000` bị chặn.

Cloud Firewall là phần quan trọng của Ngày 2: nó bảo vệ ở tầng cloud, quản lý tập trung và không phụ thuộc vào OS bên trong server.

---

## Ngày 3 — Terraform State

Tôi đã học:

- `.tfstate` là bộ nhớ của Terraform.
- Terraform dùng state để biết resource nào đang được quản lý.
- Không được commit `.tfstate`.
- Có thể xem state bằng:

```bash
terraform state list
terraform state show <resource>
```

Checklist:

- Hiểu `terraform.tfstate`.
- Biết `terraform state list`.
- Biết `terraform state show`.
- Biết vì sao không commit state.
- Biết backup state trước thao tác nguy hiểm.

---

## Ngày 4 — Refactor Terraform Code

Tôi đã học:

- Tách code thành:
  - `main.tf`
  - `variables.tf`
  - `outputs.tf`
  - `terraform.tfvars`
- Terraform tự đọc tất cả file `.tf` trong cùng folder.
- Không đổi tên resource nếu chỉ muốn refactor.
- `terraform.tfvars` không được commit.

Checklist:

- Có `main.tf`.
- Có `variables.tf`.
- Có `outputs.tf`.
- Có `terraform.tfvars`.
- `.gitignore` đã ignore `terraform.tfvars`.
- Chạy `terraform validate` pass.

---

## Ngày 5 — tfsec / Trivy Scan

Tôi đã học:

- `tfsec .` dùng để quét lỗi bảo mật Terraform.
- `trivy config .` cũng có thể quét IaC.
- Scanner báo public ingress/egress khi thấy `0.0.0.0/0`.
- Không phải cảnh báo nào cũng fix máy móc.
- Cần đọc theo ngữ cảnh.

Checklist:

- Cài được `tfsec`.
- Cài được `trivy`.
- Chạy được `tfsec .`.
- Chạy được `trivy config .`.
- Biết đọc severity.
- Biết export report vào `reports/`.

---

## Ngày 6 — Fix Firewall Rules

Tôi đã học:

- SSH public là lỗi cần fix.
- HTTP/HTTPS public có thể chấp nhận nếu là web server.
- Outbound `1-65535` quá rộng.
- Có thể harden outbound còn:
  - TCP `80`
  - TCP `443`
  - UDP `53`
- Cảnh báo còn lại cần ghi “accept có lý do”.

Checklist:

- SSH chỉ mở cho `my_ip/32`.
- Port `80/443` public có lý do.
- Outbound không còn `1-65535`.
- Có report before/after.
- Có bảng quyết định xử lý cảnh báo.

---

# 🚀 4. Quy Trình Review & Dọn Dẹp Ngày 7

## Bước 1: Vào đúng thư mục Terraform

Ví dụ:

```bash
cd ~/Documents/CODE/2.\ Study/DevSecOps-30-days/Infrastructure/day-06-fix-firewall-rules
```

Kiểm tra:

```bash
pwd
ls -la
```

Cần thấy các file:

```text
main.tf
variables.tf
outputs.tf
terraform.tfvars
.terraform/
terraform.tfstate
```

---

## Bước 2: Kiểm tra Terraform đang quản lý gì

Chạy:

```bash
terraform state list
```

Kết quả có thể thấy:

```text
data.digitalocean_ssh_key.my_key
digitalocean_vpc.my_vpc
digitalocean_droplet.web
digitalocean_firewall.web_firewall
```

Ý nghĩa:

```text
Terraform đang quản lý VPC, Droplet, Firewall.
Nếu destroy, Terraform sẽ xóa các resource này.
```

---

## Bước 3: Xem lại hạ tầng trước khi xóa

Chạy:

```bash
terraform plan
```

Mục đích:

- Đảm bảo code hiện tại khớp state.
- Kiểm tra có thay đổi bất thường không.
- Tránh destroy nhầm folder/project.

Nếu chỉ muốn xem kế hoạch destroy, chạy:

```bash
terraform plan -destroy
```

Kết quả mong muốn:

```text
Plan: 0 to add, 0 to change, 3 to destroy.
```

---

## Bước 4: Destroy hạ tầng

Chạy:

```bash
terraform destroy
```

Terraform sẽ hỏi:

```text
Do you really want to destroy all resources?
```

Nhập:

```text
yes
```

Kết quả mong muốn:

```text
Destroy complete! Resources: 3 destroyed.
```

Bạn đã từng có log destroy thành công với `digitalocean_firewall`, `digitalocean_droplet`, và `digitalocean_vpc`, kết thúc bằng `Destroy complete! Resources: 3 destroyed.`

---

## Bước 5: Kiểm tra lại sau khi destroy

Chạy:

```bash
terraform state list
```

Nếu không còn resource managed, Terraform có thể không in gì hoặc chỉ còn data source tùy trạng thái.

Chạy tiếp:

```bash
terraform plan
```

Nếu Terraform báo:

```text
Plan: 3 to add, 0 to change, 0 to destroy.
```

nghĩa là hạ tầng thật đã bị xóa, và nếu muốn dựng lại thì Terraform sẽ tạo mới từ đầu.

---

## Bước 6: Kiểm tra trên DigitalOcean Dashboard

Vào DigitalOcean Dashboard và kiểm tra:

- Droplets
- Networking → Firewalls
- Networking → VPC

Mục tiêu:

```text
Không còn Droplet/VPC/Firewall lab nào đang chạy ngoài ý muốn.
```

Nếu còn resource lạ:

- Kiểm tra có phải Terraform quản lý không.
- Không xóa bừa nếu chưa chắc.
- Nếu chắc là lab cũ, xóa để tránh phí.

---

# 🧪 5. Lab Review Ngày 7

## Lab 1 — Xác nhận destroy an toàn

### Mục tiêu

Hiểu `destroy` xóa đúng resource Terraform đang quản lý.

### Lệnh

```bash
terraform state list
terraform plan -destroy
terraform destroy
```

### Kết quả mong muốn

```text
Destroy complete! Resources: ... destroyed.
```

---

## Lab 2 — Kiểm tra không còn phí tài nguyên

### Mục tiêu

Đảm bảo không còn Droplet gây tốn tiền.

### Cách làm

Kiểm tra trên DigitalOcean Dashboard:

```text
Droplets
Networking → Firewalls
Networking → VPC
```

### Kết quả mong muốn

Không còn resource lab Tuần 1.

---

## Lab 3 — Kiểm tra Git sạch

### Mục tiêu

Đảm bảo không commit file nhạy cảm.

### Lệnh

```bash
git status
```

Không được thấy các file này trong staged/unstaged để commit:

```text
terraform.tfvars
terraform.tfstate
terraform.tfstate.backup
.terraform/
reports/*.json nếu có secret
```

Nếu thấy state hoặc tfvars bị track:

```bash
git rm --cached terraform.tfvars
git rm --cached terraform.tfstate
git rm --cached terraform.tfstate.backup
```

Sau đó kiểm tra `.gitignore`.

---

## Lab 4 — Kiểm tra scanner report

### Mục tiêu

Đảm bảo report Ngày 5/6 đã được lưu.

Kiểm tra:

```bash
ls -la reports
```

Nên có:

```text
tfsec-before.txt
tfsec-after.txt
trivy-before.txt
trivy-after.txt
```

Không bắt buộc đủ hết, nhưng nên có ít nhất report sau scan.

---

# 📁 6. Ghi Chú Obsidian Cần Tạo

Tạo file:

```text
01_Terraform_Code/Day_07_Week_1_Review.md
```

Nội dung nên có:

````md
# Day 07 - Week 1 Review

## 1. Tôi đã học được gì?

- Terraform basic
- VPC & Cloud Firewall
- Terraform State
- Refactor code Terraform
- tfsec / Trivy scan
- Fix firewall rules

## 2. Lỗi đã gặp trong tuần

| Ngày   | Lỗi                                   | Nguyên nhân                      | Cách fix                |
| ------ | ------------------------------------- | -------------------------------- | ----------------------- |
| Ngày 2 | Firewall tag `web-tier` không tồn tại | Dùng tag attach firewall chưa ổn | Đổi sang `droplet_ids`  |
| Ngày 2 | SSH timeout                           | `my_ip` không khớp IP hiện tại   | Cập nhật `my_ip`        |
| Ngày 5 | tfsec báo public ingress/egress       | `0.0.0.0/0`                      | Phân tích theo ngữ cảnh |
| Ngày 6 | Trivy vẫn báo 80/443 public           | Web server cần public            | Accept có lý do         |

## 3. Resource đã destroy chưa?

```bash
terraform destroy
```
````

Kết quả:

```text
Destroy complete! Resources: ... destroyed.
```

## 4. Checklist bảo mật

- Không commit `terraform.tfvars`
- Không commit `.tfstate`
- SSH không mở public
- Firewall rule có lý do
- Reports đã lưu
- DigitalOcean không còn resource lab

## 5. Chuẩn bị cho Tuần 2

Tuần 2 sẽ học Docker Security:

- Dockerfile cơ bản
- Multi-stage build
- Alpine image
- Non-root user
- Trivy image scan

````

Theo quy tắc quản lý học tập của bạn, các file code và bài học Terraform nằm trong `01_Terraform_Code`, còn lỗi thực hành nên ghi vào `04_Troubleshooting`. :contentReference[oaicite:4]{index=4}

---

# 🛡️ 7. Security Best Practices Review

## Những điều đã làm đúng trong Tuần 1

- Không click tay tạo hạ tầng.
- Dùng Terraform để tạo Droplet/VPC/Firewall.
- SSH chỉ mở cho IP cá nhân.
- Không commit token vào Git.
- Không commit `.tfstate`.
- Dùng `tfsec` và `trivy config`.
- Có tư duy accept risk có lý do.
- Biết destroy tài nguyên khi học xong.

---

## Những điều cần tiếp tục giữ

| Thói quen | Lý do |
|---|---|
| Luôn chạy `terraform plan` trước `apply` | Tránh tạo/xóa nhầm |
| Không dùng `apply -auto-approve` khi học | Có thời gian đọc plan |
| Luôn destroy sau buổi học | Tránh tốn tiền |
| Không paste token thật | Tránh lộ cloud account |
| Ghi lỗi vào Troubleshooting | Lần sau không bị lại |
| Scan trước khi apply | Shift-left security |

---

# ⚡ 8. Cost Cleanup

Ngày 7 là ngày quan trọng nhất về chi phí.

Lệnh sống còn:

```bash
terraform destroy
````

Sau khi destroy, phải kiểm tra:

```bash
terraform state list
terraform plan
```

Và kiểm tra thêm trên DigitalOcean Dashboard.

Ghi nhớ:

```text
Power Off không phải là dừng chi phí hoàn toàn.
Destroy mới là dọn tài nguyên thật sự.
```

Nguyên tắc quản lý chi phí của bạn là học xong hoặc rời bàn làm việc thì destroy, hôm sau apply lại nếu cần học tiếp.

---

# 🧯 9. Troubleshooting Review

## Lỗi 1: `terraform destroy` báo không có resource

### Nguyên nhân

Có thể bạn đang ở sai folder hoặc state không còn resource.

### Kiểm tra

```bash
pwd
terraform state list
```

Nếu đang sai folder, quay lại đúng thư mục Terraform.

---

## Lỗi 2: DigitalOcean vẫn còn Droplet sau destroy

### Nguyên nhân

Droplet đó có thể được tạo từ folder Terraform khác, hoặc tạo tay trên Dashboard.

### Cách xử lý

- Kiểm tra tên Droplet.
- Tìm folder Terraform tương ứng.
- Nếu chắc chắn là lab cũ, xóa thủ công hoặc import vào Terraform rồi destroy.

---

## Lỗi 3: `git status` thấy `terraform.tfvars`

### Nguyên nhân

`.gitignore` chưa đúng hoặc file đã bị Git track trước đó.

### Cách sửa

```bash
git rm --cached terraform.tfvars
```

Thêm vào `.gitignore`:

```gitignore
*.tfvars
terraform.tfvars
```

---

## Lỗi 4: Destroy nhầm hạ tầng

### Phòng tránh

Trước khi destroy luôn chạy:

```bash
terraform state list
terraform plan -destroy
```

Chỉ nhập `yes` khi chắc chắn resource đúng là lab cần xóa.

---

# 🧠 10. DevSecOps Mindset

Ngày 7 không phải ngày “không học gì”.

Ngày 7 là ngày học một kỹ năng cực kỳ quan trọng:

```text
Operational discipline
```

Tức là kỷ luật vận hành.

Một người DevSecOps không chỉ biết tạo hạ tầng.

Một người DevSecOps giỏi phải biết:

- Tạo hạ tầng bằng code
- Kiểm tra hạ tầng bằng scanner
- Đọc cảnh báo bảo mật
- Ghi nhận quyết định
- Xóa hạ tầng đúng cách
- Không để chi phí và secret bị mất kiểm soát

---

# 🏆 11. Thành Quả Sau Tuần 1

Sau Tuần 1, bạn đã có nền tảng:

- Terraform basic
- DigitalOcean provider
- VPC private network
- Cloud Firewall
- Terraform State
- Refactor Terraform code
- tfsec scan
- Trivy config scan
- Firewall hardening
- Cost cleanup bằng `terraform destroy`

Đây chính là nền tảng để bước sang Tuần 2: **Docker Security**.

Roadmap Tuần 2 của bạn sẽ bắt đầu bằng Dockerfile cơ bản cho .NET và Next.js, rồi đi tiếp multi-stage build, Alpine image, non-root user và Trivy image scan.

---

# 📌 Checklist Cuối Ngày 7

- Đã đứng đúng thư mục Terraform.
- Đã chạy `terraform state list`.
- Đã chạy `terraform plan -destroy`.
- Đã chạy `terraform destroy`.
- Đã nhập `yes` để xác nhận.
- Đã thấy `Destroy complete`.
- Đã kiểm tra DigitalOcean Dashboard.
- Không còn Droplet lab đang chạy.
- Không còn Firewall/VPC lab không cần thiết.
- Đã chạy `git status`.
- Không có `terraform.tfvars` bị track.
- Không có `.tfstate` bị track.
- Đã lưu report tfsec/Trivy.
- Đã ghi lỗi quan trọng vào `04_Troubleshooting`.
- Đã tạo note `Day_07_Week_1_Review.md`.
- Đã nghỉ ngơi.

---

# 🏁 Kết Thúc Ngày 7

> “Tạo được hạ tầng là kỹ năng.  
> Dọn được hạ tầng sạch sẽ là kỷ luật.  
> Ghi lại được bài học là trưởng thành.”

```

Gợi ý: hôm nay bạn **không cần viết thêm Terraform code mới**. Việc quan trọng nhất là **review, destroy, kiểm tra Git sạch, kiểm tra DigitalOcean sạch, rồi nghỉ**.
```
