import asyncore
import json
import socket
import time

def loop():
    '''
    Let asyncore do its job.
    '''
    asyncore.loop()

class GestureListener(asyncore.dispatcher_with_send):
    '''
    '''

    listener = None
    '''
    Gesture listener.
    '''

    service = None
    '''
    '''

    last_heartbeat = None
    '''
    Last heart beat.
    '''

    def __init__(self, handler, service = None, host = None, port = 8981):
        '''

        '''
        asyncore.dispatcher_with_send.__init__(self)        
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        if service != None:
            self.service = (service['host'], service['port'])
        else:
            self.service = (host, port)
        self.connect(self.service)
        self.listener = handler
        self.send_heartbeat(time.clock())

    def send_heartbeat(self, tmr):
        '''
        Send heart beat message to service.
        '''
        self.sendto('register', self.service)
        self.last_heartbeat = tmr

    def handle_read(self):
        '''

        '''
        data = self.recv(2048)
        try:
            j = json.loads(data)
            if j.has_key(u'type'):
                if j[u'type'] == u'pointer':
                    self.listener(j)
        except:
            import sys
            print sys.exc_info()

        t = time.time()
        if t > self.last_heartbeat + 5:
            self.send_heartbeat(t)

    def unregister(self):
        '''
        '''
        self.sendto('unregister', self.service)

class DiscoveryListener(asyncore.dispatcher):
    '''

    '''

    services = None
    '''
    Services dictionary.
    '''

    listener = None
    '''
    Listener callback.
    '''

    def __init__(self, handler, host = '', port = 8980):
        '''

        '''
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.services = {}
        self.listener = handler

    def handle_read(self):
        '''

        '''
        data, addr = self.recvfrom(1024)

        try:
            j = json.loads(data)
            if j[u'type'] == u'discovery':
                h = j[u'hostname']
                # we only support UDP connects in our client library
                # find UDP port
                s = j[u'services']
                p = None
                for i in range(len(s)):
                    u = s[i]
                    if u.startswith(u'udp:'):
                        p = int(u[4:])
                        break

                # timestamp
                ts = time.clock()
                # update service
                if p != None:
                    ip = addr[0]
                    self.services[ip] = { 'hostname': h,
                                              'port': p,
                                              'host': ip,
                                              'time': ts }
                # remove all old services
                del_l = [] # deletion list
                for kb, vb in self.services.iteritems():
                    t = vb['time']
                    if (t + 10) < ts:
                        del_l.append(kb)
                for i in range(len(del_l)):
                    del self.services[del_l[i]]

                # tell about the current list
                self.listener(self.services.values())
        except:
            import sys
            print sys.exc_info()


