// Unit tests for the game rules. No framework: each test is a function, and CHECK records
// failures without stopping the run.

#include "core/Pet.h"
#include "core/SaveFile.h"
#include "core/Session.h"
#include "ui/Art.h"

#include <functional>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace vpet;

namespace {

int failures = 0;

#define CHECK(condition)                                                                   \
    do {                                                                                   \
        if (!(condition)) {                                                                \
            ++failures;                                                                    \
            std::cerr << "  FAILED " << __FILE__ << ":" << __LINE__ << "  " #condition "\n"; \
        }                                                                                  \
    } while (false)

std::unique_ptr<Pet> dragon(const std::string& name = "Ember") {
    return makePet("Dragon", name);
}

void startsWithDefaultStats() {
    auto pet = dragon();
    CHECK(pet->stats().hunger == 35);
    CHECK(pet->stats().health == 100);
    CHECK(pet->ageHours() == 0);
    CHECK(pet->stage() == LifeStage::Hatchling);
    CHECK(pet->species() == "Dragon");
}

void statsStayInRange() {
    auto pet = dragon();
    StatChange big;
    big.hunger = 500;
    big.health = -500;
    pet->apply(big);
    CHECK(pet->stats().hunger == 100);
    CHECK(pet->stats().health == 0);
}

void feedingReducesHungerButOverfeedingHurts() {
    auto pet = dragon();
    pet->feed();
    CHECK(pet->stats().hunger == 10);
    CHECK(pet->stats().health == 100);
    pet->feed();  // hunger was 10, not below 10: still a normal meal
    CHECK(pet->stats().hunger == 0);
    const int happiness = pet->stats().happiness;
    pet->feed();  // now full
    CHECK(pet->stats().happiness == happiness - 3);
    CHECK(pet->stats().health == 98);
}

void restingAtNightRestoresMore() {
    auto day = dragon();
    auto night = dragon();
    StatChange tired;
    tired.fatigue = 60;
    day->apply(tired);
    night->apply(tired);
    day->rest(false);
    night->rest(true);
    CHECK(day->stats().fatigue == 55);
    CHECK(night->stats().fatigue == 45);
}

void unmetNeedsHurtHealthAndMood() {
    auto pet = dragon();
    StatChange starving;
    starving.hunger = 60;  // 95
    pet->apply(starving);
    const Stats before = pet->stats();
    pet->advanceHour(false);
    CHECK(pet->unmetNeeds() == 1);
    CHECK(pet->stats().health == before.health - 4);
    CHECK(pet->stats().happiness == before.happiness - 5);
    CHECK(pet->ageHours() == 1);
}

void caredForHoursBuildBond() {
    auto pet = dragon();
    StatChange cheerful;
    cheerful.happiness = 20;
    pet->apply(cheerful);
    pet->advanceHour(false);
    CHECK(pet->bond() == 1);
}

void moodReflectsTheWorstNeed() {
    auto pet = dragon();
    CHECK(pet->mood() == Mood::Content);
    StatChange change;
    change.fatigue = 50;  // 75
    pet->apply(change);
    CHECK(pet->mood() == Mood::Sleepy);
    change = StatChange{};
    change.health = -80;
    pet->apply(change);
    CHECK(pet->mood() == Mood::Unwell);
}

void petsGrowUp() {
    auto pet = dragon();
    pet->restore("Ember", pet->stats(), 23, 0);
    CHECK(pet->stage() == LifeStage::Hatchling);
    pet->advanceHour(false);
    CHECK(pet->stage() == LifeStage::Juvenile);
    pet->restore("Ember", pet->stats(), 72, 0);
    CHECK(pet->stage() == LifeStage::Adult);
}

void speciesHaveDistinctAbilities() {
    auto unicorn = makePet("Unicorn", "Luna");
    StatChange hurt;
    hurt.health = -50;
    unicorn->apply(hurt);
    unicorn->performSpecial(0);  // Restore vitality
    CHECK(unicorn->stats().health == 68);
    auto cat = makePet("Mystic Cat", "Miso");
    CHECK(cat->specialActions()[1].name == "Study a trick");
    CHECK(makePet("Griffin", "x") == nullptr);
}

void sessionTracksTimeOfDay() {
    Session session(dragon(), 1);
    CHECK(session.day() == 1);
    CHECK(session.hourOfDay() == 8);
    CHECK(!session.isNight());
    for (int i = 0; i < 14; ++i) {
        session.perform(Action::Wait);
    }
    CHECK(session.hourOfDay() == 22);
    CHECK(session.isNight());
    CHECK(session.clockLabel() == "Day 1 · 22:00");
    for (int i = 0; i < 2; ++i) {
        session.perform(Action::Wait);
    }
    CHECK(session.day() == 2);
}

void sessionIsDeterministicForASeed() {
    Session a(dragon(), 42);
    Session b(dragon(), 42);
    for (int i = 0; i < 40; ++i) {
        const Action action = static_cast<Action>(i % 6);
        const Outcome x = a.perform(action);
        const Outcome y = b.perform(action);
        CHECK(x.message == y.message);
        CHECK(x.event == y.event);
    }
    CHECK(a.pet().stats().happiness == b.pet().stats().happiness);
}

void lowDisciplineCanRefuse() {
    auto pet = dragon();
    StatChange wild;
    wild.discipline = -50;  // 0
    pet->apply(wild);
    Session session(std::move(pet), 7);
    int refused = 0;
    for (int i = 0; i < 200; ++i) {
        if (session.perform(Action::Play).refused) {
            ++refused;
        }
        StatChange reset;
        reset.discipline = -100;
        reset.hunger = -100;
        reset.fatigue = -100;
        reset.boredom = -100;
        session.pet().apply(reset);
    }
    // About half should be refused at zero discipline.
    CHECK(refused > 60);
    CHECK(refused < 140);

    Session obedient(dragon(), 7);
    for (int i = 0; i < 50; ++i) {
        CHECK(!obedient.perform(Action::Feed).refused);
    }
}

void journalKeepsTheLatestEntries() {
    Session session(dragon(), 3);
    for (int i = 0; i < 20; ++i) {
        session.perform(Action::Wait);
    }
    CHECK(session.log().size() == Session::logSize);
}

void saveRoundTrip() {
    auto pet = makePet("Mystic Cat", "Miso Soup");
    StatChange change;
    change.hunger = 21;
    change.discipline = -9;
    pet->apply(change);
    pet->restore(pet->name(), pet->stats(), 30, 4);

    std::stringstream file;
    writeSave(file, *pet);
    LoadResult loaded = readSave(file);
    CHECK(loaded.error.empty());
    CHECK(loaded.pet != nullptr);
    if (loaded.pet) {
        CHECK(loaded.pet->name() == "Miso Soup");
        CHECK(loaded.pet->species() == "Mystic Cat");
        CHECK(loaded.pet->stats().hunger == 56);
        CHECK(loaded.pet->stats().discipline == 41);
        CHECK(loaded.pet->ageHours() == 30);
        CHECK(loaded.pet->bond() == 4);
    }
}

void loadsVersionOneSaves() {
    std::stringstream file("VIRTUAL_PET_SAVE_V1\nDragon\n\"Ember\"\n42 57 23 89 100 61\n");
    LoadResult loaded = readSave(file);
    CHECK(loaded.pet != nullptr);
    if (loaded.pet) {
        CHECK(loaded.pet->stats().fatigue == 57);
        CHECK(loaded.pet->ageHours() == 0);
    }
}

void rejectsBadSaves() {
    const std::vector<std::string> bad = {
        "",
        "NOT_A_SAVE\nDragon\n\"Ember\"\n1 2 3 4 5 6\n",
        "VIRTUAL_PET_SAVE_V2\nGriffin\n\"G\"\n1 2 3 4 5 6\n0 0\n",
        "VIRTUAL_PET_SAVE_V2\nDragon\n\"Ember\"\n1 2 3 4 5\n",
        "VIRTUAL_PET_SAVE_V2\nDragon\n\"Ember\"\n1 2 3 4 5 101\n0 0\n",
        "VIRTUAL_PET_SAVE_V2\nDragon\n\"Ember\"\n1 2 3 4 5 6\n0 0 extra\n",
        "VIRTUAL_PET_SAVE_V2\nDragon\n\"\"\n1 2 3 4 5 6\n0 0\n",
    };
    for (const std::string& text : bad) {
        std::stringstream file(text);
        LoadResult loaded = readSave(file);
        CHECK(loaded.pet == nullptr);
        CHECK(!loaded.error.empty());
    }
}

void artHasConsistentWidthAndFaces() {
    for (const std::string species : {"Dragon", "Unicorn", "Mystic Cat"}) {
        for (const LifeStage stage : {LifeStage::Hatchling, LifeStage::Adult}) {
            const std::vector<std::string> art = creatureArt(species, stage, faceFor(Mood::Grumpy, false));
            CHECK(!art.empty());
            bool hasLeft = false;
            bool hasRight = false;
            for (const std::string& line : art) {
                CHECK(line.size() == art[0].size());
                CHECK(line.find('@') == std::string::npos);
                CHECK(line.find('&') == std::string::npos);
                hasLeft = hasLeft || line.find('>') != std::string::npos;
                hasRight = hasRight || line.find('<') != std::string::npos;
            }
            CHECK(hasLeft && hasRight);
            CHECK(art[0].size() <= 30);
        }
    }
}

}  // namespace

int main() {
    const std::vector<std::pair<const char*, std::function<void()>>> tests = {
        {"starts with default stats", startsWithDefaultStats},
        {"stats stay in range", statsStayInRange},
        {"feeding and overfeeding", feedingReducesHungerButOverfeedingHurts},
        {"resting at night restores more", restingAtNightRestoresMore},
        {"unmet needs hurt health and mood", unmetNeedsHurtHealthAndMood},
        {"cared-for hours build bond", caredForHoursBuildBond},
        {"mood reflects the worst need", moodReflectsTheWorstNeed},
        {"pets grow up", petsGrowUp},
        {"species have distinct abilities", speciesHaveDistinctAbilities},
        {"session tracks time of day", sessionTracksTimeOfDay},
        {"session is deterministic for a seed", sessionIsDeterministicForASeed},
        {"low discipline can refuse", lowDisciplineCanRefuse},
        {"journal keeps the latest entries", journalKeepsTheLatestEntries},
        {"save round trip", saveRoundTrip},
        {"loads version 1 saves", loadsVersionOneSaves},
        {"rejects bad saves", rejectsBadSaves},
        {"art has consistent width and faces", artHasConsistentWidthAndFaces},
    };
    for (const auto& [name, test] : tests) {
        const int before = failures;
        test();
        std::cout << (failures == before ? "PASS  " : "FAIL  ") << name << '\n';
    }
    std::cout << '\n' << tests.size() << " tests, " << failures << " failed checks\n";
    return failures == 0 ? 0 : 1;
}
