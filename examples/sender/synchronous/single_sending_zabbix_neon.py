import json
import os
from datetime import datetime

from zabbix_utils import Sender

# Zabbix server/proxy details for Sender
ZABBIX_SERVER = {
    "server": "zabbix.in.neoncorp.com.br",  # Zabbix server/proxy IP address or hostname
    "port": 443,  # Zabbix server/proxy port for Sender
}

# Create an instance of the Sender class with the specified server details
sender = Sender(**ZABBIX_SERVER)

data_dir = "./examples/sender/synchronous/data"
file_list = sorted(os.listdir(data_dir))

for file_name in file_list:
    file_path = os.path.join(data_dir, file_name)
    date_str = file_name.split("/")[-1].split(".")[0]
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    start_date_seconds = int(date_obj.timestamp())

    with open(file_path, "r") as metric:
        try:
            response = sender.send_value(
                "API - Gugelmin", "gugelmin_metrics", json.dumps(metric.read()), start_date_seconds, 0
            )

            if response.failed == 0:
                print(f"Value sent successfully in {response.time}")
            else:
                print("Failed to send value")
        except Exception as e:
            print(f"Failed to send metrics for date {date_str}: {e}")

# zabbix_sender -z zabbix.in.neoncorp.com.br -s "API - Gugelmin" -k gugelmin_metrics -o 43
