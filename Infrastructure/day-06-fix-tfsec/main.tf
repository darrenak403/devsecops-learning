
# ==========================================
# PROVIDER
# ==========================================

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

# ==========================================
# DATA SOURCE
# ==========================================

data "digitalocean_ssh_key" "my_key" {
  name = var.ssh_key_name
}

# ==========================================
# VPC
# ==========================================

resource "digitalocean_vpc" "my_vpc" {
  name     = "devsecops-vpc"
  region   = var.region
  ip_range = var.vpc_cidr
}

# ==========================================
# DROPLET
# ==========================================

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

# ==========================================
# CLOUD FIREWALL - Phiên bản khuyến nghị cho lab an toàn - đủ dùng cho server học tập
# ==========================================

resource "digitalocean_firewall" "web_firewall" {
  name = "firewall-strict-policy"

  droplet_ids = [digitalocean_droplet.web.id]

  # ==========================================
  # INBOUND RULES
  # ==========================================

  # SSH: chỉ cho phép IP cá nhân của bạn
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["${var.my_ip}/32"]
  }

  # HTTP: public vì đây là Web Server
  # tfsec có thể cảnh báo public ingress, nhưng đây là rule có chủ đích.
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # HTTPS: public vì đây là Web Server
  # Production nên ưu tiên 443 và redirect 80 -> 443.
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # ==========================================
  # OUTBOUND RULES - HARDENED
  # ==========================================

  # Cho phép server đi ra Internet qua HTTP để apt/package download khi cần
  outbound_rule {
    protocol              = "tcp"
    port_range            = "80"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Cho phép server đi ra Internet qua HTTPS để update, pull package, gọi API
  outbound_rule {
    protocol              = "tcp"
    port_range            = "443"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Cho phép DNS query qua UDP/53
  outbound_rule {
    protocol              = "udp"
    port_range            = "53"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
