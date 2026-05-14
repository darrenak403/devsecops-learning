
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
# CLOUD FIREWALL
# ==========================================

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
