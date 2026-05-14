# ==========================================
# OUTPUTS
# ==========================================

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

output "firewall_id" {
  description = "ID của Cloud Firewall"
  value       = digitalocean_firewall.web_firewall.id
}
