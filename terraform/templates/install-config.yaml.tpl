# Lab install-config.yaml template. Rendered by scripts/lab-install.sh, which
# replaces every double-underscore token and then appends two lines: sshKey and
# pullSecret. Neither secret value is ever stored in this file.
# Nothing here has run on AWS. Values marked placeholder are unmeasured.
apiVersion: v1
baseDomain: __BASE_DOMAIN__
metadata:
  name: __CLUSTER_NAME__
# FIPS mode for the cluster nodes. The installer binary must also be the FIPS
# build (openshift-install-fips) running on a FIPS-mode host: the lab bastion.
fips: true
# Mint mode: the cluster keeps a long-term IAM user key (kube-system/aws-creds) and the
# Cloud Credential Operator mints a narrower user per component. The bastion creates that key
# for the Terraform-built installer user at install time. Chosen for speed over STS/Manual mode.
credentialsMode: Mint
# LAB DECISION: public endpoints. "External" makes the API and the ingress
# load balancers internet-facing so that 'lab shell' on a laptop can reach the
# cluster with no VPN. Access is still controlled by credentials, not by network
# position. See ARCHITECTURE-DECISIONS.md (public endpoint decision and the
# private-endpoint appendix). A production build would use "Internal".
publish: External
networking:
  machineNetwork:
    # Must equal the Terraform VPC CIDR (terraform/network.tf).
    - cidr: 10.0.0.0/16
# Single-node OpenShift: one control plane node that also runs workloads.
controlPlane:
  name: master
  replicas: 1
  platform:
    aws:
      # Placeholder size. Taken from the Terraform variable instance_type so the
      # two cannot disagree; measure on a first run (README.md) and resize.
      type: __INSTANCE_TYPE__
      rootVolume:
        # 120 GB is the single-node storage minimum in Red Hat's published pages.
        size: 120
        type: gp3
        kmsKeyARN: __KMS_KEY_ARN__
      additionalSecurityGroupIDs:
        - __EXTRA_SECURITY_GROUP_ID__
compute:
  - name: worker
    replicas: 0
platform:
  aws:
    region: __AWS_REGION__
    # Existing VPC built by Terraform: one public and one private subnet.
    vpc:
      subnets:
        - id: __PUBLIC_SUBNET_ID__
        - id: __PRIVATE_SUBNET_ID__
    # Tags on every resource the installer creates, so the sweeper, the budget
    # filter and the cost guard can find them.
    propagateUserTags: true
    userTags:
      LabId: "__LAB_ID__"
      AutoDestroyAfter: "__DESTROY_AFTER__"
