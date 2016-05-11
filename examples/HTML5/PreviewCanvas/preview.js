/*	
  preview.js
  WebSocket Gesture Preview

  Gesture Preview with websocket connection
  With the function initSocket(ws_host, ws_port, ws_path) the connection is established
  and the AirPointr input is processed by the onPointer(msg) function
  The script uses the canvas with ID='gesture_preview' to draw the recognized gestures.

  This code is licensed under the MIT license

  Copyright (C) 2015-2016 MYESTRO Interactive

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"),
  to deal in the Software without restriction, including without limitation
  the rights to use, copy, modify, merge, publish, distribute, sublicense,
  and/or sell copies of the Software, and to permit persons to whom the Software
  is furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
  INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
  ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
  OR OTHER DEALINGS IN THE SOFTWARE.


*/

/* pointer images */
var pointrActiveImage  =new Image();
var pointrInactiveImage=new Image();

/* websocket */
var mySocket = null;
var ws_uri;

/* persistent handle for the canvas */
var canvas;

/* helper function to check if input is valid object */
function isObj(v) {
    if ((typeof v !== null) &&  (typeof v === 'object'))
    {
        return true;
    }
    return false;
}

/* persistent vars for visualization */
var symbol  = 0;
var fadeOut = 0;
var expiredWarningShown   = 0;
var sc_select_ani_timeout = 0;
var sc_left_ani_timeout   = 0;
var sc_sel= 0;

function showLicExpWarning() {
    var wrn = document.getElementById('expiredwarning');
    if (isObj(wrn)) {
        wrn.style.display="block";
    } else  {
        console.error("Your installation of AirPointr is not licensed and demo has expired!");
    }
}


/* This function parses the data of the received message. All pointer input information is stored in the struct "pointrData" and is used for a visualization later on */
function onPointr(msg) {
    /* msg should be a json blob */
    var pointrData = JSON.parse(msg.data);
    if (isObj(pointrData)&&(pointrData.hasOwnProperty("type"))&&(pointrData.type==="pointer")) {

        canvas = document.getElementById('gesture_preview');
        /* for the display of the received pointer information we make use of the canvas "gesture_preview" */
        if(canvas.getContext)
        {

            var context = canvas.getContext('2d');
            context.clearRect(0, 0, canvas.width, canvas.height);
            /* use the license field in the pointrdata-struct to check if your pointr-input is valid */
            if (pointrData.license==="invalid") {
                showLicExpWarning();
            }


            var width = canvas.width;
            var height = canvas.height;


            /* input of circle gesture */
            var circleActive = pointrData.circle.active;
            var phi       = pointrData.circle.phi;
            var segment   = pointrData.circle.segment;
            var direction = pointrData.circle.direction;
            var turns     = pointrData.circle.turns;


            /* input of the wipe gesture */
            var wipeLeft  = (pointrData.events.indexOf('lwipe')!==-1)?true:false;
            var wipeRight = (pointrData.events.indexOf('rwipe')!==-1)?true:false;

            /* input of smart circle gesture (experimental/ not available yet) */
            var smartCircleEnabled = pointrData.circle.smart.enabled;
            var smartSegment       = pointrData.circle.smart.segment;
            var smartCircleActionSegment = pointrData.circle.smart.actionSegment;
            var smartCircleActionSelect  = pointrData.circle.smart.actionSelect;
            var smartCircleActionLeft    = pointrData.circle.smart.actionLeft;

            /* input of the pointer coordinates */
            var px = pointrData.x * width;
            var py = pointrData.y * height;
            var pointerActive = pointrData.active;


            /* visualization of the circle gesture */
            var radius = ((width<height)?width:height) / 4;

            /* visualization of the smart circle gesture */
            var radiusSC = radius * 1.28;

            /* circle */
            if (circleActive) {
                context.beginPath();
                context.strokeStyle = '#00d000';
                context.lineWidth = 4;
                context.arc(width/2,height/2,radius,0,2*Math.PI);
                context.stroke();
            }

            var nSegments, segmentLength, phi0, phi1;

            /* further circle graphics */
            if (circleActive) {

                /* draw the segment */
                segment   = -segment - 0.5;
                nSegments = 8;
                segmentLength = 2*Math.PI / nSegments;
                phi0 = segmentLength * (segment-2);
                phi1 = segmentLength * (segment-1);
                context.beginPath();
                context.lineWidth = 16;
                context.strokeStyle = '#00d000';
                context.lineCap = "round";
                context.arc(width/2,height/2,radius,phi0,phi1);
                context.stroke();

                /* draw the phi projection on circle */
                var x = width/2  - Math.cos(phi + 0.5 * Math.PI) * radius;
                var y = height/2 - Math.sin(phi + 0.5 * Math.PI) * radius;
                context.beginPath();
                context.lineWidth = 2;
                context.strokeStyle = 'black';
                context.fillStyle = '#00ff00';
                context.arc(x,y,16,0,2*Math.PI);
                context.fill();
                context.stroke();

                /* draw smart circle segments */
                if (smartCircleEnabled) {
                    nSegments = 4;
                    segmentLength = 2*Math.PI / nSegments;
                    var lineWidth = 16;
                    var strokeStyle = '#0000f0';
                    var globalAlpha = 1;

                    context.lineCap = "butt";

                    for ( i = 0; i < nSegments; i++) {
                        phi0 = segmentLength * (i - 0.47) - 0.5*Math.PI;
                        phi1 = segmentLength * (i + 0.47) - 0.5*Math.PI;
                        if (i === smartSegment) {
                            lineWidth = 40;
                            strokeStyle = '#0000f0';
                            globalAlpha = 1;
                        } else {
                            lineWidth = 26;
                            strokeStyle = '#0080f0';
                            globalAlpha = 0.5;
                        }
                        context.beginPath();
                        context.globalAlpha = globalAlpha;
                        context.lineWidth = lineWidth;
                        context.strokeStyle = strokeStyle;
                        context.arc(width/2,height/2,radiusSC,phi0,phi1);
                        context.stroke();
                    }
                    context.globalAlpha = 1;
                }
            }

            /* trigger smart circle segment selection */
            if (smartCircleEnabled && smartCircleActionSelect) {
                sc_select_ani_timeout = 30;
                sc_sel = smartSegment;
                console.log("Smart Circle select: "+sc_sel);
            }

            /* trigger smart circle left selection */
            if (smartCircleEnabled && smartCircleActionLeft) {
                sc_left_ani_timeout = 30;
                sc_sel = smartSegment;
                console.log("Smart Circle left: "+sc_sel);
            }

            /* smart circle animation */
            if (sc_select_ani_timeout>0) {
                sc_select_ani_timeout--;
                segment = sc_sel - 1;
                nSegments = 4;
                segmentLength = 2 * Math.PI / nSegments;
                phi0 = segmentLength * segment - 0.25 * Math.PI;
                phi1 = segmentLength * segment + 0.25 * Math.PI;
                context.beginPath();
                context.save();
                context.globalAlpha=sc_select_ani_timeout/30;

                context.lineWidth = 32+60-2*sc_select_ani_timeout;
                context.strokeStyle = '#red';
                context.lineCap = "butt";
                context.arc(width/2,height/2,radiusSC-(30-sc_select_ani_timeout),phi0-(30-sc_select_ani_timeout)/200,phi1+(30-sc_select_ani_timeout)/200);
                context.stroke();
                context.restore();
            }

            /* smart circle left animation */
            if (sc_left_ani_timeout>0) {
                sc_left_ani_timeout--;
                segment = sc_sel - 1;
                nSegments = 4;
                segmentLength = 2 * Math.PI / nSegments;
                phi0 = segmentLength * segment - 0.25 * Math.PI;
                phi1 = segmentLength * segment + 0.25 * Math.PI;
                context.beginPath();
                context.save();
                context.globalAlpha=sc_left_ani_timeout/30;

                context.lineWidth = 32+60-2*sc_left_ani_timeout;
                context.strokeStyle = '#0000f0';
                context.lineCap = "butt";
                context.arc(width/2,height/2,radiusSC+(30-sc_left_ani_timeout),phi0-(30-sc_left_ani_timeout)/240,phi1+(30-sc_left_ani_timeout)/240);
                context.stroke();
                context.restore();
            }

            if (wipeLeft) {
                console.log("WIPE L");
                symbol = 1;
                fadeOut = 30;
            }
            if (wipeRight) {
                console.log("WIPE R");
                symbol = 2;
                fadeOut = 30;
            }

            /* wipe animation */
            if (symbol) {
                var x0, y0;
                x0=width/2;
                y0=height/2;
                context.save();
                context.globalAlpha=fadeOut/30;
                context.beginPath();
                context.lineWidth = 8;
                context.strokeStyle = '#4040ff';
                context.fillStyle = '#0000e0';
                context.lineCap = "round";
                switch(symbol) {
                case 1: //left wipe
                    context.moveTo(x0-128, y0-96);
                    context.lineTo(x0+128, y0);
                    context.lineTo(x0-128, y0+96);
                    context.lineTo(x0-128, y0-96);
                    break;
                case 2:
                    context.moveTo(x0+128, y0-96);
                    context.lineTo(x0-128, y0);
                    context.lineTo(x0+128, y0+96);
                    context.lineTo(x0+128, y0-96);
                    break;
                }
                context.fill();
                context.stroke();
                context.restore();
            }
            if (fadeOut>0) {
                fadeOut--;
            } else {
                symbol=0;
                fadeOut=0;
            }

            /* visualization of the pointer */
            context.fillStyle = 'red';
            context.strokeStyle = 'red';
            context.lineWidth = 2;
            /* hotspot calculation */
            var hsX = 0.5;
            var hsY = 0.33;
            var xOffs = pointrActiveImage.width * hsX;
            var yOffs = pointrActiveImage.height * hsY;
            if (pointrActiveImage.complete && pointrInactiveImage.complete) {
                if (pointerActive) {
                    context.drawImage(pointrActiveImage,px - xOffs, py - yOffs);
                } else {
                    context.drawImage(pointrInactiveImage, px - xOffs, py - yOffs);
                }
            } else {
                if (pointerActive) {
                    context.fillRect(px - 16, py-16, 32, 32);
                } else {
                    context.strokeRect(px - 16, py-16, 32, 32);
                }
            }
        } else {

        }
    }
}

function initSocket(ws_host, ws_port, ws_path) {
    /* building the websocket uri */
    var ws_prefix = (window.location.protocol === 'https')?'wss':'ws';
    ws_uri = ws_prefix + "://" + ws_host + ":" + ws_port + "/" + ws_path;
    tryConnectWS();
}

function tryConnectWS() {
    console.log("Starting websocket comm...");
    if (mySocket!==null) {
        mySocket.onclose = function(){};
        mySocket.close();
        delete mySocket;
    }

    mySocket = new WebSocket(ws_uri);
    
    /* defintion of the websocket event handlers */
    mySocket.onopen = function() {
        console.log("Socket opened");
    }

    mySocket.onclose = function(event) {
        var canvas = document.getElementById('gesture_preview');
        if(canvas.getContext)
        {
            var context = canvas.getContext('2d');
            context.clearRect(0, 0, canvas.width, canvas.height);
        }
        setTimeout(tryConnectWS, 1000);
    };

    mySocket.onerror = function(error) {
        console.log("WebSocket error" + error);
        mySocket.close();
    };
    
    /* linking the message parsing function with the socket event "onmessage" */
    mySocket.onmessage = function(msg) {
        mySocket.send('ACK_BYTES_NOW_PLZ');
        onPointr(msg);
    };
}


function preview_init() {
    canvas = document.getElementById('gesture_preview');
    pointrActiveImage.src   = "./pointer_active.png";
    pointrInactiveImage.src = "./pointer_inactive.png";
}

preview_init();
