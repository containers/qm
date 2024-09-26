# Title: How to change the variables in qm containers.conf

## Description

The `container.conf` file needs to be modified to allow pulling images larger than 1G from the repository on OStree images.

Input:

## Update container image_copy_tmp_dir if the image is an OStree

1. Create /var/qm/tmp.dir or differently named directory on host.
2. Create /etc/qm/containers/containers.conf.d or differently named directory on host.
3. Create and edit /etc/qm/containers/containers.conf.d/qm_image_tmp_dir.conf or differently named *.conf file and add the following lines:
[engine]
image_copy_tmp_dir="/var/tmp.dir"

## Sample code should look like this

<https://github.com/nsednev/qm/blob/3bbe302791ea5d0f271a1cc96ed6bce4d4b99de2/tests/ffi/common/prepare.sh#L76-L79>

By default image_copy_tmp_dir="/var/tmp".
Changing its default value to /var/tmp.dir will allow the container to pull images larger than 1G.

This is a work around and it should not be used constantly.

## Expected result

Containers on host will be able to pull images larger than 1G.
