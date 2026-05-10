# --- 1. KHAI BÁO BIẾN ---
variable "do_token" {
  type      = string
  sensitive = true
}

# --- 2. CẤU HÌNH PROVIDER ---
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

# --- 3. KẾT NỐI SSH KEY ---
# Data source giúp Terraform tìm ID của Key đã có sẵn trên Web
data "digitalocean_ssh_key" "my_key" {
  name = "darrenak" # Khớp 100% với tên bạn đặt trên Web
}

# --- 4. KHỞI TẠO DROPLET (VPS) ---
resource "digitalocean_droplet" "web" {
  image    = "ubuntu-22-04-x64"
  name     = "devsecops-day-01"
  region   = "sgp1"        # Singapore (Gần Việt Nam nhất)
  size     = "s-1vcpu-1gb" # Gói rẻ nhất ($6/tháng)
  ssh_keys = [data.digitalocean_ssh_key.my_key.id]

  tags = ["learning", "day1"]
}

# --- 5. HIỂN THỊ KẾT QUẢ ---
output "droplet_ip" {
  value = digitalocean_droplet.web.ipv4_address
}
