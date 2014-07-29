#!/usr/bin/env node
var hid = require('node-hid');
var mqtt = require('mqtt');
var sleep = require('sleep');

var port = 1883;
var host = 'atlas.hasi';
var topic = 'hasi/code_scanner';

var vendorId = 0x05e0;
var productId = 0x0200;

var client = null;

function fromHIDToChar(data) {
	if (data == 0x28) {
		return '\n';
	} else if (data >= 0x1D) {
		return String.fromCharCode((data - 0x1D) % 10 + 0x30);
	} else if (data >= 0x03) {
		return String.fromCharCode(data + 0x5D);
	} else {
		return null;
	}
}

function connectMQTT(port, host) {
	console.log('Connecting to MQTT broker ' + host + ' on port ' + port + '.');

	client = mqtt.createClient(port, host);

	client.on('error', function(packet) {
		console('An error occured. Reconnecting now...')
		client.stream.end();
		client = null;

		connectMQTT(port, host);
	});
}

function connectHID(vendorId, productId, callback) {
	var devices = [];
	var scanners = [];

	while (scanners.length == 0) {
		devices = hid.devices();
		scanners = devices.filter(function (obj) {
			return (obj.vendorId == vendorId) && (obj.productId == productId);
		});

		sleep.sleep(1);
	}

	callback(new hid.HID(scanners[0].path));
}

function readHID(device) {
	var buffer = '';

	device.on('data', function (data) {
		character = fromHIDToChar(data[2]);
		if (character) {
			if (character != '\n') {
				buffer += character;
			} else {
				console.log('Scanned ' + buffer);

				client.publish(topic, buffer);

				buffer = '';
			}
		}
	});

	device.on('error', function (err) {
		console.log(err);

		connectHID(vendorId, productId, readHID);
	});
}

connectMQTT(port, host);
connectHID(vendorId, productId, readHID);
