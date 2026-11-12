# Manual Cluster Install (Optional)

STATUS: DRAFT. Nothing here has run on AWS. Commands follow the lab scripts in `terraform/` and the vendor install flow; expect corrections on the first live run. Times and sizes are estimates.

## 1. When to use this

`lab up` normally installs the cluster for you. Use this guide instead if you want to run the OpenShift installer yourself and see each step. The result is the same cluster. You still use `lab down` to destroy it.

> **NOTE:** Cost: the lab bills from the moment `lab up` builds the infrastructure. A manual install takes longer than the automatic one, so work in one sitting.

## 2. What you need

- Everything in `README.md` section 1, including the Red Hat pull secret saved under `~/lab-workspace` and a public Route 53 zone.
- The Session Manager plugin and AWS CLI (both are in `lab shell`).

## 3. Steps

### Step 1. Build the infrastructure only

```bash
lab up --skip-cluster
```

This creates the VPC, KMS key, buckets and the bastion (a FIPS-mode RHEL 9 host with no inbound access). The bastion runs a background service that installs the cluster only when it finds `install/install-config.yaml` in the artifacts bucket. You will not upload that file, so the service stays idle and you run the installer yourself.

> **SECURITY:** Never copy `install-config.yaml` into `s3://$ARTIFACTS_BUCKET/install/`. That would start the automatic install while you are working by hand.

### Step 2. Collect the values

In `lab shell`, from the `terraform` folder, read the values the config needs:

```bash
cd /workspace/../terraform 2>/dev/null || cd terraform
terraform output
```

| Placeholder | Where the value comes from |
| --- | --- |
| <BASE_DOMAIN> | Your public Route 53 zone name, for example example.com |
| <CLUSTER_NAME> | `terraform output -raw cluster_name` |
| <INSTANCE_TYPE> | `terraform output -raw instance_type` |
| <KMS_KEY_ARN> | `terraform output -raw kms_key_arn` |
| <EXTRA_SECURITY_GROUP_ID> | `terraform output -raw extra_security_group_id` |
| <AWS_REGION> | `terraform output -raw aws_region` |
| <PUBLIC_SUBNET_ID>, <PRIVATE_SUBNET_ID> | `terraform output -raw public_subnet_id` and `private_subnet_id` |
| <LAB_ID>, <DESTROY_AFTER> | `terraform output -raw lab_id` and `destroy_after` |
| <YOUR_SSH_PUBLIC_KEY> | Any OpenSSH public key line, RSA or ECDSA because the cluster uses FIPS (for example `ssh-keygen -t ecdsa -b 256`, then the .pub file). Nodes are reached with `oc debug`, so the private half is optional |
| <PULL_SECRET_JSON_ON_ONE_LINE> | Your pull secret as one line: `jq -c . pull-secret.txt` |

### Step 3. Send the pull secret to the bastion

The bastion has no inbound access, so pass the secret through the encrypted artifacts bucket under a different key, then delete it.

```bash
aws s3 cp "$PULL_SECRET_FILE" "s3://$ARTIFACTS_BUCKET/manual/pull-secret.json" --sse aws:kms --sse-kms-key-id "$KMS_KEY_ARN"
```

### Step 4. Open a shell on the bastion

```bash
aws ssm start-session --target "$BASTION_ID" --region "$AWS_REGION"
sudo -i
cat /proc/sys/crypto/fips_enabled
```

> **CHECKPOINT:** The last command prints `1`. If it prints `0`, the bastion has not finished its FIPS reboot; wait a few minutes and try again. The installer binary only works on a FIPS host.

### Step 5. Get the tools and the secret

```bash
grep '^CHANNEL=' /usr/local/bin/lab-install.sh
CHANNEL=<value from the line above>
BUCKET=<your artifacts bucket name>
umask 077
aws s3 cp s3://$BUCKET/manual/pull-secret.json /var/lib/lab/pull-secret.json
aws s3 rm s3://$BUCKET/manual/pull-secret.json
MIRROR=https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/$CHANNEL
curl -fsSL $MIRROR/openshift-client-linux.tar.gz | tar -xz -C /usr/local/bin oc kubectl
PULL=$(curl -fsSL $MIRROR/release.txt | awk '/^Pull From:/ {print $3}')
oc adm release extract --command=openshift-install-fips --from=$PULL --registry-config=/var/lib/lab/pull-secret.json --to=/usr/local/bin
```

`oc adm release extract` pulls the FIPS installer out of Red Hat's release image. This is the first place the pull secret is used. If it fails with an authentication error, the pull secret is wrong or expired.

### Step 6. Write install-config.yaml

Create the file in the installer directory the bastion service already uses (`/var/lib/lab/cluster`), so `lab down` can find and destroy this cluster later. Fill in every placeholder from Step 2.

```bash
cat > /var/lib/lab/cluster/install-config.yaml <<'EOF'
apiVersion: v1
baseDomain: <BASE_DOMAIN>
metadata:
  name: <CLUSTER_NAME>
fips: true
publish: External
networking:
  machineNetwork:
    - cidr: 10.0.0.0/16
controlPlane:
  name: master
  replicas: 1
  platform:
    aws:
      type: <INSTANCE_TYPE>
      rootVolume:
        size: 120
        type: gp3
        kmsKeyARN: <KMS_KEY_ARN>
      additionalSecurityGroupIDs:
        - <EXTRA_SECURITY_GROUP_ID>
compute:
  - name: worker
    replicas: 0
platform:
  aws:
    region: <AWS_REGION>
    vpc:
      subnets:
        - id: <PUBLIC_SUBNET_ID>
        - id: <PRIVATE_SUBNET_ID>
    propagateUserTags: true
    userTags:
      LabId: "<LAB_ID>"
      AutoDestroyAfter: "<DESTROY_AFTER>"
sshKey: <YOUR_SSH_PUBLIC_KEY>
pullSecret: '<PULL_SECRET_JSON_ON_ONE_LINE>'
EOF
chmod 600 /var/lib/lab/cluster/install-config.yaml
```

> **NOTE:** The installer deletes `install-config.yaml` when it runs. Keep a copy first if you want one: `cp /var/lib/lab/cluster/install-config.yaml /var/lib/lab/install-config.backup` (it holds your pull secret, so delete the copy afterward).

### Step 7. Run the installer

```bash
cd /var/lib/lab
nohup openshift-install-fips create cluster --dir /var/lib/lab/cluster --log-level=info > /var/log/lab-manual-install.log 2>&1 &
tail -F /var/log/lab-manual-install.log
```

`nohup` keeps the install running if your session drops. If it drops, reconnect with Step 4 and run the `tail` line again. The install usually takes about 45 to 70 minutes (estimate).

> **CHECKPOINT:** The log ends with `Install complete!` and the console URL. The kubeadmin password is printed in the last lines; do not copy it into chat or notes.

### Step 8. Hand the cluster to the lab

`lab up`, `lab down` and the cost guard read the install result from the artifacts bucket. Publish it the same way the automatic path does:

```bash
D=/var/lib/lab/cluster
aws s3 cp $D/auth/kubeconfig s3://$BUCKET/install/auth/kubeconfig --sse aws:kms
aws s3 cp $D/auth/kubeadmin-password s3://$BUCKET/install/auth/kubeadmin-password --sse aws:kms
aws s3 cp $D/metadata.json s3://$BUCKET/install/state/metadata.json --sse aws:kms
touch /var/lib/lab/installed
echo complete | aws s3 cp - s3://$BUCKET/install/status --sse aws:kms
rm -f /var/lib/lab/pull-secret.json
exit
```

Setting `/var/lib/lab/installed` stops the bastion service from starting a second install. Back in `lab shell` on your laptop, run `lab up` once more. It sees status `complete` and saves the kubeconfig to `<workspace>/.lab/kubeconfig` without building anything new.

### Step 9. Check the cluster

```bash
lab shell
oc get nodes
oc get clusteroperators
```

> **CHECKPOINT:** One node in `Ready`, and every cluster operator `Available=True`. Then `lab start eng-0` and begin with ENG-0.

## 4. If it fails

| Symptom | Likely cause and next step |
| --- | --- |
| Authentication error in Step 5 | Pull secret missing, expired or not valid JSON. Download a new one from Red Hat and repeat Step 3. |
| Installer refuses to run | Host is not in FIPS mode. Check `cat /proc/sys/crypto/fips_enabled`; it must print 1. |
| Installer stops with a quota or capacity error | The AWS account or Region lacks quota for the instance type. Request more quota or choose another Region, then run `lab down` and start again. |
| Installer fails part-way | Read the end of `/var/log/lab-manual-install.log`. Run `lab down` to clean up (it destroys whatever the installer created), then start again. |
| `lab up` says unexpected status | Step 8 `status` upload did not run. Repeat it, then run `lab up`. |

## 5. Stopping

Run `lab down` as usual. It asks the bastion to run `openshift-install-fips destroy cluster` against `/var/lib/lab/cluster`, which works because you installed into that directory. Then Terraform destroys the rest.

> **SECURITY:** Do not leave the pull secret on the bastion or in the bucket. Steps 5 and 8 delete both copies; confirm with `ls /var/lib/lab` and `aws s3 ls s3://$BUCKET/manual/`.
