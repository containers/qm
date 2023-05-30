- [Dashboard](#dashboard)
  * [Requirements](#requirements)
  * [Technologies](#technologies)
  * [Want to contribute?](#want-to-contribute-)

# Dashboard

Imagine if you could simulate your car computer managing all the services running in an isolated environment with containers?  
Not only that, all these services will be showing to you in a clear way if it's running as Automotive Safety Integrity Level (**ASIL**) or as Quality Management (**QM**)?

We would love that too, see the demo below! 

**NOTE**: only in the video below, the graphs are not working correctly.
[![asciicast](https://asciinema.org/a/RGrjJRwM10sgFvXU3d9gcWsl3.svg)](https://asciinema.org/a/RGrjJRwM10sgFvXU3d9gcWsl3)

## Requirements

To create a TUI in python, we use `rich` module. To install use:
```
pip install rich
```

We recommend (for now) setting the test environment using [e2e script from qm software](https://github.com/containers/qm/tree/main/tests/e2e).  
In the future, we might provide users flags in the software to make it more dynamic.

```
git clone https://github.com/containers/qm/ && cd qm
cd tests/e2e
./run-test-e2e
```
After that, you can just run the dashboard-tui with the same user run-test-e2e was executed.

```
./car-dashboard
```

## Technologies
containers, nested containers, podman, qm, hirte, cgroupv2, python, Fedora and much more!

## Want to contribute?
Send us your patches, we appreciate all help!
