#include "Arduino.h"
#include "Wire.h"
#include "AD5252.h"
#include "EMSSystem.h"
#include "EMSChannel.h"

// DEBUG: setup for verbose mode (prints debug messages)
#define DEBUG_ON 1

// No custom printer needed, just use Serial.println
void debugPrint(String msg) {
  if (DEBUG_ON) {
    Serial.println(msg);
  }
}

// Initialize control objects
AD5252 digitalPot(0); // I2C address 0
EMSChannel emsChannel1(5, 4, A2, &digitalPot, 1); // Pins and channel 1 on digipot
EMSChannel emsChannel2(6, 7, A3, &digitalPot, 3); // Pins and channel 3 on digipot
EMSSystem emsSystem(2); // 2 channels

void setup() {
  Serial.begin(19200);
  debugPrint("\nSETUP:");
  
  // Initialize EMS system
  debugPrint("\tEMS: Initializing Channels");
  emsSystem.addChannelToSystem(&emsChannel1);
  emsSystem.addChannelToSystem(&emsChannel2);
  EMSSystem::start();
  debugPrint("\tEMS: Initialized and Started");

  // Setup pin 13 LED
  pinMode(13, OUTPUT);
  digitalWrite(13, HIGH);
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    command = tolower(command); // handle both uppercase and lowercase
    handleCommand(command);
    Serial.flush();
  }

  // Check if EMS needs to be stopped
  emsSystem.check();
}

void handleCommand(char c) {
  if (c == 'q') {
    increaseIntensity(emsChannel1, 1);
  } else if (c == 'a') {
    decreaseIntensity(emsChannel1, 1);
  } else if (c == 'w') {
    increaseIntensity(emsChannel2, 3);
  } else if (c == 's') {
    decreaseIntensity(emsChannel2, 3);
  } else if (c == '1') {
    toggleChannel(emsChannel1);
  } else if (c == '2') {
    toggleChannel(emsChannel2);
  } else {
    debugPrint("\tUnknown Command");
  }
}

// Increase intensity by ~5%
void increaseIntensity(EMSChannel& channel, int digipotChannel) {
  int currentPosition = digitalPot.getPosition(digipotChannel);
  int decrement = (int)(255 * 0.05); // 5% of max 255
  int newPosition = max(currentPosition - decrement, 0); // ensure not below 0
  digitalPot.setPosition(digipotChannel, newPosition);
  debugPrint("\tIncreased Intensity. New Digipot Pos: " + String(newPosition));
}

// Decrease intensity by ~5%
void decreaseIntensity(EMSChannel& channel, int digipotChannel) {
  int currentPosition = digitalPot.getPosition(digipotChannel);
  int increment = (int)(255 * 0.05); // 5% of max 255
  int newPosition = min(currentPosition + increment, 255); // ensure not above 255
  digitalPot.setPosition(digipotChannel, newPosition);
  debugPrint("\tDecreased Intensity. New Digipot Pos: " + String(newPosition));
}

// Toggle the EMS channel (activate/deactivate)
void toggleChannel(EMSChannel& channel) {
  if (channel.isActivated()) {
    channel.deactivate();
    debugPrint("\tChannel Deactivated");
  } else {
    channel.activate();
    debugPrint("\tChannel Activated");
  }
}
