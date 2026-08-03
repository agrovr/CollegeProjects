#include <algorithm>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

struct Employee {
    std::string name;
    std::vector<std::string> keys;
};

class KeyRegistry {
public:
    bool load(const std::string& path, std::string& error) {
        std::ifstream input(path);
        if (!input) {
            error = "Unable to open " + path + ".";
            return false;
        }

        std::string line;
        std::size_t employeeCount = 0;
        if (!std::getline(input, line) || !parseCount(line, employeeCount) || employeeCount > maximumEmployees) {
            error = "The first line must contain a valid employee count.";
            return false;
        }

        std::vector<Employee> loaded;
        loaded.reserve(employeeCount);

        for (std::size_t index = 0; index < employeeCount; ++index) {
            Employee employee;
            if (!std::getline(input, employee.name) || employee.name.empty()) {
                error = "Employee " + std::to_string(index + 1) + " has no valid name.";
                return false;
            }
            if (std::any_of(loaded.begin(), loaded.end(), [&](const Employee& existing) {
                    return existing.name == employee.name;
                })) {
                error = "Duplicate employee name: " + employee.name + ".";
                return false;
            }

            if (!std::getline(input, line)) {
                error = "Missing key data for " + employee.name + ".";
                return false;
            }

            std::istringstream keyLine(line);
            std::size_t keyCount = 0;
            if (!(keyLine >> keyCount) || keyCount > maximumKeys) {
                error = "Invalid key count for " + employee.name + ".";
                return false;
            }

            for (std::size_t keyIndex = 0; keyIndex < keyCount; ++keyIndex) {
                std::string key;
                if (!(keyLine >> key)) {
                    error = "Missing key identifier for " + employee.name + ".";
                    return false;
                }
                if (std::find(employee.keys.begin(), employee.keys.end(), key) != employee.keys.end()) {
                    error = "Duplicate key " + key + " for " + employee.name + ".";
                    return false;
                }
                employee.keys.push_back(key);
            }

            std::string extra;
            if (keyLine >> extra) {
                error = "Unexpected key data for " + employee.name + ".";
                return false;
            }

            loaded.push_back(std::move(employee));
        }

        employees = std::move(loaded);
        return true;
    }

    bool save(const std::string& path, std::string& error) const {
        std::ofstream output(path);
        if (!output) {
            error = "Unable to write " + path + ".";
            return false;
        }

        output << employees.size() << '\n';
        for (const Employee& employee : employees) {
            output << employee.name << '\n' << employee.keys.size();
            for (const std::string& key : employee.keys) {
                output << ' ' << key;
            }
            output << '\n';
        }

        if (!output) {
            error = "Writing " + path + " did not complete successfully.";
            return false;
        }
        return true;
    }

    const std::vector<Employee>& allEmployees() const {
        return employees;
    }

    const Employee* findEmployee(const std::string& name) const {
        const auto match = std::find_if(employees.begin(), employees.end(), [&](const Employee& employee) {
            return employee.name == name;
        });
        return match == employees.end() ? nullptr : &*match;
    }

    std::vector<std::string> findKeyHolders(const std::string& key) const {
        std::vector<std::string> holders;
        for (const Employee& employee : employees) {
            if (std::find(employee.keys.begin(), employee.keys.end(), key) != employee.keys.end()) {
                holders.push_back(employee.name);
            }
        }
        return holders;
    }

    bool issueKey(const std::string& name, const std::string& key, std::string& error) {
        Employee* employee = findMutableEmployee(name);
        if (employee == nullptr) {
            error = "Employee not found.";
            return false;
        }
        if (employee->keys.size() >= maximumKeys) {
            error = "This employee already holds the maximum of five keys.";
            return false;
        }
        if (!isValidKey(key)) {
            error = "Key identifiers cannot contain whitespace.";
            return false;
        }
        if (std::find(employee->keys.begin(), employee->keys.end(), key) != employee->keys.end()) {
            error = "This employee already holds that key.";
            return false;
        }
        employee->keys.push_back(key);
        return true;
    }

    bool returnKey(const std::string& name, const std::string& key, std::string& error) {
        Employee* employee = findMutableEmployee(name);
        if (employee == nullptr) {
            error = "Employee not found.";
            return false;
        }
        const auto match = std::find(employee->keys.begin(), employee->keys.end(), key);
        if (match == employee->keys.end()) {
            error = "This employee does not hold that key.";
            return false;
        }
        employee->keys.erase(match);
        return true;
    }

private:
    static constexpr std::size_t maximumKeys = 5;
    static constexpr std::size_t maximumEmployees = 10000;
    std::vector<Employee> employees;

    static bool parseCount(const std::string& text, std::size_t& value) {
        std::istringstream input(text);
        std::string extra;
        return static_cast<bool>(input >> value) && !(input >> extra);
    }

    static bool isValidKey(const std::string& key) {
        std::istringstream input(key);
        std::string token;
        std::string extra;
        return static_cast<bool>(input >> token) && !(input >> extra);
    }

    Employee* findMutableEmployee(const std::string& name) {
        const auto match = std::find_if(employees.begin(), employees.end(), [&](const Employee& employee) {
            return employee.name == name;
        });
        return match == employees.end() ? nullptr : &*match;
    }
};

std::string readRequiredLine(const std::string& prompt) {
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

int readMenuChoice() {
    while (true) {
        const std::string value = readRequiredLine("Select an option: ");
        if (value.empty() && !std::cin) {
            return 7;
        }
        std::istringstream input(value);
        int choice = 0;
        std::string extra;
        if (input >> choice && !(input >> extra) && choice >= 1 && choice <= 7) {
            return choice;
        }
        std::cout << "Enter a number from 1 to 7.\n";
    }
}

void printKeys(const Employee& employee) {
    std::cout << employee.name << ": ";
    if (employee.keys.empty()) {
        std::cout << "No keys";
    } else {
        for (std::size_t index = 0; index < employee.keys.size(); ++index) {
            if (index > 0) {
                std::cout << ", ";
            }
            std::cout << employee.keys[index];
        }
    }
    std::cout << '\n';
}

int main(int argc, char* argv[]) {
    const std::string inputPath = argc > 1 ? argv[1] : readRequiredLine("Registry file: ");
    if (inputPath.empty()) {
        std::cerr << "No registry file was provided.\n";
        return 1;
    }

    KeyRegistry registry;
    std::string error;
    if (!registry.load(inputPath, error)) {
        std::cerr << error << '\n';
        return 1;
    }

    while (true) {
        std::cout << "\nKey Registry\n"
                  << "1. List employees and keys\n"
                  << "2. Find an employee's keys\n"
                  << "3. Find holders of a key\n"
                  << "4. Issue a key\n"
                  << "5. Return a key\n"
                  << "6. Save registry\n"
                  << "7. Exit\n";

        const int choice = readMenuChoice();
        if (choice == 1) {
            for (const Employee& employee : registry.allEmployees()) {
                printKeys(employee);
            }
        } else if (choice == 2) {
            const Employee* employee = registry.findEmployee(readRequiredLine("Employee name: "));
            if (employee == nullptr) {
                std::cout << "Employee not found.\n";
            } else {
                printKeys(*employee);
            }
        } else if (choice == 3) {
            const std::string key = readRequiredLine("Key identifier: ");
            const std::vector<std::string> holders = registry.findKeyHolders(key);
            if (holders.empty()) {
                std::cout << "No employee holds " << key << ".\n";
            } else {
                std::cout << "Holders of " << key << ": ";
                for (std::size_t index = 0; index < holders.size(); ++index) {
                    if (index > 0) {
                        std::cout << ", ";
                    }
                    std::cout << holders[index];
                }
                std::cout << '\n';
            }
        } else if (choice == 4) {
            error.clear();
            const std::string name = readRequiredLine("Employee name: ");
            const std::string key = readRequiredLine("Key identifier: ");
            std::cout << (registry.issueKey(name, key, error) ? "Key issued.\n" : error + "\n");
        } else if (choice == 5) {
            error.clear();
            const std::string name = readRequiredLine("Employee name: ");
            const std::string key = readRequiredLine("Key identifier: ");
            std::cout << (registry.returnKey(name, key, error) ? "Key returned.\n" : error + "\n");
        } else if (choice == 6) {
            error.clear();
            const std::string outputPath = readRequiredLine("Output file: ");
            std::cout << (registry.save(outputPath, error) ? "Registry saved to " + outputPath + ".\n" : error + "\n");
        } else {
            std::cout << "Goodbye.\n";
            return 0;
        }
    }
}
