import asyncio
import time

import common
import logging
import argparse


class EchoServerHandler(common.Handler):
    """
    Defines echo server protocol
    """
    def __init__(self, server, loop):
        super().__init__()
        self.server = server
        self.loop = loop

    def connection_made(self, transport):
        """
        Defines the process of accepting a connection

        :param transport: socket to write data on
        """
        peername = transport.get_extra_info('peername')
        logging.info("SSL cipher: {}".format(transport.get_extra_info('cipher')))
        logging.info('Connection from {}'.format(peername))
        self.transport = transport
        self.name = None


    def process_request(self, command, data):
        """
        Defines commands for servers

        :param command: Received command from client.
        :param data: Received data from client.
        :return: message to send
        """
        if command == "echo-c":
            return self.echo_master(data)
        elif command == 'hello':
            return self.hello(data)
        else:
            return super().process_request(command, data)


    def echo_master(self, data):
        return 'ok-m ', data


    def hello(self, data):
        """
        Adds a client's data to global clients dictionary

        :param data: client's data -> name
        :return: successful result
        """
        if data in self.server.clients:
            logging.error("Client {} already present".format(data))
            self.transport.close()
            return 'err', 'Client already present'
        else:
            self.server.clients[data] = self
            self.name = data
            return 'ok', 'Client {} added'.format(data)


    def process_response(self, command, payload):
        """
        Defines response commands for servers

        :param command: response command received
        :param payload: data received
        :return:
        """
        if command == 'ok-c':
            return "Sucessful response from client: {}".format(payload)
        else:
            return super().process_response(command, payload)


    def connection_lost(self, exc):
        """
        Defines process of closing connection with the server

        :param exc:
        :return:
        """
        if self.name:
            logging.info("The client '{}' closed the connection".format(self.name))
            del self.server.clients[self.name]
        else:
            logging.error("Error during handshake with incoming client.")


class EchoServer:
    """
    Defines an asynchronous echo server.
    """
    def __init__(self, performance_test, concurrency_test):
        self.clients = {}
        self.performance = performance_test
        self.concurrency = concurrency_test

    async def echo(self):
        while True:
            for client_name, client in self.clients.items():
                logging.debug("Sending echo to client {}".format(client_name))
                logging.info(await client.send_request('echo-m', 'hello {} from server'.format(client_name)))
            await asyncio.sleep(3)

    async def performance_test(self):
        while True:
            for client_name, client in self.clients.items():
                before = time.time()
                response = await client.send_request('echo', 'a'*self.performance)
                after = time.time()
                logging.info("Received size: {} // Time: {}".format(len(response), after - before))
            await asyncio.sleep(3)

    async def concurrency_test(self):
        while True:
            for i in range(self.concurrency):
                before = time.time()
                for client_name, client in self.clients.items():
                    response = await client.send_request('echo', 'concurrency {} client {}'.format(i, client_name))
                after = time.time()
                logging.info("Time sending {} messages: {}".format(self.concurrency, after - before))
                await asyncio.sleep(10)

    async def start(self):
        # Get a reference to the event loop as we plan to use
        # low-level APIs.
        loop = asyncio.get_running_loop()

        server = await loop.create_server(lambda: EchoServerHandler(server=self, loop=loop), '0.0.0.0', 8888)
        logging.info('Serving on {}'.format(server.sockets[0].getsockname()))

        async with server:
            # use asyncio.gather to run both tasks in parallel
            await server.serve_forever()


async def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--performance_test', default=0, type=int, dest='performance_test',
                        help="Perform a performance test against all clients. Number of bytes to test with.")
    parser.add_argument('-c', '--concurrency_test', default=0, type=int, dest='concurrency_test',
                        help="Perform a concurrency test against all clients. Number of messages to send in a row to each client.")
    args = parser.parse_args()

    server = EchoServer(args.performance_test, args.concurrency_test)
    await server.start()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    logging.info("SIGINT received. Bye!")
