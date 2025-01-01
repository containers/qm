1. Create a dir in the python site-packages for QM

```console
sudo mkdir -p /usr/lib/python3.13/site-packages/qm/
```

1.1 Copy library to it site-library for the specific user, in the case
   bellow will be available only for root user.

```console
sudo cp __init__.py /usr/lib/python3.13/site-packages/qm/
```

1.2 Test it

Source code:

```python
from qm import QM

def main():
    # Initialize the QM class
    qm_manager = QM()

    # Example: Start a container named 'qm'
    container_name = "qm"
    if qm_manager.start_container(container_name):
        print(f"Container '{container_name}' started successfully.")
    else:
        print(f"Failed to start container '{container_name}'.")

    # Example: Check the status of the container
    status = qm_manager.container_status(container_name)
    #print(f"Status of container '{container_name}': {status}")
    print(f"Status of container {status}")

    # Example: Count the number of running containers
    running_count = qm_manager.count_running_containers()
    print(f"Number of running containers: {running_count}")

    # Example: Stop the container
    if qm_manager.stop_container(container_name):
        print(f"Container '{container_name}' stopped successfully.")
    else:
        print(f"Failed to stop container '{container_name}'.")

    # Example: Check if the QM service is installed
    if qm_manager.is_qm_service_installed():
        print("QM service is installed.")
    else:
        print("QM service is not installed.")

    # Example: Check if the QM service is running
    if qm_manager.is_qm_service_running():
        print("QM service is running.")
    else:
        print("QM service is not running.")

if __name__ == "__main__":
    main()
```

Testing:

```console
$ sudo ./reading_information
QM service is installed.
QM service is running.
```
