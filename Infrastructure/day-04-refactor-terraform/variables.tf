# ==========================================
# VARIABLES
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
  default     = "devsecops-day-04"
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
