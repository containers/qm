#!/bin/bash



# shellcheck disable=SC1091

. ../common/prepare.sh

disk_cleanup
prepare_test
reload_config

#Preset with expected value the variable.
expected_value="setenforce:  security_setenforce() failed:  Permission denied"

# Get setenforce 0 permission denied from qm.
setenforce_0=$(podman exec qm /bin/bash -c \
               "podman exec qm setenforce 0 2>&1" | grep -c "setenforce:  security_setenforce() failed:  Permission denied")

echo "This is what qm returns $setenforce_0"

if [ "$setenforce_0" -eq "$expected_value" ];then
   info_message "Attempt to change Selinux enforcement to 0 denied successfully inside QM container."
   exit 0
fi





# This is my script that I use for the different repo
# I would definitely check how other test.sh look in th qm repo, get some inspiration (for example here)

# Specify files that you need and those files are not in your directory
# In your case it's prepare.sh
#. $(dirname $(readlink --canonicalize $0))/../../common.sh

#You need some test image that podman will use (this one is created in common.sh, so I guess yours will be in prepare.sh - look at the prepare.sh)
#For the test image you can define some parameters like what program you need there (procps in my case)
#test_image=$(build_container_image procps)

# Echo - see some parameters or messages in the terminal while running the script.
#echo "Starting container with interference:."

# Podman run is basic command how to run a container
# But you need to some parameters to configure it
# --detach is parameter for podman (yours will be different, depends on what you need from the container, see podman manual)
# $CONTAINER_PARAMS are parameters that are defined somwhere for example in the common.sh where the test image is created 
# $CONFUSION_OPTS are parameters that I define for my test and are written somewhere else, in my case $CONFUSION_OPTS --pids-limit=100 
# --name confusion is the name of the container, that you need to specify
# test_image is the image that you need for your container
#podman run --detach $CONTAINER_PARAMS $CONFUSION_OPTS --name confusion $test_image

# podman cp copies your script .sh (in my case forkbomb.sh) to the container (you have to specify the name of the container, in my case confusion)
#podman cp forkbomb.sh confusion:/usr/local/forkbomb.sh
#echo "Starting forkbomb in the container."
# podman exec is for executing some command in your container (in my case ps -e | wc -l)
# -it are parameters for podman, see manual, confusion is name of the container, sh is bash -c is parameter for bash, see bash manual)
#podman exec -it confusion sh -c "ps -e | wc -l"
# podman exec will run your .sh script (in my case forkbomb.sh), >/dev/null 2>&1 means tah you wont see the output in your terminal
#podman exec --detach confusion '/usr/local/forkbomb.sh' >/dev/null 2>&1


# Basics
# podman run -podman_parameters container_parameters your_parameters --name container_name image
# podman cp bash_script.sh container_name:/where_is_the_script_you_need\
# podman exec -podman_parameters container_name bash bash_parameter 'bash_command'
# podman exec -podman_parameters container_name 'your_script'

