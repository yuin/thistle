#!/bin/bash

export PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

cd `dirname $0`
BASE_DIR=`pwd`
which chkconfig > /dev/null 2>&1
if [ $? -eq 0 ]; then
  CHKCONFIG=1
else
  CHKCONFIG=0
fi

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
    if [ $CHKCONFIG -eq 1 ]; then
      echo "chkconfig --add thistle"
      chkconfig --add thistle
      echo "chkconfig thistle on"
      chkconfig thistle on
    else
      echo "update-rc.d thistle defaults 99 01"
      update-rc.d thistle defaults 99 01
    fi
  fi
}

uninstall () {
  echo "rm -f /usr/local/bin/thistle"
  rm -f /usr/local/bin/thistle

  echo "rm -rf /var/log/thistle"
  rm -rf /var/log/thistle

  if [ $CHKCONFIG -eq 1 ]; then
    echo "chkconfig thistle off"
    chkconfig thistle off
    echo "chkconfig --del thistle"
    chkconfig --del thistle
    echo "rm -f /etc/init.d/thistle"
    rm -f /etc/init.d/thistle
  else
    echo "rm -f /etc/init.d/thistle"
    rm -f /etc/init.d/thistle
    echo "update-rc.d thistle remove"
    update-rc.d thistle remove
  fi

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
