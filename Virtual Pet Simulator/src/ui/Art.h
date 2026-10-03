#ifndef VPET_UI_ART_H
#define VPET_UI_ART_H

#include "core/Pet.h"

#include <string>
#include <vector>

namespace vpet {

// Creature art. Templates use '@' for the left eye, '#' for the right eye and '&&' for a
// two-character mouth, so one drawing can show every mood and blink.
struct Face {
    char leftEye;
    char rightEye;
    char mouth[2];
};

Face faceFor(Mood mood, bool blinking);

// Lines for a species at a life stage, with the face filled in. Every line has the same width.
std::vector<std::string> creatureArt(const std::string& species, LifeStage stage, const Face& face);

// A small three-line portrait used on the title screen and species picker.
std::vector<std::string> creaturePortrait(const std::string& species);

}  // namespace vpet

#endif
