#!/usr/bin/env python
'''
This script looks for running AirPointr Services on localhost and the
local network. It connects to a local or remote kodi instance and provides
the basic control functions (volume control, play, pause, next track,
previous track) via gesture input from the connected AirPointr Service

@package kodi_airpointr_client
'''

import sys
import time
import socket
import threading
import json

import pyjsonrpc

# Interface IP for the communiation with the AirPointr Service
# set to "0.0.0.0" on UNIX and to "<ip_of_ethernet_interface>" on Windows
LOCAL_INTERFACE_IP = "localhost"

# Host name where kodi is running, default is localhost if on same machine as Kodi
# Make sure "Allow control of Kodi via HTTP" is set to ON in Settings -> 
# Services -> Webserver
KODI_HOST = "localhost"
 
#Configured in Settings -> Services -> Webserver -> Port
KODI_PORT = 8080

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
some globals for the kodi control
"""
volume_change_active = False

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
    and starts the evaluation of the pointer data
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
    if volume control is active, playback mode is not changed
    """
    global volume_change_active
    global last_segment
    if json_data["circle"]["active"]:
        if json_data["circle"]["direction"] != 0:
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
        else:
            volume_change_active = False
    else:
        volume_change_active = False
        
    if json_data["events"] and volume_change_active == False:
        if json_data["events"] == [u'rwipe']:
            print "\nevent occured: right swipe"
            change_playback_mode("forward")
        elif json_data["events"] == [u'lwipe']:
            print "\nevent occured: left swipe"
            change_playback_mode("backward")
                   
def set_volume_change(change):
    """
    Current volume ist requested and set to the changed value
    """
    global http_client
    
    response = http_client.call("Application.GetProperties",["volume"])
    volume = response["volume"]
    new_volume = min(100, max(0, volume+change))
    http_client.call("Application.SetVolume",new_volume)
    print "Kodi Status: Volume changed to: " +str(new_volume) + "%"
        
def change_playback_mode(direction):
    """
    depending on the current kodi playback state the client gives a specific
    control command to kodi in response to the swipe event
    """
    global http_client
    
    response = http_client.call("Player.GetActivePlayers")
    if len(response) >= 1:
        playerid = response[0]["playerid"] # the first player is controlled
        response = http_client.call("Player.GetProperties",
                                    playerid,
                                    ["speed", "percentage", "time"] )
        
        if response["speed"] != 0:
            playback_state = "play"
        else:
            playback_state = "pause"    
            
        if playback_state == "play":
            if direction == "forward":
                response = http_client.call("Player.GoTo",
                                            playerid,
                                            "next")
                print "Playback state:  play --> next track"
            if direction == "backward":
                response = http_client.call("Player.PlayPause",
                                            playerid=playerid,
                                            play=False)
                print "Playback state:  play --> pause"
        if playback_state == "pause":
            if direction == "forward":
                response = http_client.call("Player.PlayPause",
                                            playerid=playerid,
                                            play=True)
                print "Playback state:  pause --> play"
            if direction == "backward":
                response = http_client.call("Player.GoTo", 
                                            playerid, 
                                            "previous")
                response = http_client.call("Player.GoTo",
                                            playerid, 
                                            "previous")
                print "Playback state:  pause --> previous track"
            
    else:
        print "Kodi Status: No Player active, playback control is not active!"
   


def main():
    global LOCAL_INTERFACE_IP
    
    global KODI_HOST
    global KODI_PORT
    
    global AIRPOINTR_HOST_IP
    global AIRPOINTR_HOSTNAME
    global AIRPOINTR_DISCOVERY_PORT
    global AIRPOINTR_GESTURE_PORT
    
    global sock
    global http_client
    
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    
    
    sock.bind((LOCAL_INTERFACE_IP, AIRPOINTR_DISCOVERY_PORT))
    
    if AIRPOINTR_HOST_IP == None:
        AIRPOINTR_HOST_IP = socket.gethostbyname_ex(AIRPOINTR_HOSTNAME)[2][0]
    
    #discovery messages are not sent over the loopback interface, so if the
    #service should run over this interface it has to be triggered directly
    if AIRPOINTR_HOST_IP == "127.0.0.1" or AIRPOINTR_HOST_IP == "127.0.1.1":
        register_to_gesture_server("127.0.0.1", AIRPOINTR_GESTURE_PORT)
        airpointr_services_list.append(dict(address=("127.0.0.1", 
                                                     AIRPOINTR_GESTURE_PORT),
                                            active=False, 
                                            license_status="demo",
                                            last_packet=0))
    
    do_every(15, keep_alive_airpointr_service)
    
    
    #Base URL of the json RPC calls.
    kodi_json_rpc_url = ("http://" + KODI_HOST +
                         ":" + str(KODI_PORT) + "/jsonrpc")
    
    http_client = pyjsonrpc.HttpClient(kodi_json_rpc_url)
    
    try:
        response = http_client.call("Player.GetActivePlayers")
    except Exception as e:
        print e
        print "Kodi is not responding."
        print "Please start Kodi before you run the client script!"
        sys.exit(0)    
    
    if len(response) < 1:
        print "Kodi Status: No Player active, playback control is not active!"
    
    
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
            