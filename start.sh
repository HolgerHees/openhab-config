#!/bin/sh

echo Launching the openHAB runtime...

DIRNAME=`dirname "$0"`

#export JAVA_HOME="/dataDisk/java/"
export JAVA_OPTS="${JAVA_OPTS} -Dgnu.io.rxtx.SerialPorts=/dev/ttyOpenHabLueftung:/dev/ttyOpenHabFunk -Xbootclasspath/a:/dataDisk/jython/jython.jar -Dpython.home=/dataDisk/jython -Dpython.path=/dataDisk/openhab-runtime/python"
#export JYTHONPATH="${DIRNAME}/python"
export OPENHAB_HOME="${DIRNAME}"
export OPENHAB_CONF="${DIRNAME}/conf"
export OPENHAB_RUNTIME="${DIRNAME}/runtime"
export OPENHAB_USERDATA="${DIRNAME}/userdata"
export OPENHAB_LOGDIR="/dataDisk/var/log/openhab"

exec "${DIRNAME}/runtime/bin/karaf" "${@}"
