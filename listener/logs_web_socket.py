import logging
import asyncio
import tornado
import tornado.websocket


class WebsocketStreamHandler(logging.StreamHandler):
    def __init__(self, websocket):
        super().__init__(self)
        self.websocket = websocket
        self.loop = websocket.loop

    def emit(self, record):
        self.websocket.send(record)

    def write(self, record):
        record = record.rstrip()
        if record:  # and: not self.websocket.closed:
            self.loop.call_soon_threadsafe(self.websocket.write_message, record)

    def flush(self):
        pass


class LogsWebSocketHandler(tornado.websocket.WebSocketHandler):
    """
    Note that Tornado uses asyncio. Since we are using threads on our backend
    we need to use call_soon_threadsafe to get messages through.
    """

    def __init__(self, application, request, **kwargs):

        self._root_logger = logging.getLogger()
        self._stream_handler = None
        super().__init__(application, request, **kwargs)
        self.loop = asyncio.get_event_loop()  # pylint: disable=W0201

    def open(self, *args, **kwargs):
        """Called when websocket is opened"""

        # Get websocket logger just for getting logging settings
        ws_logger = logging.getLogger('websocket')
        # Get handler which is configured is logging.yaml
        handler = list(
            filter(
                lambda x: x.name is not None and x.name.lower() == 'websocket', ws_logger.handlers
            )
        )[0]

        weblogger = WebsocketStreamHandler(self)
        self._stream_handler = logging.StreamHandler(weblogger)
        self._stream_handler.formatter = handler.formatter
        self._stream_handler.level = handler.level

        self._root_logger.addHandler(self._stream_handler)

        self._root_logger.info('Websocket logger connected')

    def on_close(self):
        """Called when websocket is closed"""
        self._root_logger.removeHandler(self._stream_handler)

    def on_message(self, message):
        """Called when message comes from client through websocket"""
        # self.write_message("echo: %r" % message)

    def check_origin(self, origin):  # pylint: disable=R0201, W0613
        """Checks whether websocket connection from origin is allowed.

        We will allow all connection which is actually potential safety risk. See:
        https://www.tornadoweb.org/en/stable/websocket.html#tornado.websocket.WebSocketHandler.check_origin
        """
        return True

    def data_received(self, chunk):
        pass
