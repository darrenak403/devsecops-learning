# =============================================================================
# FILE: main.tf (Ngày 2)
# Mục tiêu: Thiết lập VPC riêng và Firewall thắt chặt bảo mật
# =============================================================================

# 1. KHAI BÁO BIẾN
variable "do_token" {
  type      = string
  sensitive = true
}

# Biến chứa IP cá nhân của bạn để mở port SSH an toàn
variable "my_ip" {
  type    = string
  default = "118.69.182.144" # IP hiện tại của bạn
}

terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

# 2. LẤY SSH KEY (Đã có sẵn trên Cloud)
data "digitalocean_ssh_key" "my_key" {
  name = "darrenak"
}

# 3. THIẾT LẬP VPC (MẠNG RIÊNG)
# Tạo một "hàng rào" mạng nội bộ, tách biệt server khỏi mạng công cộng mặc định
resource "digitalocean_vpc" "my_vpc" {
  name     = "devsecops-vpc"
  region   = "sgp1"
  ip_range = "10.10.10.0/24"
}

# 4. TẠO DROPLET TRONG VPC
resource "digitalocean_droplet" "web" {
  image    = "ubuntu-22-04-x64"
  name     = "devsecops-day-02"
  region   = "sgp1"
  size     = "s-1vcpu-1gb"
  vpc_uuid = digitalocean_vpc.my_vpc.id # Gắn vào mạng riêng vừa tạo
  ssh_keys = [data.digitalocean_ssh_key.my_key.id]
}

# 5. THIẾT LẬP CLOUD FIREWALL (TƯỜNG LỬA)
resource "digitalocean_firewall" "web_firewall" {
  name = "firewall-standard-ports"

  # Gắn firewall này vào Droplet vừa tạo
  droplet_ids = [digitalocean_droplet.web.id]

  # [INBOUND] - Quy tắc chặn đường vào

  # SSH: Chỉ cho phép IP nhà bạn (An toàn tuyệt đối)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["${var.my_ip}/32"]
  }

  # HTTP/HTTPS: Mở cho toàn thế giới để khách xem web
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # [OUTBOUND] - Cho phép server đi ra ngoài internet (tải update, library)
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# 6. ĐẦU RA
output "droplet_public_ip" {
  value = digitalocean_droplet.web.ipv4_address
}
