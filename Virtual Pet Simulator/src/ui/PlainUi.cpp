#include "ui/PlainUi.h"

#include "core/SaveFile.h"

#include <array>
#include <iomanip>
#include <istream>
#include <ostream>
#include <sstream>

namespace vpet {

namespace {

std::string bar(int value) {
    const int filled = (value + 5) / 10;
    return "[" + std::string(static_cast<std::size_t>(filled), '#') + std::string(static_cast<std::size_t>(10 - filled), '-') + "]";
}

}  // namespace

PlainUi::PlainUi(std::istream& input, std::ostream& output, std::uint32_t seed) : in_(input), out_(output), seed_(seed) {}

void PlainUi::open(std::unique_ptr<Pet> pet) {
    session_ = std::make_unique<Session>(std::move(pet), seed_);
}

int PlainUi::run() {
    out_ << "Virtual Pet Simulator\n";
    if (session_) {
        interact();
    }
    while (true) {
        out_ << "\n1. Create a pet\n2. Load a pet\n3. Exit\n";
        const int choice = readChoice("Select an option: ", 1, 3);
        if (choice == 3) {
            out_ << "Goodbye.\n";
            return 0;
        }
        if (choice == 1 ? createPet() : loadPet()) {
            interact();
        }
    }
}

bool PlainUi::createPet() {
    out_ << "\n1. Dragon\n2. Unicorn\n3. Mystic Cat\n4. Back\n";
    const int choice = readChoice("Choose a species: ", 1, 4);
    if (choice == 4) {
        return false;
    }
    const std::array<std::string, 3> species = {"Dragon", "Unicorn", "Mystic Cat"};
    const std::string name = readLine("Pet name: ");
    if (name.empty()) {
        return false;
    }
    open(makePet(species[static_cast<std::size_t>(choice - 1)], name));
    out_ << name << " is ready for adventure.\n";
    return true;
}

bool PlainUi::loadPet() {
    const std::string path = readLine("Save file: ");
    if (path.empty()) {
        return false;
    }
    LoadResult result = loadFromFile(path);
    if (!result.pet) {
        out_ << result.error << '\n';
        return false;
    }
    open(std::move(result.pet));
    out_ << "Pet loaded successfully.\n";
    return true;
}

void PlainUi::interact() {
    while (session_) {
        const auto actions = session_->pet().specialActions();
        out_ << "\n[" << session_->clockLabel() << "]\n"
             << "1. View status\n"
             << "2. Feed\n"
             << "3. Rest\n"
             << "4. Play\n"
             << "5. " << actions[0].name << '\n'
             << "6. " << actions[1].name << '\n'
             << "7. Advance one hour\n"
             << "8. Save\n"
             << "9. Return to main menu\n";
        const int choice = readChoice("Select an action: ", 1, 9);
        Action action = Action::Wait;
        switch (choice) {
            case 1: showStatus(); continue;
            case 2: action = Action::Feed; break;
            case 3: action = Action::Rest; break;
            case 4: action = Action::Play; break;
            case 5: action = Action::Special1; break;
            case 6: action = Action::Special2; break;
            case 7: action = Action::Wait; break;
            case 8: savePet(); continue;
            default: session_.reset(); continue;
        }
        const Outcome outcome = session_->perform(action);
        out_ << outcome.message << '\n';
        if (!outcome.event.empty()) {
            out_ << "* " << outcome.event << '\n';
        }
        if (outcome.stageChanged) {
            out_ << "* " << session_->pet().name() << " has grown into a " << stageName(session_->pet().stage()) << "!\n";
        }
    }
}

void PlainUi::showStatus() const {
    const Pet& pet = session_->pet();
    const Stats& s = pet.stats();
    auto row = [&](const char* label, int value) {
        out_ << std::left << std::setw(11) << label << std::right << std::setw(3) << value << "/100 " << bar(value) << '\n';
    };
    out_ << '\n' << pet.name() << " the " << pet.species() << '\n'
         << stageName(pet.stage()) << ", " << pet.ageHours() << "h old · mood " << moodName(pet.mood())
         << " · bond " << pet.bond() << "/100\n";
    row("Health:", s.health);
    row("Happiness:", s.happiness);
    row("Hunger:", s.hunger);
    row("Fatigue:", s.fatigue);
    row("Boredom:", s.boredom);
    row("Discipline:", s.discipline);
}

void PlainUi::savePet() {
    const std::string path = readLine("Save file: ");
    if (path.empty()) {
        return;
    }
    std::string error;
    if (saveToFile(path, session_->pet(), error)) {
        out_ << "Pet saved to " << path << ".\n";
    } else {
        out_ << error << '\n';
    }
}

int PlainUi::readChoice(const std::string& prompt, int minimum, int maximum) {
    while (true) {
        const std::string value = readLine(prompt);
        if (value.empty() && !in_) {
            return maximum;  // input closed: back out
        }
        std::istringstream parse(value);
        int choice = 0;
        std::string extra;
        if (parse >> choice && !(parse >> extra) && choice >= minimum && choice <= maximum) {
            return choice;
        }
        out_ << "Enter a number from " << minimum << " to " << maximum << ".\n";
    }
}

std::string PlainUi::readLine(const std::string& prompt) {
    while (true) {
        out_ << prompt << std::flush;
        std::string value;
        if (!std::getline(in_, value)) {
            return {};
        }
        if (!value.empty() && value.back() == '\r') {
            value.pop_back();
        }
        if (!value.empty()) {
            return value;
        }
        out_ << "A value is required.\n";
    }
}

}  // namespace vpet
