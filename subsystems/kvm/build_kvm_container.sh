#!/usr/bin/bash

# Install required repos
dnf install guestfs-tools \
            curl \
            perl -y

# Download fedora cloud image
curl -Lo ./Fedora-Cloud-Base-Generic.qcow2 https://download.fedoraproject.org/pub/fedora/linux/releases/41/Cloud/"$(arch)"/images/Fedora-Cloud-Base-Generic-41-1.4."$(arch)".qcow2

# Customize user:pass
export LIBGUESTFS_BACKEND=direct &&   \
      virt-customize -a ./Fedora-Cloud-Base-Generic.qcow2   \
            --edit '/etc/ssh/sshd_config: s/#PasswordAuthentication.*/PasswordAuthentication yes/' \
            --uninstall cloud-init \
            --firstboot-command "useradd -m -s /bin/bash -G wheel fedora" \
            --firstboot-command "echo 'fedora:fedora' | chpasswd"

# Container build
podman build -t quay.io/qm-images/kvm:latest -f ContainerFile

