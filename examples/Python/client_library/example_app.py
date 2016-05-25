#!/usr/bin/env python

'''
Very simple example how to use Raspberry AirPointr with your code.
'''

import airpointr

class MyGestureHandler:
    gesture_listener = None

    discovery_listener = None

    def handle_gesture(self, gesture):
        '''
        You may add your event handlers here that will be called on each received
        packet from airpointr.
        The argument to this function contains the parsed json so
        you may simply write 
          print gesture['x'], gesture['y']
        to output the current cursor position
        '''
        print gesture
        pass

    def handle_discovery(self, services):
        if len(services) > 0:
            print "Found AirPointr service - connecting to", services[0]['host']
            self.connect(services[0]['host'], services[0]['port'])
            self.discovery_listener.close();

    def connect(self, host, port):
        self.gesture_listener = airpointr.GestureListener(handler = self.handle_gesture,
                                                          host = host,
                                                          port = port)

    def discover(self):
        self.discovery_listener = airpointr.DiscoveryListener(handler = self.handle_discovery)
        

if __name__ == "__main__":
    g = MyGestureHandler()
    g.discover()
    #g.connect(host = '192.168.57.1', port = 8981)
    airpointr.loop()
