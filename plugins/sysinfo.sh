#!/bin/bash
##############################################################
# Basic system info for the thistle.CommandOutputVarMonitor
# variables:
#   CPU_USAGE (%) : uses top -b -n1
#   MEM_USAGE (%) : uses free
#   DISK_USAGE_[mount point name] (%) : uses df
#     i.e) DISK_USAGE_/, DISK_USAGE_/var
# 
# Author: Yusuke Inuzuka <yuin@inforno.net>
##############################################################

export LANG=C
FREE=`free`
TOTAL_MEM=`echo "${FREE}" | grep Mem | awk '{print $2}'`
UNUSED_MEM=`echo "${FREE}" | grep cache: | awk '{print $4}'`
USED_MEM=`expr ${TOTAL_MEM} - ${UNUSED_MEM}`
MEM_USAGE=`echo ${USED_MEM} ${TOTAL_MEM} | awk '{ print int($1 / $2 * 100) }'`

TOP=`top -b -n1`
CPU_USAGE=`echo "${TOP}" | grep '^Cpu' | sed -e s/%us,// | awk '{print int($2)}'`

echo "CPU_USAGE=${CPU_USAGE}"
echo "MEM_USAGE=${MEM_USAGE}"
OLD_IFS=$IFS
IFS=$'\n'
DF_LINES=(`df -P`)
IFS=${OLD_IFS}
i=0
for LINE in "${DF_LINES[@]}"; do
  if [ $i -eq 0 ]; then
    i=`expr $i + 1`
  else
    DISK_USAGE=`echo "${LINE}" | sed -e s/%// | awk '{print $5}'`
    MOUNT_NAME=`echo "${LINE}" | awk '{print $6}'`
    echo "DISK_USAGE_${MOUNT_NAME}=${DISK_USAGE}"
  fi
done
IFS=${OLD_IFS}

