#!/usr/bin/env python
'''
This script looks for running AirPointr Services on localhost and the
local network. It connects to a local or remote mpd-server and provides
the basic control functions (volume control, play, pause, next track,
previous track) via gesture input from the connected AirPointr Service

@package mpd_airpointr_client
'''

import socket
import time
import threading
import json

import mpd

# Interface IP for the communiation with the AirPointr Service
# set to "0.0.0.0" on UNIX and to "<ip_of_ethernet_interface>" on Windows
LOCAL_INTERFACE_IP = "127.0.0.1"

MPD_HOST = "localhost"
MPD_PORT = "6600"
MPD_PASSWORD = None

# IP Address of the machine that should provide the AirPointr service
# set to <"127.0.0.1"> if AirPointr runs on same machine
# set to <None> if machine is addressed by AIRPOINTR_HOSTNAME
AIRPOINTR_HOST_IP = "127.0.0.1"

# Hostname of the machine that runs the AirPointr service
# only needed if AIRPOINTR_HOST_IP = None, otherwise set to <None> 
AIRPOINTR_HOSTNAME = None
AIRPOINTR_DISCOVERY_PORT = 8980
AIRPOINTR_GESTURE_PORT = 8981


"""
some globals for the mpd control
"""
mpd_client = None
mpd_state = "stop"
volume_change_active = False
last_segment = 0

airpointr_services_list = []
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
                    
def register_to_gesture_server(ip, port):
    """
    Sends the registration request to the specefied address
    """
    try:
        sock.sendto("register",(ip,port))
    except socket.error as e:
        print e
        print (ip,port)    

def keep_alive_airpointr_service():
    """
    Lists the discovered AirPointr Server and sends a keep alive message to
    the one that should provide the control input
    """
    inactive_server = []
    print "\nDiscovered Airpointr Server:"
    for idx, server in enumerate(airpointr_services_list):
        if server["last_packet"]+10 > time.clock():
            if server["active"]:
                register_to_gesture_server(*server["address"])
                print "Address: " + (str(server["address"])
                       + " | License Status: " + str(server["license_status"])
                       + " | (active)")
            else:
                print str(server["address"])
        else:
            ip = server["address"][0]
            if ip != "127.0.0.1" and ip != "127.0.1.1":
                inactive_server.append(idx)
            
    for idx in sorted(inactive_server, reverse=True):
        del airpointr_services_list[idx]

def handle_discovery_message(addr, json_data):
    """
    adds any new server address to airpointr_services_list and sends
    registration message if the server should provide the control input
    """
    reception_time = time.clock()
    ip = addr[0]
    
    not_in_list = True
    for server in airpointr_services_list:
        if server["address"] == addr:
            server["last_packet"] = reception_time
            not_in_list = False
    
    if not_in_list:
        airpointr_services_list.append(dict(address=addr, 
                                            active=False, 
                                            license_status="demo",
                                            last_packet=reception_time))
        if ip == AIRPOINTR_HOST_IP:
            register_to_gesture_server(*addr)
        
        print "\nreceived discovery message:"
        for ka, va in json_data.iteritems():
            if isinstance(va,dict):
                print ka+": "
                for kb, vb in va.iteritems():
                    print "  "+kb+": "+str(vb)
            else:
                print ka+": "+str(va)
        print "From Addresse", addr
        print "\n"
        

def handle_pointer_message(addr, json_data):
    """
    checks if the received pointer message should be handled as control input
    and starts the evalution of the pointer data
    """
    reception_time = time.clock()
    ip = addr[0]
    valid_input = False
    for server in airpointr_services_list:
        if ip == server["address"][0]:
            server["active"] = True
            server["license_status"] = json_data["license"]
            if (server["license_status"] == "demo" or 
                server["license_status"] == "licensed"):
                    valid_input = True
            else:
                    print ("AirPointr Status " + 
                           server["address"][0] + ":" +
                           str(server["address"][1]) + " :" )
                    print "Demo expired -> Pointer output is invalid!"
            
        server["last_packet"] = reception_time


    if ip == AIRPOINTR_HOST_IP and valid_input:
        handle_pointer_input(json_data)
        
def handle_op_message(addr, json_data):
    """
    Just displays if an registration operation has been successful
    """
    print "\nOperation-Status from: " + str(addr)
    if json_data["success"]:
        print ".."+str(json_data["op"]) + " --> success"
    else:
        print ".."+str(json_data["op"]) + " --> fail"       

def handle_pointer_input(json_data):
    """
    evaluates the pointer data and changes the volume or the playback mode
    accordingly
    Playback control is controlled with the selected segment of the smart
    circle, each segment triggers one of 4 different actions
    Volume control is activated when after the first circle activation 2
    further circle turns are made
    """
    global volume_change_active
    global last_segment

    if not volume_change_active:    
        if json_data["circle"]["smart"]["enabled"]:
            if json_data["circle"]["smart"]["actionSelect"]:
                action_segment = json_data["circle"]["smart"]["actionSegment"]
                if action_segment == 0:
                    execute_playback_command("play")
                if action_segment == 1:
                    execute_playback_command("next")
                if action_segment == 2:
                    execute_playback_command("stop")
                if action_segment == 3:
                    execute_playback_command("prev")
    
    if json_data["circle"]["active"]:
        if json_data["circle"]["direction"] != 0:
            if abs(json_data["circle"]["turns"]) >= 2:
                if volume_change_active:
                    segment = json_data["circle"]["segment"]
                    if segment != last_segment:
                        seg_diff = segment - last_segment
                        if seg_diff > 4:
                            vol_change = seg_diff - 8
                        elif seg_diff < -4:
                            vol_change = seg_diff + 8
                        else:
                            vol_change = seg_diff
                        set_volume_change(vol_change*2)
                        last_segment = segment
                else:
                    last_segment = json_data["circle"]["segment"]
                    volume_change_active = True
        #else:
            #volume_change_active = False
    else:
        volume_change_active = False
        

def connect_to_mpd():
    """
    Establishes TCP connection to mdp-host using  MPD_HOST, MPD_PORT.
    Continuous attempts to connect every 5 seconds, if connection fails.
    Also using MPD_PASSWORD if specified.
    """
    global mpd_client
    
    connected = False
    while connected == False:
            connected = True
            try:
                mpd_client.connect(MPD_HOST, MPD_PORT)
            except socket.error as e:
                connected = False
                print e
    
            if connected == True and MPD_PASSWORD != None:
                try:
                    mpd_client.password(MPD_PASSWORD)
    
                except mpd.CommandError as e:
                    connected = False
    
            if connected == False:
                    print "Couldn't connect. Retrying"
                    time.sleep(5)
                    
def set_volume_change(change):
    """
    Volume change is transmitted to the connected mpd-host
    """
    mpd_status = mpd_client.status()    
    mpd_volume = float(mpd_status["volume"])
    new_volume = min(100,max(0,mpd_volume+change))
    mpd_client.setvol(int(new_volume))
    print "MPD Status: Volume changed to: " +str(new_volume) + "%"

        
def execute_playback_command(command):
    """
    executing one of the commands stop, prev, play/pause, next
    """
    if command == "play":
        mpd_client.play()
    elif command == "next":
        mpd_client.next()
    elif command == "stop":
        mpd_client.stop()
    elif command == "prev":
        mpd_client.previous()
    else:
        print "Wrong input command string for execute_playback_command()"
        return
        
    print "MPD Status: Playback switched to: "+command
   

def main():
    global LOCAL_INTERFACE_IP
    
    global MPD_HOST
    global MPD_PORT
    global MPD_PASSWORD
    
    global AIRPOINTR_HOST_IP
    global AIRPOINTR_HOSTNAME
    global AIRPOINTR_DISCOVERY_PORT
    global AIRPOINTR_GESTURE_PORT
    
    global sock
    global mpd_client
    
    mpd_client = mpd.MPDClient()
    
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    
    
    sock.bind(('', 0))
    
    if AIRPOINTR_HOST_IP == None:
        AIRPOINTR_HOST_IP = socket.gethostbyname_ex(AIRPOINTR_HOSTNAME)[2][0]
    
    connect_to_mpd()
    print "Connection to mpd established"
    
    #discovery messages are not sent over the loopback interface, so if the
    #service should run over this interface it has to be triggered directly
    if AIRPOINTR_HOST_IP == "127.0.0.1" or AIRPOINTR_HOST_IP == "127.0.1.1":
        register_to_gesture_server("127.0.0.1", AIRPOINTR_GESTURE_PORT)
        airpointr_services_list.append(dict(address=("127.0.0.1", AIRPOINTR_GESTURE_PORT), 
                                            active=False, 
                                            license_status="demo",
                                            last_packet=0))
    
    do_every(15, keep_alive_airpointr_service)
    
    while 1:
        data, addr = sock.recvfrom(1024)
        if data[0] == "{":
            json_data = json.loads(data)
            if "type" in json_data:
                if json_data["type"] == "discovery":
                    handle_discovery_message(addr, json_data)
                        
                elif json_data["type"] == "pointer" in data:
                    handle_pointer_message(addr, json_data)
                                
            if "op" in json_data:
                handle_op_message(addr, json_data)
        else:
            print "\nnot a JSON-Blob"
 
            
if __name__ == "__main__":
    main()