"""HTTP listener to enable REST API and serving web UI"""

import time
import shutil
import logging
import json
import os
import asyncio
import tornado.web
import tornado.websocket
from listener.logs_web_socket import LogsWebSocketHandler

RESP_CONTENT_TYPE = 'application/vnd.siren+json; charset=UTF-8'


# disable pylint warning for not overriding 'data_received' from RequestHandler
# pylint: disable=W0223
class IrisRequestHandler(tornado.web.RequestHandler):
    """Base class for REST API calls"""

    def initialize(self, test_control, test_definitions, listener_args, **kwargs):
        """Initialize is called when tornado.web.Application is created"""
        self.logger = logging.getLogger(self.__class__.__name__)  # pylint: disable=W0201
        # Disable tornado access logging by default
        logging.getLogger('tornado.access').disabled = True
        self.test_control = test_control  # pylint: disable=W0201
        self.test_definitions = test_definitions  # pylint: disable=W0201
        self.listener_args = listener_args  # pylint: disable=W0201
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, Content-Type")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def json_args(self):
        """Get json args (fields) from request body"""
        return tornado.escape.json_decode(self.request.body)

    def text_plain(self):
        """Get plain text converted from byte string to str"""
        return tornado.escape.native_str(self.request.body)

    def siren_response(self, resp):
        """Respond with siren, i.e write response and set content type"""
        if resp is not None:
            self.write(resp)
        self.set_content_type()

    def set_content_type(self):
        """Set content type"""
        self.set_header('Content-Type', RESP_CONTENT_TYPE)

    def get(self, *args):
        """Handles get requests

        First handles authentication etc, calls handle_get()
        on child class and then writes response.
        """
        # Tornado stores current user automatically to self.current_user
        user = None  # Authentication not implemented
        host = self.request.headers.get('host')
        self.siren_response(self.handle_get(host, user, *args))

    def post(self, *args):
        """Handles post requests

        First handles authentication etc, calls handle_post()
        on child class and then writes response.
        """
        self.logger.debug("Handling post")
        # Tornado stores current user automatically to self.current_user
        user = self.current_user
        host = self.request.headers.get('host')

        data = None
        content_type = self.request.headers['Content-Type']

        if 'json' in content_type:
            data = self.json_args()
        elif 'text/plain' in content_type:
            data = self.text_plain()

        self.siren_response(self.handle_post(data, host, user, *args))

    def options(self):
        """Handle preflight request"""

        self.set_status(204)
        self.finish()


class NoCacheStaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        # Disable cache
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')


class ApiRootHandler(IrisRequestHandler):
    """Handles calls to "/api"""

    def handle_get(self, host, user, *args):  # pylint: disable=W0613
        """Handle /api get"""

    def handle_post(self, json_args, host, user, *args):  # pylint: disable=W0613
        """Handle /api post"""


class TestRunnerHandler(IrisRequestHandler):
    """Handles starting of tests, returns status of tests etc."""

    def handle_get(self, host, user, *args):
        """Returns running test handlers"""
        print("GET test_control")
        return "Stay tuned"

    def handle_post(self, json_args, host, user, *args):  # pylint: disable=W0613
        """Handles post to /api/test_control"""

        for key, value in json_args.items():

            if key == 'run':
                if json_args['run']:
                    self.test_control['run'].set()
                else:
                    self.test_control['run'].clear()
            else:
                if key in self.test_control:
                    self.test_control[key] = value


class HistorySearchItems(IrisRequestHandler):
    """Handles starting of tests, returns status of tests etc."""

    def handle_get(self, host, user, *args):
        """Returns running test handlers"""
        return self.listener_args['database'].get_search_bar_items()


class IrisEncoder(json.JSONEncoder):
    '''Encode json properly'''

    def default(self, obj):

        try:
            return json.JSONEncoder.default(self, obj)
        except Exception as e:
            return str(obj)


class SearchHistoryHandler(IrisRequestHandler):
    """Handles starting of tests, returns status of tests etc."""

    def handle_post(self, json_args, host, user, *args):  # pylint: disable=W0613
        """Handles post to /api/test_control"""

        return json.dumps(self.listener_args['database'].search_db(json_args), cls=IrisEncoder)


class DutsHandler(IrisRequestHandler):
    """Handles starting of tests, returns status of tests etc."""

    def handle_get(self, host, user, *args):
        """Returns running test handlers"""

        return {'duts': self.test_definitions.DUTS}


class ProgressHandler(IrisRequestHandler):
    """Handles calls to /api/progress"""

    def handle_get(self, host, user, *args):
        """Returns current progress as json"""

        return {'progress': self.test_control['progress']}


class UiEntryHandler(tornado.web.StaticFileHandler):
    """Handles returning the UI from all paths except /api"""

    def validate_absolute_path(self, root, absolute_path):  # pylint: disable=R1710
        """Validate and return the absolute path.

        Override validate_absolute_path of Tornado to return UI from all
        paths. This is mostly copy-paste from:
        https://www.tornadoweb.org/en/stable/_modules/tornado/web.html#StaticFileHandler.validate_absolute_path
        """
        root = os.path.abspath(root)
        if not root.endswith(os.path.sep):
            # abspath always removes a trailing slash, except when
            # root is '/'. This is an unusual case, but several projects
            # have independently discovered this technique to disable
            # Tornado's path validation and (hopefully) do their own,
            # so we need to support it.
            root += os.path.sep
        # The trailing slash also needs to be temporarily added back
        # the requested path so a request to root/ will match.
        if not (absolute_path + os.path.sep).startswith(root):
            raise tornado.web.HTTPError(403, "%s is not in root static directory", self.path)
        if os.path.isdir(absolute_path) and self.default_filename is not None:
            # need to look at the request.path here for when path is empty
            # but there is some prefix to the path that was already
            # trimmed by the routing
            if not self.request.path.endswith("/"):
                self.redirect(self.request.path + "/", permanent=True)
                return
            absolute_path = os.path.join(absolute_path, self.default_filename)
        if not os.path.exists(absolute_path) or not os.path.isfile(absolute_path):
            # This is changed by JOT: Return UI if file/path is not found
            return os.path.join(root, self.default_filename)
        return absolute_path


class MessageWebsocketHandler(tornado.websocket.WebSocketHandler):
    """
    Note that Tornado uses asyncio. Since we are using threads on our backend
    we need to use call_soon_threadsafe to get messages through.
    """

    def initialize(self, message_handlers=None, return_message_handler=None, **kwargs):
        """Initialize is called when tornado.web.Application is created"""

        if message_handlers is not None:
            message_handlers.append(self.websocket_signal_handler)  # pylint: disable=W0201

        self.loop = asyncio.get_event_loop()  # pylint: disable=W0201
        self.return_message_handler = return_message_handler  # pylint: disable=W0201
        self.logger = logging.getLogger("MessageWebsocketHandler")

    def websocket_signal_handler(self, message):  # pylint: disable=W0613
        """Sends application state changes through websocket"""

        def send_a_message(self, msg):
            try:
                self.write_message(msg)
            except tornado.websocket.WebSocketClosedError:
                pass
            except Exception as e:
                self.logger.exception("Failed to write to the websocket")
                raise e

        self.loop.call_soon_threadsafe(send_a_message, self, message)

    def open(self, *args: str, **kwargs: str):
        """Called when websocket is opened"""

        pass

    def on_close(self):
        """Called when websocket is closed"""

        pass

    def on_message(self, message):
        """Called when message comes from client through websocket"""
        self.return_message_handler.put(message)

    def check_origin(self, origin):  # pylint: disable=R0201, W0613
        """Checks whether websocket connection from origin is allowed.

        We will allow all connection which is actually potential safety risk. See:
        https://www.tornadoweb.org/en/stable/websocket.html#tornado.websocket.WebSocketHandler.check_origin
        """
        return True


class LogsHandler(IrisRequestHandler):
    _filename = ''

    def get(self, *args):
        self._filename = 'logs_' + time.strftime("%Y%m%d-%H%M%S")
        self.set_header('Content-Type', 'application/force-download')
        self.set_header('Content-Disposition', 'attachment; filename=%s' % self._filename + '.zip')
        shutil.make_archive(self._filename, 'zip', 'logs/')
        with open(os.path.join(self._filename + '.zip'), "rb") as _f:
            try:
                while True:
                    _buffer = _f.read(4096)
                    if _buffer:
                        self.write(_buffer)
                    else:
                        _f.close()
                        self.finish()
                        return
            except:
                raise tornado.web.HTTPError(404, "Log files not found")

    def on_finish(self):
        if os.path.exists(self._filename + '.zip'):
            os.remove(self._filename + '.zip')


class MediaFileHandler(tornado.web.StaticFileHandler):
    def initialize(self, listener_args, path, **kwargs):
        """Initialize is called when tornado.web.Application is created"""
        self.logger = logging.getLogger(self.__class__.__name__)  # pylint: disable=W0201
        # Disable tornado access logging by default
        logging.getLogger('tornado.access').disabled = True
        self.listener_args = listener_args  # pylint: disable=W0201
        super().initialize(path=path)

    def parse_url_path(self, url_path):
        return self.listener_args['database'].get_media_file_path(url_path)


def create_listener(
    port,
    test_control,
    message_handlers,
    progress_handlers,
    test_definitions,
    return_message_handler,
    listener_args,
):
    """Setup and create listener"""
    import ui
    from pathlib import Path

    ui_path = Path(ui.__path__[0], 'build')

    init = {
        'test_control': test_control,
        'test_definitions': test_definitions,
        'listener_args': listener_args,
    }

    app = tornado.web.Application(
        [
            (
                r'/api/websocket/messagequeue',
                MessageWebsocketHandler,
                {'message_handlers': message_handlers},
            ),
            (
                r'/api/websocket/progress',
                MessageWebsocketHandler,
                {'message_handlers': progress_handlers},
            ),
            (
                r'/api/websocket/dut_sn',
                MessageWebsocketHandler,
                {'return_message_handler': return_message_handler},
            ),
            (r"/api", ApiRootHandler, init),
            (r"/api/duts", DutsHandler, init),
            (r"/api/history/search_bar_items", HistorySearchItems, init),
            (r"/api/history/search", SearchHistoryHandler, init),
            (r"/api/progress", ProgressHandler, init),
            (
                r"/api/latest_result/(.*)",
                NoCacheStaticFileHandler,
                {'path': 'results/', "default_filename": "latest_result.html"},
            ),
            (r"/api/websocket/log", LogsWebSocketHandler),
            (r"/api/testcontrol", TestRunnerHandler, init),
            (r"/api/testcontrol/([0-9]+)", TestRunnerHandler, init),
            (r"/logs", LogsHandler, init),
            (
                r"/api/media/(.*)",
                MediaFileHandler,
                {'listener_args': listener_args, 'path': os.getcwd()},
            ),
            (r"/(.*\.(js|json|html|css))", tornado.web.StaticFileHandler, {'path': ui_path}),
            (r"/(.*)", UiEntryHandler, {'path': ui_path, "default_filename": "index.html"}),
        ]
    )

    app.listen(port)
