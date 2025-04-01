#!/usr/bin/bash

# Install required repos
sudo dnf -y install guestfs-tools curl perl qemu-user-static

ARCHS=("amd64" "aarch64")
IMAGE_NAME="kvm"
TAG="latest"
MANIFEST_NAME="${IMAGE_NAME}-manifest:${TAG}"
FEDORA_USER_PASSWORD=${FEDORA_USER_PASSWORD:-$(openssl rand -base64 12)}

#IMG_REG=quay.io
#IMG_ORG=qm-images

rm -f ./Fedora-Cloud-Base-Generic.qcow2
podman manifest rm "$MANIFEST_NAME"
podman manifest create "$MANIFEST_NAME" || exit 1

for ARCH in "${ARCHS[@]}"; do
    ARCH_QEMU=$([[ "$ARCH" == "amd64" ]] && echo "x86_64" || echo "$ARCH")
    curl  -Lo ./Fedora-Cloud-Base-Generic.qcow2 "https://download.fedoraproject.org/pub/fedora/linux/releases/41/Cloud/${ARCH_QEMU}/images/Fedora-Cloud-Base-Generic-41-1.4.${ARCH_QEMU}.qcow2"
    # Customize user:pass
    export LIBGUESTFS_BACKEND=direct &&   \
       virt-customize -a ./Fedora-Cloud-Base-Generic.qcow2   \
             --edit '/etc/ssh/sshd_config: s/#PasswordAuthentication.*/PasswordAuthentication yes/' \
             --firstboot-command 'dnf remove -y cloud-init' \
             --firstboot-command "useradd -m -s /bin/bash -G wheel fedora" \
             --firstboot-command "echo fedora:$FEDORA_USER_PASSWORD | chpasswd"

    echo "Adding ${IMAGE_NAME}:${ARCH} to the manifest"
    podman build \
        --arch "${ARCH}" \
	--build-arg ARCH_QEMU="${ARCH_QEMU}" \
        --manifest ${MANIFEST_NAME} \
        -f ContainerFile \
        -t "${IMAGE_NAME}:${ARCH}"

    rm -f ./Fedora-Cloud-Base-Generic.qcow2

done

#podman login --username "${REG_USERNAME}" --password "${REG_PASSWORD}" "${REG_URL}"
#podman push localhost/kvm-manifest quay.io/qm-images/kvm:latest
