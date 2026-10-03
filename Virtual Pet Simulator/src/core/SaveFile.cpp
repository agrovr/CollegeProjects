#include "core/SaveFile.h"

#include "core/Session.h"

#include <fstream>
#include <iomanip>
#include <istream>
#include <ostream>
#include <sstream>

namespace vpet {

namespace {
constexpr const char* headerV1 = "VIRTUAL_PET_SAVE_V1";
constexpr const char* headerV2 = "VIRTUAL_PET_SAVE_V2";

bool inRange(int value) {
    return value >= 0 && value <= 100;
}
}  // namespace

void writeSave(std::ostream& output, const Pet& pet) {
    const Stats& s = pet.stats();
    output << headerV2 << '\n'
           << pet.species() << '\n'
           << std::quoted(pet.name()) << '\n'
           << s.hunger << ' ' << s.fatigue << ' ' << s.boredom << ' '
           << s.happiness << ' ' << s.health << ' ' << s.discipline << '\n'
           << pet.ageHours() << ' ' << pet.bond() << '\n';
}

LoadResult readSave(std::istream& input) {
    LoadResult result;
    std::string header;
    std::string species;
    if (!std::getline(input, header)) {
        result.error = "The file is empty.";
        return result;
    }
    if (!header.empty() && header.back() == '\r') {
        header.pop_back();
    }
    const bool v2 = header == headerV2;
    if (!v2 && header != headerV1) {
        result.error = "This is not a virtual pet save.";
        return result;
    }
    if (!std::getline(input, species)) {
        result.error = "The save has no species.";
        return result;
    }
    if (!species.empty() && species.back() == '\r') {
        species.pop_back();
    }

    std::string name;
    Stats stats;
    if (!(input >> std::quoted(name) >> stats.hunger >> stats.fatigue >> stats.boredom
          >> stats.happiness >> stats.health >> stats.discipline)) {
        result.error = "The save data is incomplete.";
        return result;
    }
    int age = 0;
    int bond = 0;
    if (v2 && !(input >> age >> bond)) {
        result.error = "The save data is incomplete.";
        return result;
    }
    std::string extra;
    if (input >> extra) {
        result.error = "The save has unexpected extra data.";
        return result;
    }
    if (name.empty() || !inRange(stats.hunger) || !inRange(stats.fatigue) || !inRange(stats.boredom)
        || !inRange(stats.happiness) || !inRange(stats.health) || !inRange(stats.discipline)
        || age < 0 || !inRange(bond)) {
        result.error = "The save has values out of range.";
        return result;
    }

    result.pet = makePet(species, name);
    if (!result.pet) {
        result.error = "Unknown species: " + species + ".";
        return result;
    }
    result.pet->restore(name, stats, age, bond);
    return result;
}

bool saveToFile(const std::string& path, const Pet& pet, std::string& error) {
    std::ofstream output(path);
    if (!output) {
        error = "Unable to write " + path + ".";
        return false;
    }
    writeSave(output, pet);
    output.flush();
    if (!output) {
        error = "The save to " + path + " did not complete.";
        return false;
    }
    return true;
}

LoadResult loadFromFile(const std::string& path) {
    std::ifstream input(path);
    if (!input) {
        LoadResult result;
        result.error = "Unable to open " + path + ".";
        return result;
    }
    return readSave(input);
}

}  // namespace vpet
