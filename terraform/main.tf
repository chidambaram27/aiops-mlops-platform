# Main Terraform configuration for AIOps MLOps + AIOps POC
# This file serves as the entry point and can be used for additional resources

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

