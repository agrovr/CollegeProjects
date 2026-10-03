#ifndef VPET_CORE_SAVEFILE_H
#define VPET_CORE_SAVEFILE_H

#include "core/Pet.h"

#include <iosfwd>
#include <memory>
#include <string>

namespace vpet {

// Save format, version 2:
//
//   VIRTUAL_PET_SAVE_V2
//   Dragon
//   "Ember"
//   42 57 23 89 100 61        hunger fatigue boredom happiness health discipline
//   30 4                      age in hours, bond
//
// Version 1 files (no last line) still load, starting at age 0 and bond 0.
struct LoadResult {
    std::unique_ptr<Pet> pet;
    std::string error;  // empty on success
};

void writeSave(std::ostream& output, const Pet& pet);
LoadResult readSave(std::istream& input);

bool saveToFile(const std::string& path, const Pet& pet, std::string& error);
LoadResult loadFromFile(const std::string& path);

}  // namespace vpet

#endif
