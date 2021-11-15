""" Allows controlling runner test_control """

def set_events(test_control, instruments):
    """Called in the beginning of actual test loop."""
    event = Events(test_control)
    # instruments['G5'].set_app_callback("StopButton_IN", "True", event.state_changed)

class Events():
    """Class for handling test_control and callbacks"""
    def __init__(self, test_control):
        self.test_control = test_control

    def state_changed(self, message):
        """Callback method"""
        pass
        # if message['name'] == 'StopButton_IN':
        #    self.test_control['abort'] = True
