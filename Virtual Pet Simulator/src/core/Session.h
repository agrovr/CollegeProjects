#ifndef VPET_CORE_SESSION_H
#define VPET_CORE_SESSION_H

#include "core/Pet.h"

#include <cstdint>
#include <deque>
#include <memory>
#include <random>
#include <string>

namespace vpet {

enum class Action { Feed, Rest, Play, Special1, Special2, Wait };

enum class Animation { None, Eat, Sleep, Play, Special, Refuse, Event };

struct Outcome {
    Action action = Action::Wait;
    std::string message;      // what happened because of the action
    std::string event;        // a random event during the hour, or empty
    Stats before;
    Stats after;
    Animation animation = Animation::None;
    bool refused = false;
    bool stageChanged = false;
};

// Plays one pet: owns the clock, the random source and the event log, and applies the rules
// that sit around the pet's own stat changes (night, refusals, random events).
class Session {
public:
    static constexpr int startHour = 8;
    static constexpr std::size_t logSize = 6;

    Session(std::unique_ptr<Pet> petToPlay, std::uint32_t seed);

    Outcome perform(Action action);

    Pet& pet() { return *pet_; }
    const Pet& pet() const { return *pet_; }

    int day() const;           // 1-based
    int hourOfDay() const;     // 0-23
    bool isNight() const;      // 22:00 to 05:59
    std::string clockLabel() const;  // "Day 2 · 14:00"

    const std::deque<std::string>& log() const { return log_; }
    void note(const std::string& line);

private:
    bool refuses(Action action);

    std::unique_ptr<Pet> pet_;
    std::mt19937 rng_;
    std::deque<std::string> log_;
};

std::unique_ptr<Pet> makePet(const std::string& species, const std::string& name);

}  // namespace vpet

#endif
