#include "Game.h"

#include "Dragon.h"
#include "MysticCat.h"
#include "Unicorn.h"

#include <array>
#include <fstream>
#include <iostream>
#include <sstream>
#include <utility>

namespace {
constexpr const char* saveHeader = "VIRTUAL_PET_SAVE_V1";
}

void Game::run() {
    std::cout << "Virtual Pet Simulator\n";

    while (true) {
        std::cout << "\n1. Create a pet\n2. Load a pet\n3. Exit\n";
        const int choice = readChoice("Select an option: ", 1, 3);
        if (choice == 3) {
            std::cout << "Goodbye.\n";
            return;
        }

        const bool ready = choice == 1 ? createPet() : loadPet();
        if (ready) {
            interact();
        }
    }
}

bool Game::createPet() {
    std::cout << "\n1. Dragon\n2. Unicorn\n3. Mystic Cat\n4. Back\n";
    const int choice = readChoice("Choose a species: ", 1, 4);
    if (choice == 4) {
        return false;
    }

    const std::array<std::string, 3> species = {"Dragon", "Unicorn", "Mystic Cat"};
    const std::string name = readRequiredLine("Pet name: ");
    if (name.empty()) {
        return false;
    }

    pet = makePet(species[static_cast<std::size_t>(choice - 1)], name);
    std::cout << name << " is ready for adventure.\n";
    return true;
}

bool Game::loadPet() {
    const std::string path = readRequiredLine("Save file: ");
    if (path.empty()) {
        return false;
    }

    std::ifstream input(path);
    if (!input) {
        std::cout << "Unable to open " << path << ".\n";
        return false;
    }

    std::string header;
    std::string species;
    if (!std::getline(input, header) || header != saveHeader || !std::getline(input, species)) {
        std::cout << "The file is not a supported virtual pet save.\n";
        return false;
    }

    std::unique_ptr<Pet> loaded = makePet(species, "Pet");
    std::string extra;
    if (!loaded || !loaded->loadState(input) || input >> extra) {
        std::cout << "The save data is incomplete or invalid.\n";
        return false;
    }

    pet = std::move(loaded);
    std::cout << "Pet loaded successfully.\n";
    return true;
}

void Game::interact() {
    while (pet) {
        const std::array<std::string, 2> actions = pet->specialActionNames();
        std::cout << "\n1. View status\n"
                  << "2. Feed\n"
                  << "3. Rest\n"
                  << "4. Play\n"
                  << "5. " << actions[0] << '\n'
                  << "6. " << actions[1] << '\n'
                  << "7. Advance one hour\n"
                  << "8. Save\n"
                  << "9. Return to main menu\n";

        const int choice = readChoice("Select an action: ", 1, 9);
        if (choice == 1) {
            pet->displayStatus(std::cout);
        } else if (choice == 2) {
            pet->feed();
            pet->advanceHour();
            std::cout << "Your pet enjoyed a balanced meal.\n";
        } else if (choice == 3) {
            pet->rest();
            pet->advanceHour();
            std::cout << "Your pet wakes up refreshed.\n";
        } else if (choice == 4) {
            pet->play();
            pet->advanceHour();
            std::cout << "Playtime lifted your pet's mood.\n";
        } else if (choice == 5 || choice == 6) {
            std::cout << pet->performSpecialAction(static_cast<std::size_t>(choice - 5)) << '\n';
            pet->advanceHour();
        } else if (choice == 7) {
            pet->advanceHour();
            std::cout << "One hour passes.\n";
        } else if (choice == 8) {
            savePet();
        } else {
            pet.reset();
        }
    }
}

void Game::savePet() const {
    const std::string path = readRequiredLine("Save file: ");
    if (path.empty()) {
        return;
    }

    std::ofstream output(path);
    if (!output) {
        std::cout << "Unable to write " << path << ".\n";
        return;
    }

    output << saveHeader << '\n' << pet->species() << '\n';
    pet->saveState(output);
    if (!output) {
        std::cout << "The save did not complete successfully.\n";
        return;
    }
    std::cout << "Pet saved to " << path << ".\n";
}

int Game::readChoice(const std::string& prompt, int minimum, int maximum) {
    while (true) {
        const std::string value = readRequiredLine(prompt);
        if (value.empty() && !std::cin) {
            return maximum;
        }

        std::istringstream input(value);
        int choice = 0;
        std::string extra;
        if (input >> choice && !(input >> extra) && choice >= minimum && choice <= maximum) {
            return choice;
        }
        std::cout << "Enter a number from " << minimum << " to " << maximum << ".\n";
    }
}

std::string Game::readRequiredLine(const std::string& prompt) {
    while (true) {
        std::cout << prompt;
        std::string value;
        if (!std::getline(std::cin, value)) {
            return {};
        }
        if (!value.empty()) {
            return value;
        }
        std::cout << "A value is required.\n";
    }
}

std::unique_ptr<Pet> Game::makePet(const std::string& species, const std::string& name) {
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
