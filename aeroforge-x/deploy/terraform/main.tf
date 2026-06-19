terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }

  backend "s3" {
    bucket = "aeroforge-x-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "cn-north-1"
  }
}

provider "aws" {
  region = var.region
}

provider "aws" {
  alias  = "dr"
  region = var.dr_region
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.cluster_name}-vpc"
    Environment = var.environment
  }
}

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.cluster_name}-private-${count.index}"
  }
}

resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index + 3)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cluster_name}-public-${count.index}"
  }
}

resource "aws_security_group" "db" {
  name        = "${var.cluster_name}-db-sg"
  description = "Database security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  ingress {
    from_port   = 7687
    to_port     = 7687
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.cluster_name}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_rds_cluster" "postgresql" {
  cluster_identifier      = "${var.cluster_name}-pg"
  engine                  = "aurora-postgresql"
  engine_version          = "16.1"
  database_name           = "aeroforge_x"
  master_username         = "aeroforge"
  master_password         = "ChangeMe123!"
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  storage_encrypted       = true
  backup_retention_period = var.backup_retention_days
  preferred_backup_window = "03:00-04:00"
  deletion_protection     = var.environment == "production"

  tags = {
    Name = "${var.cluster_name}-postgresql"
  }
}

resource "aws_rds_cluster_instance" "pg_primary" {
  count              = 2
  identifier         = "${var.cluster_name}-pg-${count.index}"
  cluster_identifier = aws_rds_cluster.postgresql.id
  instance_class     = var.db_instance_class
  engine             = aws_rds_cluster.postgresql.engine
  engine_version     = aws_rds_cluster.postgresql.engine_version
}

resource "aws_rds_cluster" "postgresql_dr" {
  provider                = aws.dr
  cluster_identifier      = "${var.cluster_name}-pg-dr"
  engine                  = "aurora-postgresql"
  engine_version          = "16.1"
  database_name           = "aeroforge_x"
  master_username         = "aeroforge"
  master_password         = "ChangeMe123!"
  replication_source_identifier = aws_rds_cluster.postgresql.arn
  storage_encrypted       = true
  deletion_protection     = true

  tags = {
    Name = "${var.cluster_name}-postgresql-dr"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

output "postgresql_endpoint" {
  value = aws_rds_cluster.postgresql.endpoint
}

output "postgresql_reader_endpoint" {
  value = aws_rds_cluster.postgresql.reader_endpoint
}

output "vpc_id" {
  value = aws_vpc.main.id
}