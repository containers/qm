#!/bin/bash -euvx

# shellcheck disable=SC1091

. ../common/prepare.sh

export QM_HOST_REGISTRY_DIR="/var/qm/lib/containers/registry"
export QM_REGISTRY_DIR="/var/lib/containers/registry"

disk_cleanup
prepare_test
reload_config

#Here $timper is allowed percentage delay and $ploss is allowed packet loss
timper=5
ploss=0
echo " "
echo "Creating Containers*"
echo " "
podman run -d --name orderly stream9-stress
podman run -d --name confusion stream9-stress
podman run -d --name partner stream9-stress
podman inspect orderly | grep IPAddress | tail -1 | awk '{print $NF}' |  sed 's/"//g' | sed 's/,//g'
ipadd=$(podman inspect orderly | grep IPAddress | tail -1 | awk '{print $NF}' |  sed 's/"//g' | sed 's/,//g')
STRESS_CMD=$(printf "$1" $ipadd)
partneripadd=$(podman inspect partner | grep IPAddress | tail -1 | awk '{print $NF}' |  sed 's/"//g' | sed 's/,//g')
echo " "
echo "*****Orderly pings partner 10 times in ideal conditions*****"
echo " "
idealtime=$(podman exec -it orderly sh -c "ping -c 10 $partneripadd" | grep packet| tail -1 | awk '{print $NF}' | sed 's/[ms]//g')
sleep 2
echo -e "\e[1;35m Time taken to ping in ideal condition is $idealtime ms \e[0m"
echo "*****Confusion container creates stress condition, while orderly pings partner 10 times*****"
echo " "
podman exec -it confusion sh -c "$STRESS_CMD" &
sleep 5
understresstime=$(podman exec -it orderly sh -c "ping -c 10 $partneripadd"  &>> log && cat log | grep packet | tail -1 | awk '{print $NF}'| sed 's/[ms]//g')
sar -n EICMP 1 5 &
echo ""
sleep 10
pkill ping
echo  -e "\e[1;35m Time taken to ping target in while in a heavy traffic is $understresstime ms \e[0m"
increase=$(awk -v t1="$idealtime" -v t2="$understresstime" 'BEGIN{printf "%.0f", (t2-t1)/t1 * 100}')
sleep 1
echo ""
echo -e "\e[1;32m Percentage increase in time taken is $increase percent \e[0m"
echo ""
if [[ $increase -gt $timper ]]
then
  echo -e "\e[1;31m Interference is present - Delay in pinging target when under stress \e[0m"
  exit 1
else
  echo -e "\e[1;32m Interference is not present - No Delay in pinging target under stress condition created by Confusion Container \e[0m"
fi
echo ""
loss=$(cat log | grep packet | tail -1 | awk '{print $6}' | sed 's/%//g')
echo -e "\e[1;32m Packet loss is $loss percent  \e[0m"
if [[ $loss -gt $ploss ]]
then
  echo -e "\e[1;31m Interference is present - presence of packet loss \e[0m"
  exit 1
else
        echo -e "\e[1;32m Interference is not present - No packet loss \e[0m"
fi
./cleanup.sh
rm -f log
