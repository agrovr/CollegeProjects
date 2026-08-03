#include "Unicorn.h"

Unicorn::Unicorn(const std::string& name) : Pet(name) {}

std::string Unicorn::species() const {
    return "Unicorn";
}

std::array<std::string, 2> Unicorn::specialActionNames() const {
    return {"Restore vitality", "Shape a light spell"};
}

std::string Unicorn::performSpecialAction(std::size_t index) {
    if (index == 0) {
        adjustHealth(18);
        adjustFatigue(6);
        adjustHappiness(4);
        return petName() + " releases a calm restorative glow.";
    }

    adjustBoredom(-16);
    adjustFatigue(10);
    adjustHappiness(10);
    adjustDiscipline(5);
    return petName() + " forms a bright constellation in the air.";
}
