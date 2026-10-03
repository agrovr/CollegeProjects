#ifndef VPET_CORE_PET_H
#define VPET_CORE_PET_H

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace vpet {

// The six needs every pet has. All values stay between 0 and 100.
struct Stats {
    int hunger = 35;
    int fatigue = 25;
    int boredom = 30;
    int happiness = 70;
    int health = 100;
    int discipline = 50;
};

// A change to one or more stats, used by care actions, abilities and random events.
struct StatChange {
    int hunger = 0;
    int fatigue = 0;
    int boredom = 0;
    int happiness = 0;
    int health = 0;
    int discipline = 0;
};

enum class Mood { Joyful, Content, Hungry, Sleepy, Bored, Grumpy, Unwell };
enum class LifeStage { Hatchling, Juvenile, Adult };

// A species-flavoured random event that can happen as an hour passes.
struct PetEvent {
    std::string text;  // "{name}" is replaced with the pet's name
    StatChange change;
};

struct SpecialAction {
    std::string name;      // menu label, e.g. "Flight training"
    std::string verb;      // short label for the action bar, e.g. "Fly"
    std::string message;   // "{name}" is replaced with the pet's name
    StatChange change;
};

class Pet {
public:
    static constexpr int unmetNeedThreshold = 75;
    static constexpr int hatchlingHours = 24;
    static constexpr int juvenileHours = 72;

    explicit Pet(std::string name);
    virtual ~Pet() = default;

    // Species identity and abilities.
    virtual std::string species() const = 0;
    virtual std::array<SpecialAction, 2> specialActions() const = 0;
    virtual std::vector<PetEvent> events() const = 0;

    // Care actions. Each returns the stat change it applied.
    StatChange feed();
    StatChange rest(bool atNight);
    StatChange play();
    StatChange performSpecial(std::size_t index);

    // One hour of time: needs grow, unmet needs hurt, and the pet ages.
    void advanceHour(bool atNight);

    void apply(const StatChange& change);

    const std::string& name() const { return name_; }
    const Stats& stats() const { return stats_; }
    int ageHours() const { return ageHours_; }
    int bond() const { return bond_; }
    int unmetNeeds() const;
    Mood mood() const;
    LifeStage stage() const;

    // Persistence helpers for SaveFile.
    void restore(const std::string& name, const Stats& stats, int ageHours, int bond);

    static int clampStat(int value);
    static std::string fill(const std::string& text, const std::string& name);

private:
    std::string name_;
    Stats stats_;
    int ageHours_ = 0;
    int bond_ = 0;
};

const char* moodName(Mood mood);
const char* stageName(LifeStage stage);

}  // namespace vpet

#endif
