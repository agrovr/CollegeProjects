#include "core/RegistryFile.h"

#include <algorithm>
#include <cstdio>
#include <fstream>
#include <istream>
#include <ostream>
#include <sstream>

namespace kms {

namespace {

constexpr const char* v2Header = "KEY_REGISTRY_V2";

std::string trim(const std::string& text) {
    const auto start = text.find_first_not_of(" \t\r");
    if (start == std::string::npos) {
        return "";
    }
    const auto end = text.find_last_not_of(" \t\r");
    return text.substr(start, end - start + 1);
}

std::vector<std::string> splitFields(const std::string& line) {
    std::vector<std::string> fields;
    std::string field;
    std::istringstream stream(line);
    while (std::getline(stream, field, '|')) {
        fields.push_back(trim(field));
    }
    if (!line.empty() && line.back() == '|') {
        fields.push_back("");
    }
    return fields;
}

bool parseCount(const std::string& text, std::size_t& value) {
    std::istringstream input(text);
    std::string extra;
    return static_cast<bool>(input >> value) && !(input >> extra);
}

ReadResult fail(const std::string& message, std::size_t line = 0) {
    ReadResult result;
    result.error = line ? "Line " + std::to_string(line) + ": " + message : message;
    return result;
}

ReadResult readClassic(std::istream& input, const std::string& firstLine, Registry& registry) {
    std::size_t employeeCount = 0;
    if (!parseCount(trim(firstLine), employeeCount) || employeeCount > Registry::maxEmployees) {
        return fail("The first line must contain a valid employee count.");
    }
    std::vector<Employee> employees;
    std::string line;
    std::size_t lineNumber = 1;
    for (std::size_t index = 0; index < employeeCount; ++index) {
        Employee employee;
        ++lineNumber;
        if (!std::getline(input, employee.name) || trim(employee.name).empty()) {
            return fail("Employee " + std::to_string(index + 1) + " has no valid name.", lineNumber);
        }
        employee.name = trim(employee.name);
        if (std::any_of(employees.begin(), employees.end(), [&](const Employee& e) { return e.name == employee.name; })) {
            return fail("Duplicate employee name: " + employee.name + ".", lineNumber);
        }
        ++lineNumber;
        if (!std::getline(input, line)) {
            return fail("Missing key data for " + employee.name + ".", lineNumber);
        }
        std::istringstream keys(line);
        std::size_t keyCount = 0;
        if (!(keys >> keyCount) || keyCount > Registry::maxKeysPerEmployee) {
            return fail("Invalid key count for " + employee.name + ".", lineNumber);
        }
        for (std::size_t k = 0; k < keyCount; ++k) {
            std::string id;
            if (!(keys >> id)) {
                return fail("Missing key identifier for " + employee.name + ".", lineNumber);
            }
            if (std::find(employee.keys.begin(), employee.keys.end(), id) != employee.keys.end()) {
                return fail("Duplicate key " + id + " for " + employee.name + ".", lineNumber);
            }
            employee.keys.push_back(id);
        }
        std::string extra;
        if (keys >> extra) {
            return fail("Unexpected key data for " + employee.name + ".", lineNumber);
        }
        employees.push_back(std::move(employee));
    }
    registry.restore({}, std::move(employees), {});
    ReadResult result;
    result.ok = true;
    result.format = Format::Classic;
    return result;
}

ReadResult readV2(std::istream& input, Registry& registry) {
    enum class Section { None, Keys, Employees, History } section = Section::None;
    std::vector<Key> keys;
    std::vector<Employee> employees;
    std::vector<Event> history;
    std::string line;
    std::size_t lineNumber = 1;
    std::string error;
    while (std::getline(input, line)) {
        ++lineNumber;
        const std::string text = trim(line);
        if (text.empty() || text[0] == '#') {
            continue;
        }
        if (text == "[keys]") {
            section = Section::Keys;
            continue;
        }
        if (text == "[employees]") {
            section = Section::Employees;
            continue;
        }
        if (text == "[history]") {
            section = Section::History;
            continue;
        }
        const std::vector<std::string> fields = splitFields(text);
        switch (section) {
            case Section::None:
                return fail("Expected a [keys], [employees] or [history] section.", lineNumber);
            case Section::Keys: {
                if (fields.size() > 2 || !Registry::validKey(fields[0], error)
                    || (fields.size() == 2 && !Registry::validLabel(fields[1], error))) {
                    return fail(fields.size() > 2 ? "A key line has too many fields." : error, lineNumber);
                }
                if (std::any_of(keys.begin(), keys.end(), [&](const Key& k) { return k.id == fields[0]; })) {
                    return fail("Key " + fields[0] + " is listed twice.", lineNumber);
                }
                keys.push_back(Key{fields[0], fields.size() == 2 ? fields[1] : ""});
                break;
            }
            case Section::Employees: {
                if (fields.size() > 2 || !Registry::validName(fields[0], error)) {
                    return fail(fields.size() > 2 ? "An employee line has too many fields." : error, lineNumber);
                }
                if (std::any_of(employees.begin(), employees.end(), [&](const Employee& e) { return e.name == fields[0]; })) {
                    return fail("Duplicate employee name: " + fields[0] + ".", lineNumber);
                }
                Employee employee{fields[0], {}};
                std::istringstream ids(fields.size() == 2 ? fields[1] : "");
                std::string id;
                while (ids >> id) {
                    if (!Registry::validKey(id, error)) {
                        return fail(error, lineNumber);
                    }
                    if (std::find(employee.keys.begin(), employee.keys.end(), id) != employee.keys.end()) {
                        return fail("Duplicate key " + id + " for " + employee.name + ".", lineNumber);
                    }
                    employee.keys.push_back(id);
                }
                if (employee.keys.size() > Registry::maxKeysPerEmployee) {
                    return fail(employee.name + " holds more than five keys.", lineNumber);
                }
                if (employees.size() >= Registry::maxEmployees) {
                    return fail("Too many employees.", lineNumber);
                }
                employees.push_back(std::move(employee));
                break;
            }
            case Section::History: {
                EventKind kind;
                if (fields.size() != 4 || !parseEventName(fields[1], kind)) {
                    return fail("A history line needs: time | event | employee | key.", lineNumber);
                }
                history.push_back(Event{fields[0], kind, fields[2], fields[3]});
                break;
            }
        }
    }
    if (history.size() > Registry::historyLimit) {
        history.erase(history.begin(), history.begin() + static_cast<std::ptrdiff_t>(history.size() - Registry::historyLimit));
    }
    registry.restore(std::move(keys), std::move(employees), std::move(history));
    ReadResult result;
    result.ok = true;
    result.format = Format::V2;
    return result;
}

std::string csvField(const std::string& text) {
    if (text.find_first_of(",\"\n") == std::string::npos) {
        return text;
    }
    std::string quoted = "\"";
    for (char c : text) {
        quoted += c == '"' ? std::string("\"\"") : std::string(1, c);
    }
    return quoted + "\"";
}

}  // namespace

ReadResult readRegistry(std::istream& input, Registry& registry) {
    std::string first;
    if (!std::getline(input, first)) {
        return fail("The file is empty.");
    }
    if (trim(first) == v2Header) {
        return readV2(input, registry);
    }
    return readClassic(input, first, registry);
}

bool writeRegistry(std::ostream& output, const Registry& registry, Format format, std::string& error) {
    if (format == Format::Classic) {
        output << registry.employees().size() << '\n';
        for (const Employee& e : registry.employees()) {
            output << e.name << '\n' << e.keys.size();
            for (const std::string& id : e.keys) {
                output << ' ' << id;
            }
            output << '\n';
        }
        return static_cast<bool>(output);
    }

    for (const Employee& e : registry.employees()) {
        if (e.name.find('|') != std::string::npos) {
            error = "The name \"" + e.name + "\" contains |, which version 2 files can't store. Save in the classic format.";
            return false;
        }
    }
    output << v2Header << "\n\n[keys]\n";
    for (const Key& k : registry.keys()) {
        output << k.id;
        if (!k.label.empty()) {
            output << " | " << k.label;
        }
        output << '\n';
    }
    output << "\n[employees]\n";
    for (const Employee& e : registry.employees()) {
        output << e.name << " |";
        for (const std::string& id : e.keys) {
            output << ' ' << id;
        }
        output << '\n';
    }
    output << "\n[history]\n";
    for (const Event& event : registry.history()) {
        output << event.when << " | " << eventName(event.kind) << " | " << event.employee << " | " << event.key << '\n';
    }
    return static_cast<bool>(output);
}

ReadResult loadRegistry(const std::string& path, Registry& registry) {
    std::ifstream input(path);
    if (!input) {
        return fail("Unable to open " + path + ".");
    }
    return readRegistry(input, registry);
}

bool saveRegistry(const std::string& path, const Registry& registry, Format format, std::string& error) {
    // Write to a temporary file first, so a failed save never leaves a half-written registry.
    const std::string temporary = path + ".tmp";
    {
        std::ofstream output(temporary);
        if (!output) {
            error = "Unable to write " + path + ".";
            return false;
        }
        if (!writeRegistry(output, registry, format, error)) {
            output.close();
            std::remove(temporary.c_str());
            if (error.empty()) {
                error = "Writing " + path + " did not complete successfully.";
            }
            return false;
        }
        output.flush();
        if (!output) {
            output.close();
            std::remove(temporary.c_str());
            error = "Writing " + path + " did not complete successfully.";
            return false;
        }
    }
    std::remove(path.c_str());
    if (std::rename(temporary.c_str(), path.c_str()) != 0) {
        std::remove(temporary.c_str());
        error = "Unable to replace " + path + ".";
        return false;
    }
    return true;
}

std::string toCsv(const Registry& registry) {
    std::string csv = "key,label,holder\n";
    for (const Key& k : registry.keys()) {
        const std::vector<std::string> holders = registry.holders(k.id);
        if (holders.empty()) {
            csv += csvField(k.id) + "," + csvField(k.label) + ",\n";
        }
        for (const std::string& holder : holders) {
            csv += csvField(k.id) + "," + csvField(k.label) + "," + csvField(holder) + "\n";
        }
    }
    return csv;
}

}  // namespace kms
