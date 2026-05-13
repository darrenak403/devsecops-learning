# ==========================================
# 1. VARIABLES & PROVIDER
# ==========================================

variable "do_token" {
  description = "DigitalOcean API Token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "Region triển khai"
  type        = string
  default     = "sgp1"
}

variable "ssh_key_name" {
  description = "Tên SSH key đã upload lên DigitalOcean"
  type        = string
  default     = "darrenak"
}

variable "droplet_name" {
  description = "Tên Droplet dùng để học Terraform State"
  type        = string
  default     = "devsecops-day-03-state"
}

variable "droplet_size" {
  description = "Size nhỏ để tiết kiệm chi phí"
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "droplet_image" {
  description = "Image Ubuntu"
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

# ==========================================
# 2. DATA SOURCE - SSH KEY
# ==========================================

data "digitalocean_ssh_key" "my_key" {
  name = var.ssh_key_name
}

# ==========================================
# 3. RESOURCE - DROPLET
# ==========================================

resource "digitalocean_droplet" "state_demo" {
  name   = var.droplet_name
  region = var.region
  size   = var.droplet_size
  image  = var.droplet_image

  ssh_keys = [data.digitalocean_ssh_key.my_key.id]

  monitoring = true

  tags = ["day-03", "terraform-state"]
}

# ==========================================
# 4. OUTPUTS
# ==========================================

output "droplet_public_ip" {
  description = "Public IP của Droplet"
  value       = digitalocean_droplet.state_demo.ipv4_address
}

output "droplet_id" {
  description = "ID thật của Droplet trên DigitalOcean"
  value       = digitalocean_droplet.state_demo.id
}
