# Data source for EKS optimized AMI (Amazon Linux 2023)
data "aws_ami" "eks_optimized" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amazon-eks-node-al2023-x86_64-standard-${var.eks_cluster_version}-v*"]
  }
}

# Launch Templates for node groups (created dynamically from variable)
# Note: These depend on the EKS module to create the cluster and node security group first
resource "aws_launch_template" "node_groups" {
  for_each    = var.eks_node_groups
  name_prefix = "${var.project_name}-${each.key}-ng-"
  image_id    = data.aws_ami.eks_optimized.id
  # Note: instance_type is specified in the node group configuration
  # Note: user_data is managed by EKS managed node group service

  vpc_security_group_ids = [module.eks.node_security_group_id]

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = each.value.disk_size
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  # Tags applied to EC2 instances
  tag_specifications {
    resource_type = "instance"
    tags = merge(
      {
        Name        = "${var.project_name}-${each.key}-node"
        Environment = var.environment
        NodeGroup   = each.key
        Project     = var.project_name
        ManagedBy   = "Terraform"
        createdby   = "ck@presidio.com"
        modifiedby  = "ck@presidio.com"
      },
      each.value.instance_tags
    )
  }

  # Tags applied to volumes
  tag_specifications {
    resource_type = "volume"
    tags = merge(
      {
        Name        = "${var.project_name}-${each.key}-node-volume"
        Environment = var.environment
        NodeGroup   = each.key
        Project     = var.project_name
        ManagedBy   = "Terraform"
        createdby   = "ck@presidio.com"
        modifiedby  = "ck@presidio.com"
      },
      each.value.volume_tags
    )
  }

  lifecycle {
    create_before_destroy = true
  }
}

# EKS Cluster Module
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${var.project_name}-cluster"
  cluster_version = var.eks_cluster_version

  # VPC Configuration
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  enable_irsa                              = true
  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = true

  # Cluster endpoint access
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # Enable cluster logging
  # cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # EKS Managed Node Groups (created dynamically from variable)
  eks_managed_node_groups = {
    for key, config in var.eks_node_groups : key => {
      name           = "${var.project_name}-${key}"
      instance_types = config.instance_types

      min_size     = config.min_size
      max_size     = config.max_size
      desired_size = config.desired_size

      # Use launch template for better control and instance tagging
      use_custom_launch_template = true
      launch_template_id         = aws_launch_template.node_groups[key].id
      launch_template_version    = aws_launch_template.node_groups[key].latest_version

      # Disk configuration (handled in launch template)
      disk_size = config.disk_size

      # Labels and taints
      labels = merge(
        {
          Environment = var.environment
        },
        config.labels
      )

      # Taints (if specified)
      taints = config.taints

      # Update configuration
      update_config = config.update_config
    }
  }

  # Addon configuration
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent    = true
      before_compute = true
      configuration_values = jsonencode({
        env = {
          # Reference docs https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html
          ENABLE_PREFIX_DELEGATION = "true"
          WARM_PREFIX_TARGET       = "1"
        }
      })
    }
    aws-ebs-csi-driver = {
      most_recent              = true
      service_account_role_arn = aws_iam_role.ebs_csi.arn
    }
  }

  tags = {
    Name       = "${var.project_name}-eks-cluster"
    createdby  = "ck@presidio.com"
    modifiedby = "ck@presidio.com"
  }
}


data "aws_iam_policy_document" "ebs_csi_irsa" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [module.eks.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_provider}:sub"

      values = [
        "system:serviceaccount:kube-system:ebs-csi-controller-sa"
      ]
    }

    effect = "Allow"
  }
}

resource "aws_iam_role" "ebs_csi" {
  name               = "${var.project_name}-ebs-csi"
  assume_role_policy = data.aws_iam_policy_document.ebs_csi_irsa.json
}

resource "aws_iam_role_policy_attachment" "AmazonEBSCSIDriverPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
  role       = aws_iam_role.ebs_csi.name
}
