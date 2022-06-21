import logging
import time

import osc


def __tests():
    logging.basicConfig(level=logging.DEBUG)

    @osc.receive(host="127.0.0.1", port=19994, address="/some/addr")
    def receive_something(address: str, message):
        print(f"I got a message: '{message}' from '{address}'.")
        time.sleep(0.5)
        # Loop!
        send_something(message)

    @osc.send(host="127.0.0.1", port=19994)
    def send_something(message: str):
        return "/some/addr", message

    osc.start_servers()  # Start listening for messages
    send_something("Hey this is something")
    osc.wait()  # Don't exit


if __name__ == "__main__":
    __tests()
