#ifndef GAME_H
#define GAME_H

#include "Pet.h"

#include <memory>
#include <string>

class Game {
public:
    void run();

private:
    bool createPet();
    bool loadPet();
    void interact();
    void savePet() const;
    static int readChoice(const std::string& prompt, int minimum, int maximum);
    static std::string readRequiredLine(const std::string& prompt);
    static std::unique_ptr<Pet> makePet(const std::string& species, const std::string& name);

    std::unique_ptr<Pet> pet;
};

#endif
