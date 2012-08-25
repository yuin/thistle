#!/bin/bash
##############################################################
# Basic system info for the thistle.CommandOutputVarMonitor
# variables:
#   CPU_USAGE (%) : uses top -b -n1
#   LOAD_AVERAGE_[1|5|15] : uses top -b -n1, such as "0.01"
#   MEM_USAGE (%) : uses free
#   SWAP_USAGE (%) : uses free
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

TOTAL_SWAP=`echo "${FREE}" | grep Swap | awk '{print $2}'`
USED_SWAP=`echo "${FREE}" | grep Swap | awk '{print $3}'`
SWAP_USAGE=`echo ${USED_SWAP} ${TOTAL_SWAP} | awk '{ print int($1 / $2 * 100) }'`
if [ ${TOTAL_SWAP} -eq 0 ]; then
  SWAP_USAGE=0
fi


TOP=`top -b -n1`
CPU_USAGE=`echo "${TOP}" | grep '^Cpu' | sed -e s/%us,// | awk '{print int($2)}'`
LOAD_AVERAGES=(`echo "${TOP}" | grep 'load average' | awk '{gsub(/,/, "")}{i=NF-2;j=NF-1; print $i " " $j " " $NF}'`)

echo "CPU_USAGE=${CPU_USAGE}"
echo "LOAD_AVERAGE_1=${LOAD_AVERAGES[0]}"
echo "LOAD_AVERAGE_5=${LOAD_AVERAGES[1]}"
echo "LOAD_AVERAGE_15=${LOAD_AVERAGES[2]}"
echo "MEM_USAGE=${MEM_USAGE}"
echo "SWAP_USAGE=${SWAP_USAGE}"
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

which iostat > /dev/null 2>&1
if [ $? -eq 0 ]; then
  OLD_IFS=$IFS
  IFS=$'\n'
  IOSTAT_LINES=(`iostat -xk 15 2 | awk 'BEGIN {count=0} /^Device/ { count = count+1 } count > 1 { print $0 }' | grep -v Device`)
  IFS=${OLD_IFS}
  for LINE in "${IOSTAT_LINES[@]}"; do
    DEVICE_NAME=`echo "${LINE}" | awk '{print $1}'`
    DEVICE_RKBS=`echo "${LINE}" | awk '{print $6}'`
    DEVICE_WKBS=`echo "${LINE}" | awk '{print $7}'`
    DEVICE_UTIL=`echo "${LINE}" | awk '{print $NF}'`
    echo "DEV_RKBS_${DEVICE_NAME}=${DEVICE_RKBS}"
    echo "DEV_WKBS_${DEVICE_NAME}=${DEVICE_WKBS}"
    echo "DEV_UTIL_${DEVICE_NAME}=${DEVICE_UTIL}"
  done
fi
