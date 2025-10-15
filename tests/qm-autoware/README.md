# CentOS Automotive Autoware Demo Test

This test uses the simulator from CentOS Automotive Autoware Demo and runs it within QM.

## qm-autoware

Test verifies Autoware demo health is OK.
[CentOS Automotive Autoware Repository](https://gitlab.com/CentOS/automotive/demos/autoware.git)

## scripts

Directory is used in case `quay.io/qm-images/autoware:latest` Autoware update is needed.

## Test notes

Simulator container should run inside QM with the following settings:

```bash
--privileged -v /var/lib/containers/storage:/var/lib/containers/storage
```
