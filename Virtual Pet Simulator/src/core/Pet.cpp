#include "core/Pet.h"

#include <algorithm>
#include <utility>

namespace vpet {

Pet::Pet(std::string petName) : name_(std::move(petName)) {}

StatChange Pet::feed() {
    StatChange change;
    change.hunger = -25;
    change.health = 4;
    change.happiness = 2;
    if (stats_.hunger < 10) {
        // Already full: overfeeding is unpleasant.
        change.happiness = -3;
        change.health = -2;
    }
    apply(change);
    return change;
}

StatChange Pet::rest(bool atNight) {
    StatChange change;
    change.fatigue = atNight ? -40 : -30;
    change.health = atNight ? 8 : 6;
    apply(change);
    return change;
}

StatChange Pet::play() {
    StatChange change;
    change.boredom = -25;
    change.fatigue = 8;
    change.happiness = 10;
    apply(change);
    return change;
}

StatChange Pet::performSpecial(std::size_t index) {
    const StatChange change = specialActions().at(index).change;
    apply(change);
    return change;
}

void Pet::advanceHour(bool atNight) {
    StatChange change;
    change.hunger = 8;
    change.fatigue = atNight ? 9 : 6;
    change.boredom = 7;
    apply(change);

    const int unmet = unmetNeeds();
    if (unmet > 0) {
        StatChange penalty;
        penalty.health = -4 * unmet;
        penalty.happiness = -5 * unmet;
        apply(penalty);
    } else {
        StatChange reward;
        reward.happiness = 1;
        apply(reward);
        if (stats_.happiness >= 60) {
            bond_ = std::min(100, bond_ + 1);
        }
    }
    ++ageHours_;
}

void Pet::apply(const StatChange& change) {
    stats_.hunger = clampStat(stats_.hunger + change.hunger);
    stats_.fatigue = clampStat(stats_.fatigue + change.fatigue);
    stats_.boredom = clampStat(stats_.boredom + change.boredom);
    stats_.happiness = clampStat(stats_.happiness + change.happiness);
    stats_.health = clampStat(stats_.health + change.health);
    stats_.discipline = clampStat(stats_.discipline + change.discipline);
}

int Pet::unmetNeeds() const {
    return (stats_.hunger >= unmetNeedThreshold ? 1 : 0)
         + (stats_.fatigue >= unmetNeedThreshold ? 1 : 0)
         + (stats_.boredom >= unmetNeedThreshold ? 1 : 0);
}

Mood Pet::mood() const {
    if (stats_.health < 30) {
        return Mood::Unwell;
    }
    // The most pressing need wins.
    const int worst = std::max({stats_.hunger, stats_.fatigue, stats_.boredom});
    if (worst >= 60) {
        if (worst == stats_.hunger) {
            return Mood::Hungry;
        }
        if (worst == stats_.fatigue) {
            return Mood::Sleepy;
        }
        return Mood::Bored;
    }
    if (stats_.happiness < 35) {
        return Mood::Grumpy;
    }
    if (stats_.happiness >= 80) {
        return Mood::Joyful;
    }
    return Mood::Content;
}

LifeStage Pet::stage() const {
    if (ageHours_ < hatchlingHours) {
        return LifeStage::Hatchling;
    }
    if (ageHours_ < juvenileHours) {
        return LifeStage::Juvenile;
    }
    return LifeStage::Adult;
}

void Pet::restore(const std::string& newName, const Stats& newStats, int newAgeHours, int newBond) {
    name_ = newName;
    stats_ = newStats;
    ageHours_ = std::max(0, newAgeHours);
    bond_ = std::clamp(newBond, 0, 100);
}

int Pet::clampStat(int value) {
    return std::clamp(value, 0, 100);
}

std::string Pet::fill(const std::string& text, const std::string& name) {
    std::string result = text;
    const std::string token = "{name}";
    for (std::size_t at = result.find(token); at != std::string::npos; at = result.find(token, at + name.size())) {
        result.replace(at, token.size(), name);
    }
    return result;
}

const char* moodName(Mood mood) {
    switch (mood) {
        case Mood::Joyful: return "Joyful";
        case Mood::Content: return "Content";
        case Mood::Hungry: return "Hungry";
        case Mood::Sleepy: return "Sleepy";
        case Mood::Bored: return "Bored";
        case Mood::Grumpy: return "Grumpy";
        case Mood::Unwell: return "Unwell";
    }
    return "Content";
}

const char* stageName(LifeStage stage) {
    switch (stage) {
        case LifeStage::Hatchling: return "Hatchling";
        case LifeStage::Juvenile: return "Juvenile";
        case LifeStage::Adult: return "Adult";
    }
    return "Hatchling";
}

}  // namespace vpet
