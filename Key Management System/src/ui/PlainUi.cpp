#include "ui/PlainUi.h"

#include <istream>
#include <ostream>
#include <sstream>

namespace kms {

PlainUi::PlainUi(std::istream& input, std::ostream& output, Registry& registry, Format format)
    : in_(input), out_(output), registry_(registry), format_(format) {}

int PlainUi::run() {
    while (true) {
        out_ << "\nKey Registry\n"
             << "1. List employees and keys\n"
             << "2. Find an employee's keys\n"
             << "3. Find holders of a key\n"
             << "4. Issue a key\n"
             << "5. Return a key\n"
             << "6. Save registry\n"
             << "7. Exit\n";
        const int choice = readChoice();
        std::string error;
        if (choice == 1) {
            for (const Employee& employee : registry_.employees()) {
                printKeys(employee);
            }
        } else if (choice == 2) {
            const Employee* employee = registry_.findEmployee(readLine("Employee name: "));
            if (employee) {
                printKeys(*employee);
            } else {
                out_ << "Employee not found.\n";
            }
        } else if (choice == 3) {
            const std::string key = readLine("Key identifier: ");
            const std::vector<std::string> holders = registry_.holders(key);
            if (holders.empty()) {
                out_ << "No employee holds " << key << ".\n";
            } else {
                out_ << "Holders of " << key << ": ";
                for (std::size_t i = 0; i < holders.size(); ++i) {
                    out_ << (i ? ", " : "") << holders[i];
                }
                out_ << '\n';
            }
        } else if (choice == 4) {
            const std::string name = readLine("Employee name: ");
            const std::string key = readLine("Key identifier: ");
            out_ << (registry_.issue(name, key, error) ? "Key issued." : error) << '\n';
        } else if (choice == 5) {
            const std::string name = readLine("Employee name: ");
            const std::string key = readLine("Key identifier: ");
            out_ << (registry_.giveBack(name, key, error) ? "Key returned." : error) << '\n';
        } else if (choice == 6) {
            const std::string path = readLine("Output file: ");
            if (saveRegistry(path, registry_, format_, error)) {
                registry_.markSaved();
                out_ << "Registry saved to " << path << ".\n";
            } else {
                out_ << error << '\n';
            }
        } else {
            out_ << "Goodbye.\n";
            return 0;
        }
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

int PlainUi::readChoice() {
    while (true) {
        const std::string value = readLine("Select an option: ");
        if (value.empty() && !in_) {
            return 7;
        }
        std::istringstream input(value);
        int choice = 0;
        std::string extra;
        if (input >> choice && !(input >> extra) && choice >= 1 && choice <= 7) {
            return choice;
        }
        out_ << "Enter a number from 1 to 7.\n";
    }
}

void PlainUi::printKeys(const Employee& employee) {
    out_ << employee.name << ": ";
    if (employee.keys.empty()) {
        out_ << "No keys";
    }
    for (std::size_t i = 0; i < employee.keys.size(); ++i) {
        out_ << (i ? ", " : "") << employee.keys[i];
    }
    out_ << '\n';
}

}  // namespace kms
