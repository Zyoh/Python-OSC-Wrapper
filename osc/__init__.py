#  MIT License
#
#  Copyright (c) 2022 Zoe <zoe@zyoh.ca>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
#

import logging
import threading
import time
from types import FunctionType
from typing import Optional, Callable, Any, cast

from pythonosc import udp_client, osc_server, dispatcher

# Message type.
Message = Optional[int | float | bytes | str | bool | tuple | list]

__Servers = dict[
    tuple[str, int], dict[
        str, Callable
    ]
]


def __servers(
        update: Optional[dict] = None,
        /, *,
        __servers: __Servers = {}
) -> __Servers:
    """
    Stores server data.
    I know this is a really weird way of doing it but it's funny to me that it works so I'm keeping it for now.
    Parameters
    ----------
    update: Optional[dict]
        Updates server data, if provided.
    __servers: __Servers
        This stores the data.

    Returns
    -------
    __servers: __Servers
        Returns server data.
    """
    if update is not None:
        __servers.update(update)

    return __servers


def send(
        host: str,
        port: int
) -> Callable[
    [Callable],
    Callable[
        [Any],
        tuple[str, Message]
    ]
]:
    """
    Sends the function result as OSC data. Function must return 'tuple[str, Message]'.
    Parameters
    ----------
    host: str
        IP address of the target.
    port: int
        Listening port of the target.

    Returns
    -------
    Callable[                   <-- Decorator function.
        [Callable],                 <-- Original function.
        Callable[                   <-- New function.
            [Any],                      <-- Accepts any arguments.
            tuple[str, Message]         <-- Returns OSC compatible data.
        ]]

    """

    def decorator(f: Callable) -> Callable[[Any], tuple[str, Message]]:
        def wrapper(*args, **kwargs) -> tuple[str, Message]:
            # Use function result as packet.
            packet: tuple[str, Message] = f(*args, **kwargs)

            logging.debug(f"Sending {packet} -> {host}:{port}")
            # Send packet using OSC client.
            udp_client.SimpleUDPClient(host, port).send_message(*packet)
            return packet

        return wrapper

    return decorator


def receive(
        host: str,
        port: int,
        address: Optional[str] = None,
        addresses: Optional[list[str]] = None,
) -> Callable[
    [Callable],
    Callable[
        [
            str,
            Message
        ],
        Any
    ]
]:
    """
    Binds the function to an OSC server.
    At least one address must be provided.
    Parameters
    ----------
    host: str
        IP address to listen on.
    port: int
        Port to listen on.
    address: Optional[str]
        Server will call this function when receiving data on this address.
    addresses: Optional[list[str]]
        Server will call this function when receiving data on these addresses.

    Returns
    -------
    Callable[                   <-- Decorator function.
        [Callable],                 <-- Original function.
        Callable[                   <-- New function.
            [
                addr: str,              <-- Address received.
                message: Message        <-- Message received.
            ],
            Any                         <-- Returns anything.
        ]]

    """
    if address is None and addresses is None:
        raise ValueError("Must specify an address.")

    def decorator(f: Callable) -> Callable:
        # Bound function must accept address and message as arguments.
        def wrapper(addr: str, message: Message = None) -> Any:
            return f(addr, message)

        # Consolidate addresses into a list.
        _addrs = []
        if address is not None:
            _addrs.append(address)
        if addresses is not None:
            _addrs.extend(addresses)

        # Update servers dictionary with new host, addresses, and binds.
        for _addr in _addrs:
            __servers({
                (host, port): {
                    _addr: f
                }
            })

        return wrapper

    return decorator


def start_servers(blocking: bool = False) -> None:
    """
    Starts servers for every listening function.
    Parameters
    ----------
    blocking: bool
        Halts program execution if True.

    """
    for (host, port), binds in __servers().items():
        d = dispatcher.Dispatcher()
        for address, callback in binds.items():
            # Cast to FunctionType since python-osc doesn't like Callable.
            d.map(address, cast(FunctionType, callback))
        server = osc_server.ThreadingOSCUDPServer((host, port), d)
        # Run async.
        threading.Thread(target=lambda: server.serve_forever(), daemon=True).start()

    if blocking:
        wait()


def wait() -> None:
    """
    Halt program execution.

    """
    try:
        while 1:
            time.sleep(1e6)
    except KeyboardInterrupt:
        pass
