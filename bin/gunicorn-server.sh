#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

case "$1" in
        start)
            cd $DIR/../
            gunicorn --config $DIR/../config/gunicorn_prod.py app.wsgi
            cd $DIR
            echo "Waiting for Gunicorn-server to start."
            sleep 5
            ;;
        stop)
            PID=`cat $DIR/../tmp/gunicorn-server.pid`
            kill $PID
            rm $DIR/../tmp/gunicorn-server.pid
            ;;
       
        *)
            echo $"Usage: $0 {start|stop}"
            exit 1
esac



