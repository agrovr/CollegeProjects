#include "Pet.h"

#include <iomanip>
#include <iostream>
#include <utility>

Pet::Pet(std::string name) : name(std::move(name)) {}

void Pet::feed() {
    adjustHunger(-25);
    adjustHealth(4);
    adjustHappiness(2);
}

void Pet::rest() {
    adjustFatigue(-30);
    adjustHealth(6);
}

void Pet::play() {
    adjustBoredom(-25);
    adjustFatigue(8);
    adjustHappiness(10);
}

void Pet::advanceHour() {
    adjustHunger(8);
    adjustFatigue(6);
    adjustBoredom(7);

    const int unmetNeeds = (hunger >= 75 ? 1 : 0) + (fatigue >= 75 ? 1 : 0) + (boredom >= 75 ? 1 : 0);
    if (unmetNeeds > 0) {
        adjustHealth(-4 * unmetNeeds);
        adjustHappiness(-5 * unmetNeeds);
    } else {
        adjustHappiness(1);
    }
}

void Pet::displayStatus(std::ostream& output) const {
    output << "\n" << name << " the " << species() << "\n"
           << "Health:    " << health << "/100\n"
           << "Happiness: " << happiness << "/100\n"
           << "Hunger:    " << hunger << "/100\n"
           << "Fatigue:   " << fatigue << "/100\n"
           << "Boredom:   " << boredom << "/100\n"
           << "Discipline:" << ' ' << discipline << "/100\n";
}

void Pet::saveState(std::ostream& output) const {
    output << std::quoted(name) << '\n'
           << hunger << ' ' << fatigue << ' ' << boredom << ' '
           << happiness << ' ' << health << ' ' << discipline << '\n';
}

bool Pet::loadState(std::istream& input) {
    std::string loadedName;
    int loadedHunger = 0;
    int loadedFatigue = 0;
    int loadedBoredom = 0;
    int loadedHappiness = 0;
    int loadedHealth = 0;
    int loadedDiscipline = 0;

    if (!(input >> std::quoted(loadedName)
          >> loadedHunger >> loadedFatigue >> loadedBoredom
          >> loadedHappiness >> loadedHealth >> loadedDiscipline)) {
        return false;
    }

    const auto valid = [](int value) { return value >= 0 && value <= 100; };
    if (loadedName.empty() || !valid(loadedHunger) || !valid(loadedFatigue)
        || !valid(loadedBoredom) || !valid(loadedHappiness)
        || !valid(loadedHealth) || !valid(loadedDiscipline)) {
        return false;
    }

    name = std::move(loadedName);
    hunger = loadedHunger;
    fatigue = loadedFatigue;
    boredom = loadedBoredom;
    happiness = loadedHappiness;
    health = loadedHealth;
    discipline = loadedDiscipline;
    return true;
}

void Pet::adjustHunger(int amount) {
    hunger = clampStat(hunger + amount);
}

void Pet::adjustFatigue(int amount) {
    fatigue = clampStat(fatigue + amount);
}

void Pet::adjustBoredom(int amount) {
    boredom = clampStat(boredom + amount);
}

void Pet::adjustHappiness(int amount) {
    happiness = clampStat(happiness + amount);
}

void Pet::adjustHealth(int amount) {
    health = clampStat(health + amount);
}

void Pet::adjustDiscipline(int amount) {
    discipline = clampStat(discipline + amount);
}

const std::string& Pet::petName() const {
    return name;
}

int Pet::clampStat(int value) {
    if (value < 0) {
        return 0;
    }
    if (value > 100) {
        return 100;
    }
    return value;
}
