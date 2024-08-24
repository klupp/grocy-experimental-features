#!/bin/sh

project_dir="$( cd "$( dirname "$0" )" && pwd )"

OUTFILE=/lib/systemd/system/grocyexperimentalfeatures.service
EXECUTE="cd $project_dir && conda activate grocy-experimental-features && uvicorn main:app --port 5000 --reload"
sudo out=$OUTFILE exec="$EXECUTE" sh -c 'cat << EOF > $out
[Unit]
Description=Grocy Experimental Features Server
After=multi-user.target

[Service]
Type=idle
Restart=on-failure
User=root
ExecStart=/bin/bash -c "$exec"

[Install]
WantedBy=multi-user.target
EOF'

sudo chmod 644 /lib/systemd/system/grocyexperimentalfeatures.service

sudo systemctl daemon-reload
sudo systemctl enable grocyexperimentalfeatures.service
sudo systemctl start grocyexperimentalfeatures.service
service_status=$(sudo systemctl status grocyexperimentalfeatures.service)
echo "$service_status"
