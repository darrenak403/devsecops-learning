# ==========================================
# 1. KHAI BÁO BIẾN & PROVIDER
# ==========================================

variable "do_token" {
  description = "API Token lấy từ bảng điều khiển DigitalOcean"
  type        = string
  sensitive   = true
}

variable "my_ip" {
  description = "Địa chỉ IP Public của máy tính bạn đang dùng để SSH"
  type        = string
}

variable "region" {
  description = "Region triển khai hạ tầng"
  type        = string
  default     = "sgp1"
}

variable "vpc_cidr" {
  description = "Dải IP nội bộ của VPC"
  type        = string
  default     = "10.10.10.0/24"
}

variable "ssh_key_name" {
  description = "Tên SSH Key đã upload lên DigitalOcean"
  type        = string
  default     = "darrenak"
}

variable "droplet_name" {
  description = "Tên Droplet"
  type        = string
  default     = "devsecops-day-02"
}

variable "droplet_size" {
  description = "Size Droplet để tối ưu chi phí khi học"
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "droplet_image" {
  description = "Image hệ điều hành cho Droplet"
  type        = string
  default     = "ubuntu-22-04-x64"
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

data "digitalocean_ssh_key" "my_key" {
  name = var.ssh_key_name
}

resource "digitalocean_vpc" "my_vpc" {
  name     = "devsecops-vpc"
  region   = var.region
  ip_range = var.vpc_cidr
}

resource "digitalocean_droplet" "web" {
  image  = var.droplet_image
  name   = var.droplet_name
  region = var.region
  size   = var.droplet_size

  vpc_uuid = digitalocean_vpc.my_vpc.id

  ssh_keys = [data.digitalocean_ssh_key.my_key.id]

  monitoring = true

  tags = ["web-tier"]
}

resource "digitalocean_firewall" "web_firewall" {
  name = "firewall-strict-policy"

  droplet_ids = [digitalocean_droplet.web.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["${var.my_ip}/32"]
  }

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

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

output "droplet_public_ip" {
  description = "Public IP dùng để SSH hoặc truy cập web"
  value       = digitalocean_droplet.web.ipv4_address
}

output "droplet_private_ip" {
  description = "Private IP dùng để giao tiếp nội bộ trong VPC"
  value       = digitalocean_droplet.web.ipv4_address_private
}

output "vpc_id" {
  description = "ID của VPC"
  value       = digitalocean_vpc.my_vpc.id
}
