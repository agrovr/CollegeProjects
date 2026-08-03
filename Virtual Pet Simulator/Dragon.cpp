#include "Dragon.h"

Dragon::Dragon(const std::string& name) : Pet(name) {}

std::string Dragon::species() const {
    return "Dragon";
}

std::array<std::string, 2> Dragon::specialActionNames() const {
    return {"Complete flight training", "Breathe a controlled flame"};
}

std::string Dragon::performSpecialAction(std::size_t index) {
    if (index == 0) {
        adjustFatigue(14);
        adjustBoredom(-18);
        adjustHappiness(8);
        adjustDiscipline(4);
        return petName() + " completes a sweeping flight circuit.";
    }

    adjustHunger(8);
    adjustBoredom(-10);
    adjustHappiness(6);
    adjustDiscipline(7);
    return petName() + " shapes a precise ribbon of flame.";
}
