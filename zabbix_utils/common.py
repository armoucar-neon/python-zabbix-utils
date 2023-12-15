# zabbix_utils
#
# Copyright (C) 2001-2023 Zabbix SIA
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software
# is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import re
import json
import zlib
import struct
from typing import Match, Union
from textwrap import shorten
from logging import Logger
from socket import socket


class ModuleUtils():

    # Hidding mask for sensitive data
    HIDING_MASK = "*" * 8

    # The main php-file of Zabbix API
    JSONRPC_FILE = 'api_jsonrpc.php'

    # Methods working without auth token
    UNAUTH_METHODS = ('apiinfo.version', 'user.login', 'user.checkAuthentication')

    # Methods returning files contents
    FILES_METHODS = ('configuration.export',)

    # List of private fields and regular expressions to hide them
    PRIVATE_FIELDS = {
        "token": "[A-Za-z0-9]+",
        "auth": "[A-Za-z0-9]+",
        "sessionid": "[A-Za-z0-9]+",
        "password": "[^'\"]+",
        "result": "(?!(zabbix_export|[0-9.]{5}))[A-Za-z0-9]+",
    }

    @classmethod
    def check_url(cls, url: str) -> str:
        """Check url completeness

        Args:
            url (str): Unchecked URL of Zabbix API

        Returns:
            str: Checked URL of Zabbix API
        """

        if not url.endswith(cls.JSONRPC_FILE):
            url += cls.JSONRPC_FILE if url[-1] == '/' else '/' + cls.JSONRPC_FILE
        if not url.startswith('http'):
            url = 'http://' + url

        return url

    @classmethod
    def mask_secret(cls, string: str, show_len: int = 4) -> str:
        """Replace the most part of string to hiding mask.

        Args:
            string (str): Raw string with without hiding.
            show_len (int, optional): Number of signs shown on each side of the string. \
Defaults to 4.

        Returns:
            str: String with hiding part.
        """

        # If show_len is 0 or the length of the string is smaller than the hiding mask length
        # and show_len from both sides of the string, return only hiding mask.
        if show_len == 0 or len(string) <= (len(cls.HIDING_MASK) + show_len*2):
            return cls.HIDING_MASK

        # Return the string with the hiding mask, surrounded by the specified number of characters
        # to display on each side of the string.
        return f"{string[:show_len]}{cls.HIDING_MASK}{string[-show_len:]}"

    @classmethod
    def hide_private(cls, message: str, fields: dict = None) -> str:
        """Hide private data Zabbix info (e.g. token, password)

        Args:
            message (str): Message text with private data.
            fields (dict): Dictionary of private fields and their seeking regexps.

        Returns:
            str: Message text without private data.
        """

        private_fields = fields if fields else cls.PRIVATE_FIELDS

        def gen_repl(match: Match):
            return cls.mask_secret(match.group(0))

        pattern = re.compile(
            r"|".join([rf"(?<=\"{f}\":\s\"){r}" for f, r in private_fields.items()])
        )

        return re.sub(pattern, gen_repl, message)


class ZabbixProtocol():

    ZABBIX_PROTOCOL = b'ZBXD'

    HEADER_SIZE = 13

    @classmethod
    def __prepare_request(cls, data: Union[bytes, str, dict]) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode("utf-8")
        if isinstance(data, list) or isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False).encode("utf-8")
        raise TypeError("Unsupported data type, only 'bytes', 'str' or 'dict' is expected")

    @classmethod
    def create_packet(cls, payload: Union[bytes, str, dict],
                      log: Logger, compression: bool = False) -> bytes:
        """Create a packet for sending via the Zabbix protocol.

        Args:
            payload (Union[bytes, str, dict]): Payload of the future packet
            log (Logger): Logger object
            compression (bool, optional): Compression use flag. Defaults to `False`.

        Returns:
            bytes: Generated Zabbix protocol packet
        """

        request = cls.__prepare_request(payload)

        log.debug('Request data: %s', shorten(request.decode("utf-8"), 200, placeholder='...'))

        # 0x01 - Zabbix communications protocol
        flags = 0x01
        datalen = len(request)
        reserved = 0

        if compression:
            # 0x02 - Using packet compression mode
            flags |= 0x02
            reserved = datalen
            request = zlib.compress(request)
            datalen = len(request)

        header = struct.pack('<4sBII', cls.ZABBIX_PROTOCOL, flags, datalen, reserved)
        packet = header + request

        log.debug('Content of the packet: %s', shorten(str(packet), 200, placeholder='...'))

        return packet

    @classmethod
    def receive_packet(cls, conn: socket, size: int, log: Logger) -> bytes:
        """Receive a Zabbix protocol packet.

        Args:
            conn (socket): Opened socket connection
            size (int): Expected packet size
            log (Logger): Logger object

        Returns:
            bytes: Received packet content
        """
        buf = b''

        while len(buf) < size:
            chunk = conn.recv(size - len(buf))
            if not chunk:
                log.debug("Socket connection was closed before receiving expected amount of data.")
                break
            buf += chunk

        return buf

    @classmethod
    def parse_packet(cls, conn: socket, log: Logger, exception) -> str:
        """Parse a received Zabbix protocol packet.

        Args:
            conn (socket): Opened socket connection
            log (Logger): Logger object
            exception: Exception type

        Raises:
            exception: Depends on input exception type

        Returns:
            str: Body of the received packet
        """

        response_header = cls.receive_packet(conn, cls.HEADER_SIZE, log)
        log.debug('Zabbix response header: %s', response_header)

        if (not response_header.startswith(cls.ZABBIX_PROTOCOL) or
                len(response_header) != cls.HEADER_SIZE):
            log.debug('Unexpected response was received from Zabbix.')
            raise exception('Unexpected response was received from Zabbix.')

        flags, datalen, reserved = struct.unpack('<BII', response_header[4:])

        # 0x01 - Zabbix communications protocol
        if not flags & 0x01:
            raise exception(
                'Unexcepted flags were received. '
                'Check debug log for more information.'
            )
        # 0x04 - Using large packet mode
        if flags & 0x04:
            raise exception(
                'A large packet flag was received. '
                'Current module doesn\'t support large packets.'
            )
        # 0x02 - Using packet compression mode
        if flags & 0x02:
            response_body = zlib.decompress(cls.receive_packet(conn, datalen, log))
        else:
            response_body = cls.receive_packet(conn, datalen, log)

        return response_body.decode("utf-8")
