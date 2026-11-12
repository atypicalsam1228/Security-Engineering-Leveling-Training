# IAM for the OpenShift installer, built from Red Hat's published list
# (OCP 4.22, Installing on AWS, "Required AWS permissions for the IAM user").
# The set for an EXISTING VPC is used: the "create network resources" group is
# left out because Terraform owns the network. The list is split into three
# managed policies because one managed policy is limited to 6,144 characters.

locals {
  installer_ec2_actions = [
    "ec2:AttachNetworkInterface", "ec2:AuthorizeSecurityGroupEgress", "ec2:AuthorizeSecurityGroupIngress",
    "ec2:CopyImage", "ec2:CreateNetworkInterface", "ec2:CreateSecurityGroup", "ec2:CreateTags",
    "ec2:CreateVolume", "ec2:DeleteSecurityGroup", "ec2:DeleteSnapshot", "ec2:DeleteTags",
    "ec2:DeregisterImage", "ec2:DescribeAccountAttributes", "ec2:DescribeAddresses",
    "ec2:DescribeAvailabilityZones", "ec2:DescribeDhcpOptions", "ec2:DescribeImages",
    "ec2:DescribeInstanceAttribute", "ec2:DescribeInstanceCreditSpecifications", "ec2:DescribeInstances",
    "ec2:DescribeInstanceTypes", "ec2:DescribeInstanceTypeOfferings", "ec2:DescribeInternetGateways",
    "ec2:DescribeKeyPairs", "ec2:DescribeNatGateways", "ec2:DescribeNetworkAcls",
    "ec2:DescribeNetworkInterfaces", "ec2:DescribePrefixLists", "ec2:DescribeRegions",
    "ec2:DescribeRouteTables", "ec2:DescribeSecurityGroupRules", "ec2:DescribeSecurityGroups",
    "ec2:DescribeSubnets", "ec2:DescribeTags", "ec2:DescribeVolumes", "ec2:DescribeVpcAttribute",
    "ec2:DescribeVpcClassicLink", "ec2:DescribeVpcClassicLinkDnsSupport", "ec2:DescribeVpcEndpoints",
    "ec2:DescribeVpcs", "ec2:GetEbsDefaultKmsKeyId", "ec2:ModifyInstanceAttribute",
    "ec2:ModifyNetworkInterfaceAttribute", "ec2:RevokeSecurityGroupEgress",
    "ec2:RevokeSecurityGroupIngress", "ec2:RunInstances", "ec2:TerminateInstances",
    # Deleting base cluster resources
    "autoscaling:DescribeAutoScalingGroups", "ec2:DeleteNetworkInterface", "ec2:DeletePlacementGroup",
    "ec2:DeleteVolume",
    # Tagging, deletion with an existing VPC, and quota checks
    "tag:GetResources", "tag:UntagResources", "servicequotas:ListAWSDefaultServiceQuotas",
    # Cluster delete with shared instance roles
    "iam:UntagRole",
  ]

  installer_elb_dns_actions = [
    "elasticloadbalancing:AddTags", "elasticloadbalancing:ApplySecurityGroupsToLoadBalancer",
    "elasticloadbalancing:AttachLoadBalancerToSubnets", "elasticloadbalancing:ConfigureHealthCheck",
    "elasticloadbalancing:CreateListener", "elasticloadbalancing:CreateLoadBalancer",
    "elasticloadbalancing:CreateLoadBalancerListeners", "elasticloadbalancing:CreateTargetGroup",
    "elasticloadbalancing:DeleteLoadBalancer", "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
    "elasticloadbalancing:DeregisterTargets", "elasticloadbalancing:DescribeInstanceHealth",
    "elasticloadbalancing:DescribeListeners", "elasticloadbalancing:DescribeLoadBalancerAttributes",
    "elasticloadbalancing:DescribeLoadBalancers", "elasticloadbalancing:DescribeTags",
    "elasticloadbalancing:DescribeTargetGroupAttributes", "elasticloadbalancing:DescribeTargetHealth",
    "elasticloadbalancing:ModifyLoadBalancerAttributes", "elasticloadbalancing:ModifyTargetGroup",
    "elasticloadbalancing:ModifyTargetGroupAttributes", "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
    "elasticloadbalancing:RegisterTargets", "elasticloadbalancing:SetLoadBalancerPoliciesOfListener",
    "elasticloadbalancing:SetSecurityGroups", "elasticloadbalancing:DeleteTargetGroup",
    "elasticloadbalancing:DescribeTargetGroups",
    # Not on Red Hat's list. Added so a brand-new account can create the
    # load balancer service-linked role. Remove if the role already exists.
    "iam:CreateServiceLinkedRole",
    "route53:ChangeResourceRecordSets", "route53:ChangeTagsForResource", "route53:CreateHostedZone",
    "route53:DeleteHostedZone", "route53:GetChange", "route53:GetHostedZone", "route53:ListHostedZones",
    "route53:ListHostedZonesByName", "route53:ListResourceRecordSets", "route53:ListTagsForResource",
    "route53:UpdateHostedZoneComment",
  ]

  installer_iam_s3_actions = [
    "iam:AddRoleToInstanceProfile", "iam:CreateInstanceProfile", "iam:CreateRole", "iam:DeleteInstanceProfile",
    "iam:DeleteRole", "iam:DeleteRolePolicy", "iam:GetInstanceProfile", "iam:GetRole", "iam:GetRolePolicy",
    "iam:GetUser", "iam:ListInstanceProfilesForRole", "iam:ListRoles", "iam:ListUsers", "iam:PassRole",
    "iam:PutRolePolicy", "iam:RemoveRoleFromInstanceProfile", "iam:SimulatePrincipalPolicy",
    "iam:TagInstanceProfile", "iam:TagRole",
    # Deletion
    "iam:DeleteAccessKey", "iam:DeleteUser", "iam:DeleteUserPolicy", "iam:ListAttachedRolePolicies",
    "iam:ListInstanceProfiles", "iam:ListRolePolicies", "iam:ListUserPolicies",
    # Manifests / credentials (mint mode)
    "iam:GetUserPolicy", "iam:ListAccessKeys", "iam:PutUserPolicy", "iam:TagUser", "iam:CreateAccessKey",
    "iam:CreateUser",
    # S3 for the installer
    "s3:CreateBucket", "s3:DeleteBucket", "s3:GetAccelerateConfiguration", "s3:GetBucketAcl",
    "s3:GetBucketCors", "s3:GetBucketLocation", "s3:GetBucketLogging", "s3:GetBucketObjectLockConfiguration",
    "s3:GetBucketPolicy", "s3:GetBucketRequestPayment", "s3:GetBucketTagging", "s3:GetBucketVersioning",
    "s3:GetBucketWebsite", "s3:GetEncryptionConfiguration", "s3:GetLifecycleConfiguration",
    "s3:GetReplicationConfiguration", "s3:ListBucket", "s3:PutBucketAcl", "s3:PutBucketPolicy",
    "s3:PutBucketTagging", "s3:PutEncryptionConfiguration", "s3:ListBucketVersions",
    "s3:AbortMultipartUpload", "s3:GetBucketPublicAccessBlock", "s3:ListBucketMultipartUploads",
    "s3:PutBucketPublicAccessBlock", "s3:PutLifecycleConfiguration",
    # S3 that cluster Operators need
    "s3:DeleteObject", "s3:GetObject", "s3:GetObjectAcl", "s3:GetObjectTagging", "s3:GetObjectVersion",
    "s3:PutObject", "s3:PutObjectAcl", "s3:PutObjectTagging",
  ]

  # Red Hat's "optional permissions for installing with a custom KMS key".
  # kms:ReEncrypt* is needed when the AMI is encrypted with a customer key.
  installer_kms_actions = [
    "kms:CreateGrant", "kms:Decrypt", "kms:DescribeKey", "kms:Encrypt", "kms:GenerateDataKey",
    "kms:GenerateDataKeyWithoutPlaintext", "kms:ListGrants", "kms:RevokeGrant", "kms:ReEncrypt*",
  ]
}

data "aws_iam_policy_document" "installer_ec2" {
  statement {
    sid       = "InstallerEc2AndTagging"
    effect    = "Allow"
    actions   = local.installer_ec2_actions
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "installer_elb_dns" {
  statement {
    sid       = "InstallerLoadBalancingAndDns"
    effect    = "Allow"
    actions   = local.installer_elb_dns_actions
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "installer_iam_s3_kms" {
  statement {
    sid       = "InstallerIamAndS3"
    effect    = "Allow"
    actions   = local.installer_iam_s3_actions
    resources = ["*"]
  }

  statement {
    sid       = "InstallerCustomerManagedKey"
    effect    = "Allow"
    actions   = local.installer_kms_actions
    resources = [aws_kms_key.lab.arn]
  }
}

resource "aws_iam_policy" "installer" {
  for_each = {
    ec2        = data.aws_iam_policy_document.installer_ec2.json
    elb-dns    = data.aws_iam_policy_document.installer_elb_dns.json
    iam-s3-kms = data.aws_iam_policy_document.installer_iam_s3_kms.json
  }

  name        = "${var.lab_id}-installer-${each.key}"
  description = "OpenShift installer permissions (${each.key}) for lab ${var.lab_id}"
  policy      = each.value
}

# Mint mode: the installer rejects the bastion's temporary instance-role credentials,
# so it runs with the long-term access key of this IAM user instead. The bastion creates
# the key at install time (iam:CreateAccessKey), so no secret passes through Terraform
# state or S3. force_destroy deletes the user's keys when `lab down` removes the user.
resource "aws_iam_user" "installer" {
  name          = "${var.lab_id}-installer"
  force_destroy = true
}

resource "aws_iam_user_policy_attachment" "installer" {
  for_each   = aws_iam_policy.installer
  user       = aws_iam_user.installer.name
  policy_arn = each.value.arn
}
