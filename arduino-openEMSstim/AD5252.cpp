#include "AD5252.h"
#include "Wire.h"

AD5252::AD5252(uint8_t address) {
    this->address = address;
}

AD5252::~AD5252() {
}

void AD5252::setPosition(uint8_t wiperIndex, uint8_t whiperPosition) {
    Wire.beginTransmission(this->address);
    Wire.write(wiperIndex);
    Wire.write(whiperPosition);
    Wire.endTransmission(true);
}

uint8_t AD5252::getPosition(uint8_t wiperIndex) {
    Wire.beginTransmission(this->address);
    Wire.write(wiperIndex);
    Wire.endTransmission();
    Wire.requestFrom(this->address, (uint8_t)1);
    return Wire.read();
}

void AD5252::increment(uint8_t wiperIndex) {
    uint8_t pos = getPosition(wiperIndex);
    if (pos > 0) {
        setPosition(wiperIndex, pos - 1);
    }
}

void AD5252::decrement(uint8_t wiperIndex) {
    uint8_t pos = getPosition(wiperIndex);
    if (pos < 255) {
        setPosition(wiperIndex, pos + 1);
    }
}

void AD5252::increment(uint8_t wiperIndex, int steps, int stepDelay) {
    for (int i = 0; i < steps; i++) {
        increment(wiperIndex);
        delay(stepDelay);
    }
}

void AD5252::decrement(uint8_t wiperIndex, int steps, int stepDelay) {
    for (int i = 0; i < steps; i++) {
        decrement(wiperIndex);
        delay(stepDelay);
    }
}
