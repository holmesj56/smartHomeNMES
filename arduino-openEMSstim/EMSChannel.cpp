#include "Arduino.h"
#include "Wire.h"
#include "AD5252.h"
#include "EMSSystem.h"
#include "EMSChannel.h"
#include "avr/pgmspace.h"

// DEBUG mode
#define DEBUG_ON 1

// USB Commands mode
#define USB_FULL_COMMANDS_ACTIVE 1 
#define USB_TEST_COMMANDS_ACTIVE 0

// Forward‐declare these so loop() can see them
void processMessage(String message);
void doCommand(char c);

// Helper print function
void printer(String msg, boolean force = false) {
  if (DEBUG_ON || force) {
    Serial.println(msg);
  }
}

// Track EMS intensity manually
int digipotChannel1Position = 255;  // Start at max resistance (no EMS)
int digipotChannel2Position = 255;  // Start at max resistance (no EMS)

// Track PWM Pulse Width manually
int pwmPulseWidthChannel1 = 128;  // Start at 50% duty cycle
int pwmPulseWidthChannel2 = 128;  // Start at 50% duty cycle
const int pwmStepSize = 10;        // PWM step size per button press

// Initialize control objects
AD5252 digitalPot(0);  // I2C address 0
EMSChannel emsChannel1(5, 4, A2, &digitalPot, 1);  // PWM, enable, feedback, digipot, channel #
EMSChannel emsChannel2(6, 7, A3, &digitalPot, 3);  // Channel 2 uses digipot channel 3
EMSSystem emsSystem(2);

void setup() {
  Serial.begin(19200);
  Serial.setTimeout(50);
  printer("\nSETUP:");
  Serial.flush();

  // Setup PWM output pins
  pinMode(5, OUTPUT); // Channel 1 PWM
  pinMode(6, OUTPUT); // Channel 2 PWM

  analogWrite(5, pwmPulseWidthChannel1);
  analogWrite(6, pwmPulseWidthChannel2);

  printer("\tEMS: INITIALIZING CHANNELS");
  emsSystem.addChannelToSystem(&emsChannel1);
  emsSystem.addChannelToSystem(&emsChannel2);
  EMSSystem::start();
  printer("\tEMS: INITIALIZED");
  printer("\tEMS: STARTED");

  pinMode(13, OUTPUT);
  digitalWrite(13, HIGH);  // Turn LED ON
  printer("SETUP DONE (LED 13 WILL BE ON)");
}

void loop() {
  if (Serial.available() > 0) {
    if (USB_FULL_COMMANDS_ACTIVE) {
      String message = Serial.readStringUntil('\n');
      message.trim();
      printer("\tUSB: received command: " + message);
      processMessage(message);
    } else if (USB_TEST_COMMANDS_ACTIVE) {
      char c = Serial.read();
      printer("\tUSB-TEST-MODE: received command: " + String(c));
      doCommand(c);
    }
    Serial.flush();
  }

  if (emsSystem.check() > 0) {
    // placeholder for timed shutdowns if needed
  }
}

// Convert HEX string ("4D") to one byte
char convertToHexCharsToOneByte(char one, char two) {
  char byteOne = convertHexCharToByte(one);
  char byteTwo = convertHexCharToByte(two);
  if (byteOne != -1 && byteTwo != -1)
    return byteOne * 16 + byteTwo;
  else
    return -1;
}

char convertHexCharToByte(char hexChar) {
  if (hexChar >= 'A' && hexChar <= 'F') {
    return hexChar - 'A' + 10;
  } else if (hexChar >= '0' && hexChar <= '9') {
    return hexChar - '0';
  } else {
    return -1;
  }
}

// Status messages
const char ems_channel_1_active[]    PROGMEM = "\tEMS: Channel 1 active";
const char ems_channel_1_inactive[]  PROGMEM = "\tEMS: Channel 1 inactive";
const char ems_channel_2_active[]    PROGMEM = "\tEMS: Channel 2 active";
const char ems_channel_2_inactive[]  PROGMEM = "\tEMS: Channel 2 inactive";
const char ems_channel_1_intensity[] PROGMEM = "\tEMS: Intensity Channel 1: ";
const char ems_channel_2_intensity[] PROGMEM = "\tEMS: Intensity Channel 2: ";

const char* const string_table_outputs[] PROGMEM = {
  ems_channel_1_active, ems_channel_1_inactive,
  ems_channel_2_active, ems_channel_2_inactive,
  ems_channel_1_intensity, ems_channel_2_intensity
};

char buffer[32];

void processMessage(String message) {
  if (message.startsWith("WV")) {  // HEX command
    int lastIndexOfComma = message.lastIndexOf(',');
    String hexCommandString = message.substring(lastIndexOfComma + 1, message.length() - 1);
    String command = "";
    printer("\tEMS_CMD: HEX command length: " + String(hexCommandString.length()));
    printer(hexCommandString);

    for (unsigned int i = 0; i < hexCommandString.length(); i += 2) {
      char nextChar = convertToHexCharsToOneByte(hexCommandString.charAt(i), hexCommandString.charAt(i + 1));
      command += nextChar;
    }

    printer("\tEMS_CMD: Converted HEX command:");
    printer(command);
    emsSystem.doCommand(&command);
  } else {
    printer("\tCommand NON HEX:");
    printer(message);
    doCommand(message[0]);
  }
}

void doCommand(char c) {
  if (c == '1') {
    if (emsChannel1.isActivated()) {
      emsChannel1.deactivate();
      strcpy_P(buffer, (char*)pgm_read_word(&(string_table_outputs[1])));
      printer(buffer);
    } else {
      emsChannel1.activate();
      strcpy_P(buffer, (char*)pgm_read_word(&(string_table_outputs[0])));
      printer(buffer);
    }
  }
  // ... (all your other else‐ifs for '2', 'a', 'q', 's', 'w', 'u', 'j')
  else {
    printer("\tERROR: SINGLE-CHAR Command Unknown");
  }
}
