# Lab tools image (lab-tools:latest). See README.md and versions.txt.
# Base: Red Hat UBI 9 minimal (vetted Red Hat base). The 9.8 tag floats with
# security rebuilds; pin a digest for a release build (see README).
# Stage 1 downloads and verifies every binary. Stage 2 copies only the results,
# so the download helpers (gpg, unzip, rpm2cpio) and the archives never ship.

FROM registry.access.redhat.com/ubi9/ubi-minimal:9.8 AS fetch
ARG TARGETARCH
ARG OC_VERSION=4.22.18
ARG TERRAFORM_VERSION=1.17.0
ARG COSIGN_VERSION=3.1.4
ARG TRIVY_VERSION=0.76.1
ARG ARGOCD_VERSION=3.5.6
ARG TKN_VERSION=0.46.2
ARG AWSCLI_VERSION=2.38.5
ARG SSM_PLUGIN_VERSION=1.2.896.0
ARG AWS_CLI_KEY_FPR=FB5DB77FD5C118B80511ADA8A6310ACC4672475C
ARG K8S_PROVIDER_VERSION=3.4.0
ARG KUBERNETES_CORE_VERSION=6.6.0
ARG HELM_VERSION=3.22.1

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
RUN microdnf install -y --setopt=install_weak_deps=0 --nodocs \
      tar gzip unzip gnupg2 rpm cpio findutils \
    && microdnf clean all
COPY checksums.sha256 /checksums.sha256
COPY aws-cli-public-key.asc /aws-cli-public-key.asc

WORKDIR /dl
# get URL FILE: download, then verify against the pinned sha256 in checksums.sha256.
RUN case "${TARGETARCH}" in \
      amd64) A=amd64; TRIVY_A=64bit; TKN_A=x86_64;  AWS_A=x86_64;  SSM_A=64bit ;; \
      arm64) A=arm64; TRIVY_A=ARM64; TKN_A=aarch64; AWS_A=aarch64; SSM_A=arm64 ;; \
      *) echo "unsupported TARGETARCH=${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    get() { curl -fsSL --retry 3 -o "$2" "$1"; grep -F "  $2" /checksums.sha256 | sha256sum -c -; }; \
    mkdir -p /out/bin; \
    f=openshift-client-linux-${A}-rhel9-${OC_VERSION}.tar.gz; \
    get https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OC_VERSION}/$f $f; \
    tar -xzf $f -C /out/bin oc kubectl; \
    f=terraform_${TERRAFORM_VERSION}_linux_${A}.zip; \
    get https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/$f $f; \
    unzip -q -o $f terraform -d /out/bin; \
    mkdir /tfsrc; \
    printf 'terraform {\n  required_providers {\n    kubernetes = {\n      source  = "hashicorp/kubernetes"\n      version = "%s"\n    }\n  }\n}\n' "${K8S_PROVIDER_VERSION}" > /tfsrc/main.tf; \
    (cd /tfsrc; /out/bin/terraform providers mirror -platform=linux_amd64 -platform=linux_arm64 /out/tf-providers); \
    f=kubernetes-core-${KUBERNETES_CORE_VERSION}.tar.gz; \
    get https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/artifacts/$f $f; \
    cp $f /out/$f; \
    f=helm-v${HELM_VERSION}-linux-${A}.tar.gz; \
    get https://get.helm.sh/$f $f; \
    tar -xzf $f --strip-components=1 -C /out/bin linux-${A}/helm; \
    f=cosign-linux-${A}; \
    get https://github.com/sigstore/cosign/releases/download/v${COSIGN_VERSION}/$f $f; \
    install -m 0755 $f /out/bin/cosign; \
    f=trivy_${TRIVY_VERSION}_Linux-${TRIVY_A}.tar.gz; \
    get https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/$f $f; \
    tar -xzf $f -C /out/bin trivy; \
    f=argocd-linux-${A}; \
    get https://github.com/argoproj/argo-cd/releases/download/v${ARGOCD_VERSION}/$f $f; \
    install -m 0755 $f /out/bin/argocd; \
    f=tkn_${TKN_VERSION}_Linux_${TKN_A}.tar.gz; \
    get https://github.com/tektoncd/cli/releases/download/v${TKN_VERSION}/$f $f; \
    tar -xzf $f -C /out/bin tkn; \
    f=session-manager-plugin-${SSM_PLUGIN_VERSION}-linux_${SSM_A}.rpm; \
    get https://s3.amazonaws.com/session-manager-downloads/plugin/${SSM_PLUGIN_VERSION}/linux_${SSM_A}/session-manager-plugin.rpm $f; \
    mkdir ssm; (cd ssm; rpm2cpio ../$f | cpio -idm --quiet); \
    install -m 0755 ssm/usr/local/sessionmanagerplugin/bin/session-manager-plugin /out/bin/session-manager-plugin; \
    f=awscli-exe-linux-${AWS_A}-${AWSCLI_VERSION}.zip; \
    get https://awscli.amazonaws.com/$f $f; \
    curl -fsSL --retry 3 -o $f.sig https://awscli.amazonaws.com/$f.sig; \
    export GNUPGHOME=$(mktemp -d); \
    gpg --batch --import /aws-cli-public-key.asc; \
    gpg --batch --with-colons --fingerprint | grep -q "^fpr:::::::::${AWS_CLI_KEY_FPR}:"; \
    gpg --batch --verify $f.sig $f; \
    unzip -q $f; \
    ./aws/install --install-dir /usr/local/aws-cli --bin-dir /out/bin

FROM registry.access.redhat.com/ubi9/ubi-minimal:9.8
LABEL org.opencontainers.image.title="lab-tools" \
      org.opencontainers.image.description="Tools container for the hands-on training lab" \
      org.opencontainers.image.base.name="registry.access.redhat.com/ubi9/ubi-minimal:9.8"

# OS packages from the Red Hat UBI repositories (python3-pyyaml, jq, gettext = envsubst).
RUN microdnf install -y --setopt=install_weak_deps=0 --nodocs \
      git jq openssl openssh-clients python3 python3-pyyaml gawk \
      gettext tar gzip unzip findutils diffutils procps-ng which less shadow-utils \
    && microdnf clean all

# /out/bin holds the tools plus the aws and aws_completer symlinks into /usr/local/aws-cli.
COPY --from=fetch /usr/local/aws-cli /usr/local/aws-cli
COPY --from=fetch /out/bin/ /usr/local/bin/

# Terraform provider mirror: the Kubernetes provider is installed from this folder, so
# `terraform init` needs no internet. terraform.rc routes only that provider to the mirror.
COPY --from=fetch /out/tf-providers /usr/local/share/terraform/providers
COPY terraform.rc /etc/terraform.rc
ENV TF_CLI_CONFIG_FILE=/etc/terraform.rc

# Ansible lives in its own Python 3.12 venv (hash-pinned wheels only). The system python3
# stays 3.9, so the module scripts that run on it are unaffected.
COPY requirements-ansible.txt /tmp/requirements-ansible.txt
COPY --from=fetch /out/kubernetes-core-*.tar.gz /tmp/
RUN microdnf install -y --setopt=install_weak_deps=0 --nodocs python3.12 python3.12-pip \
    && microdnf clean all \
    && python3.12 -m venv /opt/ansible \
    && /opt/ansible/bin/pip install --no-cache-dir --only-binary=:all: --require-hashes -r /tmp/requirements-ansible.txt \
    && /opt/ansible/bin/ansible-galaxy collection install /tmp/kubernetes-core-*.tar.gz -p /usr/share/ansible/collections --no-deps \
    && for t in ansible ansible-playbook ansible-lint ansible-galaxy; do ln -s /opt/ansible/bin/$t /usr/local/bin/$t; done \
    && rm -f /tmp/requirements-ansible.txt /tmp/kubernetes-core-*.tar.gz
ENV ANSIBLE_COLLECTIONS_PATH=/usr/share/ansible/collections

# Non-root user. Home and the lab folders are group-writable by root group, so
# an arbitrary UID (OpenShift style) also works. No credentials are baked in.
RUN useradd --uid 1001 --gid 0 --create-home --home-dir /home/lab --shell /bin/bash lab \
    && mkdir -p /workspace /lab/states /lab/terraform /home/lab/.ssh \
    && chmod 700 /home/lab/.ssh \
    && chown -R 1001:0 /home/lab /workspace /lab \
    && chmod -R g=u /home/lab /workspace /lab

ENV HOME=/home/lab \
    AWS_PAGER= \
    LANG=C.UTF-8
USER 1001
WORKDIR /workspace
# No ENTRYPOINT: the lab CLI passes `bash` or a command as the container argv.
CMD ["bash"]
