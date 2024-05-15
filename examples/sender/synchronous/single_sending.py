# Copyright (C) 2001-2023 Zabbix SIA
#
# Zabbix SIA licenses this file to you under the MIT License.
# See the LICENSE file in the project root for more information.

from datetime import datetime, timedelta
import json
from zabbix_utils import Sender
import requests


# Zabbix server/proxy details for Sender
ZABBIX_SERVER = {
    "server": "zabbix.in.neoncorp.com.br",  # Zabbix server/proxy IP address or hostname
    "port": 443,  # Zabbix server/proxy port for Sender
}

# Create an instance of the Sender class with the specified server details
sender = Sender(**ZABBIX_SERVER)


def get_metrics_for_date(reference_date):
    url = "https://neon--gugelmin.in.neoncorp.com.br/api/metrics/usage-metrics"
    headers = {"Content-Type": "application/json"}
    params = {"reference_date": reference_date}

    response = requests.get(url, headers=headers, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        resp = response.json()
        # resp["reference_date"] = datetime.strptime(reference_date, "%Y-%m-%d").timestamp()
        return resp
    else:
        raise Exception(f"Failed to get metrics for date {reference_date}")


start_date = datetime.strptime("2024-04-23", "%Y-%m-%d")
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

while start_date < today:
    d = start_date.strftime("%Y-%m-%d")
    start_date_seconds = int(start_date.timestamp())
    print(f"Sending metrics for date {d}")
    metrics = get_metrics_for_date(d)

    try:
        response = sender.send_value("API - Gugelmin", "gugelmin_metrics", json.dumps(metrics), start_date_seconds, 0)
    except Exception as e:
        print(f"Failed to send metrics for date {d}: {e}")
        break

    # Check if the value sending was successful
    if response.failed == 0:
        # Print a success message along with the response time
        print(f"Value sent successfully in {response.time}")
    else:
        # Print a failure message
        print("Failed to send value")

    start_date += timedelta(days=1)
    break


# zabbix_sender -z zabbix.in.neoncorp.com.br -s "API - Gugelmin" -k gugelmin_metrics -o 43