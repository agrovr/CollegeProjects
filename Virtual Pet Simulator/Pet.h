#ifndef PET_H
#define PET_H

#include <array>
#include <cstddef>
#include <iosfwd>
#include <string>

class Pet {
public:
    explicit Pet(std::string name);
    virtual ~Pet() = default;

    virtual std::string species() const = 0;
    virtual std::array<std::string, 2> specialActionNames() const = 0;
    virtual std::string performSpecialAction(std::size_t index) = 0;

    void feed();
    void rest();
    void play();
    void advanceHour();
    void displayStatus(std::ostream& output) const;

    void saveState(std::ostream& output) const;
    bool loadState(std::istream& input);

protected:
    void adjustHunger(int amount);
    void adjustFatigue(int amount);
    void adjustBoredom(int amount);
    void adjustHappiness(int amount);
    void adjustHealth(int amount);
    void adjustDiscipline(int amount);
    const std::string& petName() const;

private:
    static int clampStat(int value);

    std::string name;
    int hunger = 35;
    int fatigue = 25;
    int boredom = 30;
    int happiness = 70;
    int health = 100;
    int discipline = 50;
};

#endif
