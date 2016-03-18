#!/usr/bin/env python
'''
This is a very basic script, that has to run on the same device as
the AirPointr service. It registers to the AirPointr Service over
the loopback interface and recieves the UDP messages with the pointer
data. A certain selection of the AirPointr variables and events are written
to the console.

@package display_airpointr_input
'''

import socket
import threading
import json



# IP Address of the machine that should provide the AirPointr service
AIRPOINTR_HOST_IP = "raspberrypi3"
AIRPOINTR_GESTURE_PORT = 8981


sock = None
http_client = None

  
def do_every(interval, worker_func, iterations = 0):
    """
    helper function to create periodically executed threads
    """
    if iterations != 1:
        threading.Timer(
                        interval,
                        do_every, [interval, worker_func, 0 if iterations == 0 else iterations-1]
                        ).start()
    worker_func()
                    
def register_to_airpointr_service():
    """
    Sends the registration request to the specefied address
    """
    try:
        sock.sendto("register",(AIRPOINTR_HOST_IP,AIRPOINTR_GESTURE_PORT))
    except socket.error as e:
        print e
        print (AIRPOINTR_HOST_IP,AIRPOINTR_GESTURE_PORT)    

def handle_pointer_message(addr, json_data):
    """
    checks if the received pointer message should be handled as control input
    and starts the evalution of the pointer data
    """
    ip = addr[0]
    port = addr[1]
    license_status = json_data["license"]
    valid_input = False
    if (license_status == "demo" or 
        license_status == "licensed"):
            valid_input = True
    else:
            print ("AirPointr Status " + 
                   ip + ":" +
                   str(port) + " :" )
            print "Demo expired -> Pointer output is invalid!"


    if ip == AIRPOINTR_HOST_IP and valid_input:
        handle_pointer_input(json_data)
        
   

def handle_pointer_input(json_data):
    """
    displays the pointer input data
    """
            
    output_string = ("Pointer: x=" + "{:1.6f}".format(json_data["x"]) + 
                     " / y=" + "{:1.6f}".format(json_data["y"]))
                     
    if not json_data["active"]:
        output_string += " (inactive)"
        
    print "\033[A\033[G", output_string, "\033[K"
        
    if json_data["events"]:
        if json_data["events"] == [u'rwipe']:
            print "Wipe Right detected.\n"
    
        if json_data["events"] == [u'lwipe']:
            print "Wipe Left detected.\n"
            
    if json_data["circle"]["active"]:
        output_string = "Circle active: Segment=" + str(json_data["circle"]["segment"])
        print "\033[A\033[G", output_string, "\033[K"

    if json_data["circle"]["smart"]["enabled"]:
        if json_data["circle"]["smart"]["actionSelect"]:
            if json_data["circle"]["smart"]["actionSegment"] == 0:
                segment_string = "-north-"
            elif json_data["circle"]["smart"]["actionSegment"] == 1:
                segment_string = "-east-"
            elif json_data["circle"]["smart"]["actionSegment"] == 2:
                segment_string = "-south-"
            elif json_data["circle"]["smart"]["actionSegment"] == 3:
                segment_string = "-west-"
                
            print "Smart circle action: Selected Segment", segment_string, ".\n"

   

def main():    
    global AIRPOINTR_HOST_IP
    global AIRPOINTR_GESTURE_PORT
    
    global sock
    
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    
    sock.bind(('', 0))

    # AirPointr service has to be kept alive
    do_every(15, register_to_airpointr_service)
    
    while 1:
        data, addr = sock.recvfrom(1024)
        if data[0] == "{":
            json_data = json.loads(data)
            if "type" in json_data:        
                if json_data["type"] == "pointer" in data:
                    handle_pointer_message(addr, json_data)
 
        else:
            print "\nnot a JSON-Blob"
 
            
if __name__ == "__main__":
    main()