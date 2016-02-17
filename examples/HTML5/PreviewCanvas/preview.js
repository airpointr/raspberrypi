/*	
Gesture Preview with websocket connection 
With the function initSocket(ws_host, ws_port, ws_path) the connection is established
and the AirPointr input is processed by the onPointer(msg) function
The script uses the canvas with ID='gesture_preview' to draw the recognized gestures.
*/

//preload of the pointer images (active and inactive)
var pointrActiveImage=new Image();
pointrActiveImage.src="./pointer_active.png";
var pointrInactiveImage=new Image();
pointrInactiveImage.src="./pointer_inactive.png";

var mySocket;

//helper function to check if input is valid object
function isObj(v) {
    if ((typeof v !== null) &&  (typeof v === 'object'))
    {
	return true;
    }
    return false;
}

var symbol = 0;
var fadeOut=0;
var expiredWarningShown=0;
var sc_ani_timeout=0;
var sc_sel=0;

/* This function parses the data of the received message. All pointer input information is stored in the struct "pointrData" and is used for a visualization later on */
function onPointr(msg) {
    //msg should be a json blob
    var pointrData = JSON.parse(msg.data);
    if (isObj(pointrData)&&(pointrData.hasOwnProperty("type"))&&(pointrData.type=="pointer")) {
	//for the display of the received pointer information we make use of the canvas "gesture_preview"
	var canvas = document.getElementById('gesture_preview');
	if(canvas.getContext)
	{
	    var context = canvas.getContext('2d');
	    context.clearRect(0, 0, canvas.width, canvas.height);

	    //use the license field in the pointrdata-struct to check if your pointr-input is valid
	    if (pointrData.license=="invalid") {
		var wrn = document.getElementById('expiredwarning');
		if (isObj(wrn)) {
		    wrn.style.display="block";
		}
	    }

	    
	    
	    //input of circle gesture
	    var podActive = pointrData.circle.active;
	    var phi       = pointrData.circle.phi;
	    var segment   = pointrData.circle.segment;
	    var direction = pointrData.circle.direction;
	    
	    //input of smart circle gesture (experimental/ not available yet)
	    var smartCircleEnabled = pointrData.circle.smart.enabled
	    var smartSegment = pointrData.circle.smart.segment
	    var smartSelectedSegment = pointrData.circle.smart.selectedSegment
	    
	    //visualization of the circle gesture
	    var radius = 128;
	    
	    
	    /* smart circle segment selection "animation" */
	    if (smartCircleEnabled && smartSelectedSegment) { 
		sc_ani_timeout = 60;
		sc_sel = smartSegment;
	    }
	    
	    /* circle */ 
	    if ((sc_ani_timeout>0) || podActive || direction) {
		context.beginPath();
		context.strokeStyle = '#00d000';
		context.lineWidth = 4;
		context.arc(320,240,radius,0,2*Math.PI);
		context.stroke();
	    }
	    if (sc_ani_timeout>0) {
		sc_ani_timeout--;
		segment = sc_sel - 1;
		var nSegments = 4;
		var segmentLength = 2 * Math.PI / nSegments;
		var phi0 = segmentLength * segment - 0.33 * Math.PI;
		var phi1 = segmentLength * segment + 0.33 * Math.PI;
		context.beginPath();
		context.save();
		context.globalAlpha=sc_ani_timeout/60;
		
		context.lineWidth = 32;
		context.strokeStyle = '#0080ff';
		context.lineCap = "round";
		context.arc(320,240,128,phi0,phi1);
		context.stroke();
		context.restore();
	    
	    }
	    /* further cicle graphics */
	    if (podActive || direction) {
  
		//draw the segment
		segment = -segment - 0.5;
		var nSegments = 8;
		var segmentLength = 2*Math.PI / nSegments;
		var phi0 = segmentLength * (segment-2);
		var phi1 = segmentLength * (segment-1);
		context.beginPath();
		    context.lineWidth = 16;
		    context.strokeStyle = '#00d000';
		    context.lineCap = "round";
		    context.arc(320,240,radius,phi0,phi1);
		context.stroke();
		if (direction) {
		    var x = 320 - Math.cos(phi + 0.5 * Math.PI) * radius;
		    var y = 240 - Math.sin(phi + 0.5 * Math.PI) * radius;
		    context.beginPath();
		    context.lineWidth = 2;
		    context.strokeStyle = 'black';
		    context.fillStyle = '#00ff00';
		    context.arc(x,y,16,0,2*Math.PI);
		    context.fill();
		    context.stroke();
		}
		
		//smart circle
		if (smartCircleEnabled){
		    /* mathematically positive is CCW */
		    segment = smartSegment -1 ;
		    var nSegments = 4;
		    var segmentLength = 2*Math.PI / nSegments;
		    var phi0 = segmentLength * segment - 0.33 * Math.PI;
		    var phi1 = segmentLength * segment + 0.33 * Math.PI;
		    context.beginPath();
		    context.lineWidth = 8;
		    context.strokeStyle = '#0000f0';
		    context.lineCap = "round";
		    context.arc(320,240,144,phi0,phi1);
		    context.stroke();
		}
	    }
	    
	    //input of the wipe gesture
	    var wipeLeft = (pointrData.events.indexOf('lwipe')!=-1)?true:false;
	    var wipeRight= (pointrData.events.indexOf('rwipe')!=-1)?true:false;
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
	    /* wipe feedback */
	    if (symbol) {
		context.save();
		context.globalAlpha=fadeOut/30;
		context.beginPath();
		context.lineWidth = 8;
		context.strokeStyle = '#4040ff';
		context.fillStyle = '#0000e0';
		context.lineCap = "round";
		switch(symbol) {
		    case 1: //left wipe
			context.moveTo(320-128, 240-96);
			context.lineTo(320+128, 240);
			context.lineTo(320-128, 240+96);
			context.lineTo(320-128, 240-96);
			break;
		    case 2:
			context.moveTo(320+128, 240-96);
			context.lineTo(320-128, 240);
			context.lineTo(320+128, 240+96);
			context.lineTo(320+128, 240-96);
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
	    
	    //input of the pointer coordinates
	    var px = pointrData.x * 640;
	    var py = pointrData.y * 480;
	    
	    //visualization of the pointer
	    context.fillStyle = 'red';
	    context.strokeStyle = 'red';
	    context.lineWidth = 2;
	    /* hotspot calculation */
	    var hsX = 0.5;
	    var hsY = 0.33;
	    var xOffs = pointrActiveImage.width * hsX;
	    var yOffs = pointrActiveImage.height * hsY;
			    if (pointrActiveImage.complete && pointrInactiveImage.complete) {
		if (pointrData.active) {
		    context.drawImage(pointrActiveImage,px - xOffs, py - yOffs);
		} else {
		    context.drawImage(pointrInactiveImage, px - xOffs, py - yOffs);
		}
	    } else {
		if (pointrData.active) {
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
    //building the websocket uri
    var ws_prefix = (window.location.protocol === 'https')?'wss':'ws';
    var ws_uri = ws_prefix + "://" + ws_host + ":" + ws_port + "/" + ws_path;
    console.log("Starting websocket comm...");
    mySocket = new WebSocket(ws_uri);
    
    //defintion of the websocket event handlers
    mySocket.onopen = function() {
	console.log("Socket opened");
    }
    mySocket.onclose = function(event) {
	console.log("websocket was closed...");
	var canvas = document.getElementById('gesture_preview');
	if(canvas.getContext)
	{
	    var context = canvas.getContext('2d');
	    context.clearRect(0, 0, canvas.width, canvas.height);
	}
	setTimeout(initSocket, 1000);
    };
    mySocket.onerror = function(error) {
	console.log("WebSocket error" + error);
	mySocket.onclose = function() {};
	mySocket.close();
	var canvas = document.getElementById('gesture_preview');
	if(canvas.getContext)
	{
	    var context = canvas.getContext('2d');
	    context.clearRect(0, 0, canvas.width, canvas.height);
	}

	setTimeout(initSocket, 1000);
    };
    
    //linking the message parsing function with the socket event "onmessage"
    mySocket.onmessage = function(msg) {
	onPointr(msg);
    };
}
