variable "cluster_name" {
  description = "Kubernetes cluster name"
  type        = string
  default     = "aeroforge-x-prod"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "region" {
  description = "Cloud region"
  type        = string
  default     = "cn-north-1"
}

variable "dr_region" {
  description = "Disaster recovery region"
  type        = string
  default     = "cn-south-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_instance_class" {
  description = "Database instance class"
  type        = string
  default     = "db.r6.xlarge"
}

variable "db_storage_size" {
  description = "Database storage size in GB"
  type        = number
  default     = 100
}

variable "minio_storage_size" {
  description = "MinIO storage size in GB"
  type        = number
  default     = 500
}

variable "k8s_node_count" {
  description = "Number of K8s worker nodes"
  type        = number
  default     = 6
}

variable "k8s_node_type" {
  description = "K8s worker node instance type"
  type        = string
  default     = "c6.2xlarge"
}

variable "backup_retention_days" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}