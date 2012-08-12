#!/bin/bash

cd `dirname $0`
BASE_DIR=`pwd`

install () {
  if [ ! -e /usr/local/bin/thistle ]; then
    echo "ln -s ${BASE_DIR}/thistle.py /usr/local/bin/thistle"
    chmod +x ${BASE_DIR}/thistle.py
    ln -s ${BASE_DIR}/thistle.py /usr/local/bin/thistle
  fi
  
  if [ ! -e /var/log/thistle ]; then
    echo "mkdir /var/log/thistle"
    mkdir /var/log/thistle
  fi
  
  if [ ! -e /etc/thistle/ ]; then
    echo "mkdir /etc/thistle"
    mkdir /etc/thistle
    echo "cp ${BASE_DIR}/user/config.py /etc/thistle/config.py"
    cp ${BASE_DIR}/user/config.py /etc/thistle/config.py
  fi
  
  if [ ! -e /etc/init.d/thistle ]; then
    echo "cp ${BASE_DIR}/thistle /etc/init.d/thistle"
    cp ${BASE_DIR}/thistle /etc/init.d/thistle
    echo "update-rc.d thistle defaults"
    update-rc.d thistle defaults
  fi
}

uninstall () {
  echo "rm -f /usr/local/bin/thistle"
  rm -f /usr/local/bin/thistle

  echo "rm -rf /var/log/thistle"
  rm -rf /var/log/thistle

  echo "rm -f /etc/init.d/thistle"
  rm -f /etc/init.d/thistle

  echo "update-rc.d thistle remove"
  update-rc.d thistle remove

}



CMD=$1
usage () {
  echo "$0: [install | uninstall]"
}
shift
ARGS="$*"
case "${CMD}" in
  install)
    install
    ;;
  uninstall)
    uninstall
    ;;
  *)
    usage
    exit 1
esac
