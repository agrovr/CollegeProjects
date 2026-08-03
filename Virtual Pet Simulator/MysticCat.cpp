#include "MysticCat.h"

MysticCat::MysticCat(const std::string& name) : Pet(name) {}

std::string MysticCat::species() const {
    return "Mystic Cat";
}

std::array<std::string, 2> MysticCat::specialActionNames() const {
    return {"Focus telekinesis", "Study a new trick"};
}

std::string MysticCat::performSpecialAction(std::size_t index) {
    if (index == 0) {
        adjustFatigue(12);
        adjustBoredom(-14);
        adjustHappiness(7);
        adjustDiscipline(6);
        return petName() + " carefully lifts a toy with focused thought.";
    }

    adjustBoredom(-20);
    adjustHappiness(9);
    adjustDiscipline(8);
    adjustHunger(5);
    return petName() + " masters a clever new trick.";
}
