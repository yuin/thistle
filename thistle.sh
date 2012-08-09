#!/bin/bash

cd `dirname $0`
BASE_DIR=`pwd`
THISTLE="python thistle.py"
PID_FILE="${BASE_DIR}/dat/thistle.pid"
CONF_FILE="${BASE_DIR}/user/config.py"

start(){
  if pid=`status` >/dev/null ;then
    echo "\`thistle' is already running: $pid"
    exit 1
  fi
  echo -n "Starting thistle: "
  ${THISTLE} ${ARGS} -c ${CONF_FILE} start &
  bgid=$!
  jobid=`jobs -l | grep -e " ${bgid} " | awk '{print $1}' | tr -d "[]+-"`
  expr ${jobid} + 1 > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo "NG"
    ${THISTLE} -h
    exit $?
  fi

  disown %${jobid}
  sleep 3
  if [ `status` = "NG" ]; then
    echo "NG"
    ${THISTLE} -h
    exit $?
  else
    echo "OK"
    exit 0
  fi
}

stop(){
  if pid=`status` >/dev/null ;then
    echo -n "Stopping thistle: "
    ${THISTLE} ${ARGS} -c ${CONF_FILE} stop
    [ $? -ne 0 ] && echo NG || echo OK
    exit $?
  fi
  echo "Not runnning"
  exit 1
}

status(){
  if [ -s $PID_FILE ];then
    pid=`cat $PID_FILE`
    if [ -d /proc/$pid ];then
      echo "$pid"
      return 0
    fi
  fi
  echo "NG"
  return 1
}

CMD=$1
shift
ARGS="$*"
case "${CMD}" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  status)
    status
    ;;
  *)
    ${THISTLE} -h
    exit 1
esac
