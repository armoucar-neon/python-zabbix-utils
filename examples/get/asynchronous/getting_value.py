# Copyright (C) 2001-2023 Zabbix SIA
#
# Zabbix SIA licenses this file to you under the MIT License.
# See the LICENSE file in the project root for more information.

import sys
import json
import asyncio
from zabbix_utils import AsyncGetter


async def main():
    """
    The main function to perform asynchronous tasks.
    """

    # Create a AsyncGetter instance for querying Zabbix agent
    agent = AsyncGetter(host='127.0.0.1', port=10050)

    # Send a Zabbix agent query for network interface discovery
    resp = await agent.get('net.if.discovery')

    # Check if there was an error in the response
    if resp.error:
        # Print the error message
        print("An error occurred while trying to get the value:", resp.error)
        # Exit the script
        sys.exit()

    try:
        # Attempt to parse the JSON response
        resp_list = json.loads(resp.value)
    except json.decoder.JSONDecodeError:
        print("Agent response decoding fails")
        # Exit the script if JSON decoding fails
        sys.exit()

    # Iterate through the discovered network interfaces and print their names
    for interface in resp_list:
        print(interface['{#IFNAME}'])

# Run the main coroutine
asyncio.run(main())
