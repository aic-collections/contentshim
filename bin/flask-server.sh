#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

case "$1" in
        start)
            cd $DIR/../app/
            python server.py --config $DIR/../config/local.yaml &
            echo $! > $DIR/../tmp/flask-server.pid
            cd $DIR
            echo "Waiting for Flask-server to start."
            sleep 5
            ;;
        stop)
            PID=`cat $DIR/../tmp/flask-server.pid`
            kill $PID
            rm $DIR/../tmp/flask-server.pid
            ;;
       
        *)
            echo $"Usage: $0 {start|stop}"
            exit 1
esac



