#include "core/Session.h"

#include "core/species/Dragon.h"
#include "core/species/MysticCat.h"
#include "core/species/Unicorn.h"

#include <cstdio>
#include <utility>

namespace vpet {

namespace {
constexpr double eventChance = 0.14;
constexpr int refusalDiscipline = 25;
}

Session::Session(std::unique_ptr<Pet> petToPlay, std::uint32_t seed) : pet_(std::move(petToPlay)), rng_(seed) {}

Outcome Session::perform(Action action) {
    Pet& current = *pet_;
    Outcome outcome;
    outcome.action = action;
    outcome.before = current.stats();
    const LifeStage stageBefore = current.stage();
    const bool night = isNight();
    const std::string& name = current.name();

    if (refuses(action)) {
        outcome.refused = true;
        outcome.animation = Animation::Refuse;
        outcome.message = name + " ignores you and does something else entirely.";
        StatChange sulk;
        sulk.boredom = -4;
        current.apply(sulk);
    } else {
        switch (action) {
            case Action::Feed: {
                const bool full = current.stats().hunger < 10;
                current.feed();
                outcome.animation = Animation::Eat;
                outcome.message = full ? name + " was already full and feels a bit queasy."
                                       : name + " enjoys a balanced meal.";
                break;
            }
            case Action::Rest:
                current.rest(night);
                outcome.animation = Animation::Sleep;
                outcome.message = night ? name + " sleeps soundly through the night hour."
                                        : name + " takes a restful nap.";
                break;
            case Action::Play:
                current.play();
                outcome.animation = Animation::Play;
                outcome.message = "Playtime! " + name + " is in high spirits.";
                break;
            case Action::Special1:
            case Action::Special2: {
                const std::size_t index = action == Action::Special1 ? 0 : 1;
                current.performSpecial(index);
                outcome.animation = Animation::Special;
                outcome.message = Pet::fill(current.specialActions()[index].message, name);
                break;
            }
            case Action::Wait:
                outcome.message = "An hour passes quietly.";
                break;
        }
    }

    current.advanceHour(night);

    std::uniform_real_distribution<double> chance(0.0, 1.0);
    const std::vector<PetEvent> events = current.events();
    if (!events.empty() && chance(rng_) < eventChance) {
        std::uniform_int_distribution<std::size_t> pick(0, events.size() - 1);
        const PetEvent& event = events[pick(rng_)];
        current.apply(event.change);
        outcome.event = Pet::fill(event.text, name);
        if (outcome.animation == Animation::None) {
            outcome.animation = Animation::Event;
        }
    }

    outcome.after = current.stats();
    outcome.stageChanged = current.stage() != stageBefore;

    note(outcome.message);
    if (!outcome.event.empty()) {
        note(outcome.event);
    }
    if (outcome.stageChanged) {
        note(name + " has grown into a " + stageName(current.stage()) + "!");
    }
    return outcome;
}

bool Session::refuses(Action action) {
    const bool trainable = action == Action::Play || action == Action::Special1 || action == Action::Special2;
    const int discipline = pet_->stats().discipline;
    if (!trainable || discipline >= refusalDiscipline) {
        return false;
    }
    // Up to a 50% chance at zero discipline, falling to 0% at the threshold.
    const double probability = 0.5 * (refusalDiscipline - discipline) / refusalDiscipline;
    std::uniform_real_distribution<double> chance(0.0, 1.0);
    return chance(rng_) < probability;
}

int Session::day() const {
    return (startHour + pet_->ageHours()) / 24 + 1;
}

int Session::hourOfDay() const {
    return (startHour + pet_->ageHours()) % 24;
}

bool Session::isNight() const {
    const int hour = hourOfDay();
    return hour >= 22 || hour < 6;
}

std::string Session::clockLabel() const {
    char buffer[32];
    std::snprintf(buffer, sizeof(buffer), "Day %d · %02d:00", day(), hourOfDay());
    return buffer;
}

void Session::note(const std::string& line) {
    log_.push_back(line);
    while (log_.size() > logSize) {
        log_.pop_front();
    }
}

std::unique_ptr<Pet> makePet(const std::string& species, const std::string& name) {
    if (species == "Dragon") {
        return std::make_unique<Dragon>(name);
    }
    if (species == "Unicorn") {
        return std::make_unique<Unicorn>(name);
    }
    if (species == "Mystic Cat") {
        return std::make_unique<MysticCat>(name);
    }
    return nullptr;
}

}  // namespace vpet
