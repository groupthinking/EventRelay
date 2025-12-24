# ============================================
# UVAI YouTube Extension - Production Infrastructure
# ============================================

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    fly = {
      source  = "fly-apps/fly"
      version = "~> 0.0.20"
    }
    vercel = {
      source  = "vercel/vercel"
      version = "~> 0.11.4"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
  
  backend "s3" {
    bucket         = "uvai-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

# ============================================
# Providers Configuration
# ============================================

provider "fly" {
  fly_api_token = var.fly_api_token
}

provider "vercel" {
  api_token = var.vercel_api_token
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

provider "aws" {
  region = var.aws_region
}

# ============================================
# Variables
# ============================================

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "uvai-youtube-extension"
}

variable "fly_api_token" {
  description = "Fly.io API token"
  type        = string
  sensitive   = true
}

variable "vercel_api_token" {
  description = "Vercel API token"
  type        = string
  sensitive   = true
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token"
  type        = string
  sensitive   = true
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "database_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
}

# ============================================
# Local Values
# ============================================

locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    CreatedAt   = timestamp()
  }
  
  app_name = "${var.project_name}-${var.environment}"
}

# ============================================
# Random Resources
# ============================================

resource "random_password" "redis_password" {
  length  = 32
  special = true
}

resource "random_password" "rabbitmq_password" {
  length  = 32
  special = true
}

# ============================================
# Fly.io Backend Application
# ============================================

module "fly_backend" {
  source = "../../modules/fly-app"
  
  app_name     = "${local.app_name}-backend"
  organization = "uvai"
  region       = "iad"
  
  environment_variables = {
    APP_ENV            = var.environment
    DATABASE_URL       = module.database.connection_string
    REDIS_URL          = module.redis.connection_string
    JWT_SECRET_KEY     = var.jwt_secret_key
    OPENAI_API_KEY     = var.openai_api_key
    ANTHROPIC_API_KEY  = var.anthropic_api_key
    SENTRY_DSN         = module.monitoring.sentry_dsn
  }
  
  services = {
    internal_port = 8000
    protocol      = "tcp"
    
    ports = [{
      port     = 443
      handlers = ["tls", "http"]
    }]
    
    tcp_checks = [{
      interval = "30s"
      timeout  = "10s"
    }]
    
    http_checks = [{
      interval = "30s"
      timeout  = "10s"
      path     = "/health"
    }]
  }
  
  scaling = {
    min_machines = 3
    max_machines = 10
    
    metrics = {
      cpu_threshold     = 70
      memory_threshold  = 80
      request_threshold = 1000
    }
  }
  
  resources = {
    cpu    = 2
    memory = "2GB"
  }
  
  tags = local.common_tags
}

# ============================================
# Fly.io Orchestrator Application
# ============================================

module "fly_orchestrator" {
  source = "../../modules/fly-app"
  
  app_name     = "${local.app_name}-orchestrator"
  organization = "uvai"
  region       = "iad"
  
  environment_variables = {
    APP_ENV           = var.environment
    DATABASE_URL      = module.database.connection_string
    REDIS_URL         = module.redis.connection_string
    RABBITMQ_URL      = module.rabbitmq.connection_string
    OPENAI_API_KEY    = var.openai_api_key
    ANTHROPIC_API_KEY = var.anthropic_api_key
  }
  
  services = {
    internal_port = 8001
    protocol      = "tcp"
    
    ports = [{
      port     = 443
      handlers = ["tls", "http"]
    }]
    
    http_checks = [{
      interval = "30s"
      timeout  = "10s"
      path     = "/health"
    }]
  }
  
  scaling = {
    min_machines = 2
    max_machines = 5
    
    metrics = {
      cpu_threshold     = 80
      memory_threshold  = 85
      request_threshold = 500
    }
  }
  
  resources = {
    cpu    = 4
    memory = "4GB"
  }
  
  tags = local.common_tags
}

# ============================================
# Database Infrastructure
# ============================================

module "database" {
  source = "../../modules/database"
  
  environment = var.environment
  project     = var.project_name
  
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 100
  max_allocated_storage = 500
  storage_encrypted     = true
  
  database_name = "uvai_production"
  username      = "uvai_admin"
  password      = var.database_password
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  multi_az               = true
  deletion_protection    = true
  skip_final_snapshot    = false
  
  performance_insights_enabled = true
  monitoring_interval         = 60
  
  tags = local.common_tags
}

# ============================================
# Redis Cache
# ============================================

module "redis" {
  source = "../../modules/redis"
  
  environment = var.environment
  project     = var.project_name
  
  node_type       = "cache.t3.medium"
  num_cache_nodes = 3
  
  engine_version = "7.0"
  port          = 6379
  
  parameter_group_family = "redis7"
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                = random_password.redis_password.result
  
  tags = local.common_tags
}

# ============================================
# RabbitMQ Message Queue
# ============================================

module "rabbitmq" {
  source = "../../modules/rabbitmq"
  
  environment = var.environment
  project     = var.project_name
  
  instance_type = "mq.m5.large"
  
  engine_version = "3.12"
  
  username = "admin"
  password = random_password.rabbitmq_password.result
  
  deployment_mode = "CLUSTER_MULTI_AZ"
  
  maintenance_window = "sun:04:00-sun:05:00"
  
  tags = local.common_tags
}

# ============================================
# S3 Storage
# ============================================

module "storage" {
  source = "../../modules/s3"
  
  environment = var.environment
  project     = var.project_name
  
  buckets = {
    uploads = {
      name = "${local.app_name}-uploads"
      acl  = "private"
      
      lifecycle_rules = [{
        id      = "delete-old-uploads"
        enabled = true
        
        expiration = {
          days = 90
        }
        
        transition = [{
          days          = 30
          storage_class = "STANDARD_IA"
        }]
      }]
    }
    
    backups = {
      name = "${local.app_name}-backups"
      acl  = "private"
      
      lifecycle_rules = [{
        id      = "archive-old-backups"
        enabled = true
        
        transition = [{
          days          = 7
          storage_class = "GLACIER"
        }]
        
        expiration = {
          days = 365
        }
      }]
    }
    
    static = {
      name = "${local.app_name}-static"
      acl  = "public-read"
      
      website = {
        index_document = "index.html"
        error_document = "error.html"
      }
    }
  }
  
  enable_versioning = true
  enable_encryption = true
  
  tags = local.common_tags
}

# ============================================
# Vercel Frontend Deployment
# ============================================

module "vercel_frontend" {
  source = "../../modules/vercel"
  
  project_name = "${local.app_name}-frontend"
  framework    = "nextjs"
  
  git_repository = {
    type = "github"
    repo = "uvai/youtube-extension"
    ref  = "main"
  }
  
  build_command   = "npm run build"
  output_directory = ".next"
  install_command = "npm ci"
  
  environment_variables = {
    NEXT_PUBLIC_API_URL = "https://api.${module.cloudflare_dns.domain}"
    NEXT_PUBLIC_WS_URL  = "wss://api.${module.cloudflare_dns.domain}"
    NEXT_PUBLIC_GA_ID   = module.monitoring.google_analytics_id
  }
  
  domains = [
    module.cloudflare_dns.domain,
    "www.${module.cloudflare_dns.domain}"
  ]
  
  functions = {
    "api/auth/[...nextauth].js" = {
      maxDuration = 30
    }
  }
}

# ============================================
# Cloudflare DNS & CDN
# ============================================

module "cloudflare_dns" {
  source = "../../modules/cloudflare"
  
  zone_id = var.cloudflare_zone_id
  domain  = "uvai-youtube.com"
  
  dns_records = [
    {
      name    = "@"
      type    = "A"
      value   = module.fly_backend.ip_address
      proxied = true
    },
    {
      name    = "www"
      type    = "CNAME"
      value   = module.vercel_frontend.domain
      proxied = true
    },
    {
      name    = "api"
      type    = "A"
      value   = module.fly_backend.ip_address
      proxied = true
    }
  ]
  
  page_rules = [
    {
      target = "api.uvai-youtube.com/*"
      actions = {
        cache_level = "bypass"
        ssl         = "flexible"
      }
    },
    {
      target = "*.uvai-youtube.com/static/*"
      actions = {
        cache_level       = "cache_everything"
        edge_cache_ttl   = 86400
        browser_cache_ttl = 86400
      }
    }
  ]
  
  firewall_rules = [
    {
      description = "Block bad bots"
      expression  = "(cf.client.bot) and not (cf.verified_bot)"
      action      = "block"
    },
    {
      description = "Rate limit API"
      expression  = "(http.request.uri.path contains \"/api/\")"
      action      = "challenge"
      ratelimit = {
        threshold = 100
        period    = 60
      }
    }
  ]
}

# ============================================
# Monitoring & Observability
# ============================================

module "monitoring" {
  source = "../../modules/monitoring"
  
  environment = var.environment
  project     = var.project_name
  
  sentry_project_name = local.app_name
  sentry_org_slug     = "uvai"
  
  datadog_api_key = var.datadog_api_key
  datadog_app_key = var.datadog_app_key
  
  prometheus_endpoints = [
    "${module.fly_backend.url}/metrics",
    "${module.fly_orchestrator.url}/metrics"
  ]
  
  alert_email = "alerts@uvai.com"
  
  alerts = [
    {
      name        = "high-error-rate"
      condition   = "error_rate > 0.01"
      severity    = "critical"
      channels    = ["email", "slack"]
    },
    {
      name        = "high-latency"
      condition   = "p95_latency > 500"
      severity    = "warning"
      channels    = ["slack"]
    },
    {
      name        = "low-disk-space"
      condition   = "disk_usage > 0.9"
      severity    = "critical"
      channels    = ["email", "pagerduty"]
    }
  ]
  
  dashboards = [
    "application-overview",
    "api-performance",
    "database-metrics",
    "ai-agent-performance"
  ]
  
  tags = local.common_tags
}

# ============================================
# Security & Compliance
# ============================================

module "security" {
  source = "../../modules/security"
  
  environment = var.environment
  project     = var.project_name
  
  enable_waf        = true
  enable_ddos       = true
  enable_encryption = true
  
  ssl_certificates = {
    main = {
      domain = module.cloudflare_dns.domain
      type   = "managed"
    }
  }
  
  secrets = {
    database_password = var.database_password
    jwt_secret       = var.jwt_secret_key
    api_keys = {
      openai    = var.openai_api_key
      anthropic = var.anthropic_api_key
    }
  }
  
  compliance = {
    gdpr_enabled = true
    ccpa_enabled = true
    sox_enabled  = false
  }
  
  audit_logging = {
    enabled        = true
    retention_days = 90
    destinations   = ["s3", "cloudwatch"]
  }
  
  tags = local.common_tags
}

# ============================================
# Outputs
# ============================================

output "application_urls" {
  value = {
    frontend     = "https://${module.cloudflare_dns.domain}"
    backend_api  = "https://api.${module.cloudflare_dns.domain}"
    orchestrator = module.fly_orchestrator.url
    monitoring   = module.monitoring.grafana_url
  }
  description = "Application URLs"
}

output "database_endpoints" {
  value = {
    postgres = module.database.endpoint
    redis    = module.redis.endpoint
    rabbitmq = module.rabbitmq.endpoint
  }
  description = "Database connection endpoints"
  sensitive   = true
}

output "storage_buckets" {
  value = {
    uploads = module.storage.bucket_urls.uploads
    backups = module.storage.bucket_urls.backups
    static  = module.storage.bucket_urls.static
  }
  description = "S3 bucket URLs"
}

output "monitoring_dashboards" {
  value = {
    grafana    = module.monitoring.grafana_url
    sentry     = module.monitoring.sentry_url
    datadog    = module.monitoring.datadog_url
    prometheus = module.monitoring.prometheus_url
  }
  description = "Monitoring dashboard URLs"
}

output "deployment_info" {
  value = {
    environment     = var.environment
    deployed_at     = timestamp()
    terraform_version = terraform.version
    backend_version = module.fly_backend.app_version
    frontend_version = module.vercel_frontend.deployment_id
  }
  description = "Deployment information"
}