"""Builds MANUAL-INSTALL.docx and .md: the optional do-it-yourself cluster install.

Usage: python manual_install_guide.py     Writes both files to the project root.
"""

from __future__ import annotations

from pathlib import Path

from doc_builder import DocBuilder

ROOT = Path(__file__).resolve().parent.parent

INSTALL_CONFIG = """apiVersion: v1
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
pullSecret: '<PULL_SECRET_JSON_ON_ONE_LINE>'"""

VALUE_ROWS = [
    ["<BASE_DOMAIN>", "Your public Route 53 zone name, for example example.com"],
    ["<CLUSTER_NAME>", "`terraform output -raw cluster_name`"],
    ["<INSTANCE_TYPE>", "`terraform output -raw instance_type`"],
    ["<KMS_KEY_ARN>", "`terraform output -raw kms_key_arn`"],
    ["<EXTRA_SECURITY_GROUP_ID>", "`terraform output -raw extra_security_group_id`"],
    ["<AWS_REGION>", "`terraform output -raw aws_region`"],
    ["<PUBLIC_SUBNET_ID>, <PRIVATE_SUBNET_ID>", "`terraform output -raw public_subnet_id` and `private_subnet_id`"],
    ["<LAB_ID>, <DESTROY_AFTER>", "`terraform output -raw lab_id` and `destroy_after`"],
    ["<YOUR_SSH_PUBLIC_KEY>", "Any OpenSSH public key line, RSA or ECDSA because the cluster uses FIPS (for example `ssh-keygen -t ecdsa -b 256`, then the .pub file). Nodes are reached with `oc debug`, so the private half is optional"],
    ["<PULL_SECRET_JSON_ON_ONE_LINE>", "Your pull secret as one line: `jq -c . pull-secret.txt`"],
]


def build() -> None:
    b = DocBuilder()
    b.title("Manual Cluster Install (Optional)")
    b.para("STATUS: DRAFT. Nothing here has run on AWS. Commands follow the lab scripts in `terraform/` and the vendor install flow; expect corrections on the first live run. Times and sizes are estimates.")

    b.h1("1. When to use this")
    b.para("`lab up` normally installs the cluster for you. Use this guide instead if you want to run the OpenShift installer yourself and see each step. The result is the same cluster. You still use `lab down` to destroy it.")
    b.note("Cost: the lab bills from the moment `lab up` builds the infrastructure. A manual install takes longer than the automatic one, so work in one sitting.")

    b.h1("2. What you need")
    b.bullet("Everything in `README.md` section 1, including the Red Hat pull secret saved under `~/lab-workspace` and a public Route 53 zone.")
    b.bullet("The Session Manager plugin and AWS CLI (both are in `lab shell`).")

    b.h1("3. Steps")
    b.h2("Step 1. Build the infrastructure only")
    b.code("lab up --skip-cluster")
    b.para("This creates the VPC, KMS key, buckets and the bastion (a FIPS-mode RHEL 9 host with no inbound access). The bastion runs a background service that installs the cluster only when it finds `install/install-config.yaml` in the artifacts bucket. You will not upload that file, so the service stays idle and you run the installer yourself.")
    b.security("Never copy `install-config.yaml` into `s3://$ARTIFACTS_BUCKET/install/`. That would start the automatic install while you are working by hand.")

    b.h2("Step 2. Collect the values")
    b.para("In `lab shell`, from the `terraform` folder, read the values the config needs:")
    b.code("cd /workspace/../terraform 2>/dev/null || cd terraform\nterraform output")
    b.table(["Placeholder", "Where the value comes from"], VALUE_ROWS)

    b.h2("Step 3. Send the pull secret to the bastion")
    b.para("The bastion has no inbound access, so pass the secret through the encrypted artifacts bucket under a different key, then delete it.")
    b.code("aws s3 cp \"$PULL_SECRET_FILE\" \"s3://$ARTIFACTS_BUCKET/manual/pull-secret.json\" --sse aws:kms --sse-kms-key-id \"$KMS_KEY_ARN\"")

    b.h2("Step 4. Open a shell on the bastion")
    b.code("aws ssm start-session --target \"$BASTION_ID\" --region \"$AWS_REGION\"\nsudo -i\ncat /proc/sys/crypto/fips_enabled")
    b.checkpoint("The last command prints `1`. If it prints `0`, the bastion has not finished its FIPS reboot; wait a few minutes and try again. The installer binary only works on a FIPS host.")

    b.h2("Step 5. Get the tools and the secret")
    b.code(
        "grep '^CHANNEL=' /usr/local/bin/lab-install.sh\n"
        "CHANNEL=<value from the line above>\n"
        "BUCKET=<your artifacts bucket name>\n"
        "umask 077\n"
        "aws s3 cp s3://$BUCKET/manual/pull-secret.json /var/lib/lab/pull-secret.json\n"
        "aws s3 rm s3://$BUCKET/manual/pull-secret.json\n"
        "MIRROR=https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/$CHANNEL\n"
        "curl -fsSL $MIRROR/openshift-client-linux.tar.gz | tar -xz -C /usr/local/bin oc kubectl\n"
        "PULL=$(curl -fsSL $MIRROR/release.txt | awk '/^Pull From:/ {print $3}')\n"
        "oc adm release extract --command=openshift-install-fips --from=$PULL --registry-config=/var/lib/lab/pull-secret.json --to=/usr/local/bin"
    )
    b.para("`oc adm release extract` pulls the FIPS installer out of Red Hat's release image. This is the first place the pull secret is used. If it fails with an authentication error, the pull secret is wrong or expired.")

    b.h2("Step 6. Write install-config.yaml")
    b.para("Create the file in the installer directory the bastion service already uses (`/var/lib/lab/cluster`), so `lab down` can find and destroy this cluster later. Fill in every placeholder from Step 2.")
    b.code("cat > /var/lib/lab/cluster/install-config.yaml <<'EOF'\n" + INSTALL_CONFIG + "\nEOF\nchmod 600 /var/lib/lab/cluster/install-config.yaml")
    b.note("The installer deletes `install-config.yaml` when it runs. Keep a copy first if you want one: `cp /var/lib/lab/cluster/install-config.yaml /var/lib/lab/install-config.backup` (it holds your pull secret, so delete the copy afterward).")

    b.h2("Step 7. Run the installer")
    b.code("cd /var/lib/lab\nnohup openshift-install-fips create cluster --dir /var/lib/lab/cluster --log-level=info > /var/log/lab-manual-install.log 2>&1 &\ntail -F /var/log/lab-manual-install.log")
    b.para("`nohup` keeps the install running if your session drops. If it drops, reconnect with Step 4 and run the `tail` line again. The install usually takes about 45 to 70 minutes (estimate).")
    b.checkpoint("The log ends with `Install complete!` and the console URL. The kubeadmin password is printed in the last lines; do not copy it into chat or notes.")

    b.h2("Step 8. Hand the cluster to the lab")
    b.para("`lab up`, `lab down` and the cost guard read the install result from the artifacts bucket. Publish it the same way the automatic path does:")
    b.code(
        "D=/var/lib/lab/cluster\n"
        "aws s3 cp $D/auth/kubeconfig s3://$BUCKET/install/auth/kubeconfig --sse aws:kms\n"
        "aws s3 cp $D/auth/kubeadmin-password s3://$BUCKET/install/auth/kubeadmin-password --sse aws:kms\n"
        "aws s3 cp $D/metadata.json s3://$BUCKET/install/state/metadata.json --sse aws:kms\n"
        "touch /var/lib/lab/installed\n"
        "echo complete | aws s3 cp - s3://$BUCKET/install/status --sse aws:kms\n"
        "rm -f /var/lib/lab/pull-secret.json\n"
        "exit"
    )
    b.para("Setting `/var/lib/lab/installed` stops the bastion service from starting a second install. Back in `lab shell` on your laptop, run `lab up` once more. It sees status `complete` and saves the kubeconfig to `<workspace>/.lab/kubeconfig` without building anything new.")

    b.h2("Step 9. Check the cluster")
    b.code("lab shell\noc get nodes\noc get clusteroperators")
    b.checkpoint("One node in `Ready`, and every cluster operator `Available=True`. Then `lab start eng-0` and begin with ENG-0.")

    b.h1("4. If it fails")
    b.table(["Symptom", "Likely cause and next step"], [
        ["Authentication error in Step 5", "Pull secret missing, expired or not valid JSON. Download a new one from Red Hat and repeat Step 3."],
        ["Installer refuses to run", "Host is not in FIPS mode. Check `cat /proc/sys/crypto/fips_enabled`; it must print 1."],
        ["Installer stops with a quota or capacity error", "The AWS account or Region lacks quota for the instance type. Request more quota or choose another Region, then run `lab down` and start again."],
        ["Installer fails part-way", "Read the end of `/var/log/lab-manual-install.log`. Run `lab down` to clean up (it destroys whatever the installer created), then start again."],
        ["`lab up` says unexpected status", "Step 8 `status` upload did not run. Repeat it, then run `lab up`."],
    ])

    b.h1("5. Stopping")
    b.para("Run `lab down` as usual. It asks the bastion to run `openshift-install-fips destroy cluster` against `/var/lib/lab/cluster`, which works because you installed into that directory. Then Terraform destroys the rest.")
    b.security("Do not leave the pull secret on the bastion or in the bucket. Steps 5 and 8 delete both copies; confirm with `ls /var/lib/lab` and `aws s3 ls s3://$BUCKET/manual/`.")

    b.save(ROOT, "MANUAL-INSTALL")
    print("callouts:", dict(b.counts))


if __name__ == "__main__":
    build()
