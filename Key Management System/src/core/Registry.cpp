#include "core/Registry.h"

#include <algorithm>
#include <cctype>
#include <ctime>
#include <utility>

namespace kms {

Registry::Registry(Clock clock) : clock_(clock ? std::move(clock) : Clock(systemClock)) {}

const Employee* Registry::findEmployee(const std::string& name) const {
    const auto match = std::find_if(employees_.begin(), employees_.end(),
                                    [&](const Employee& e) { return e.name == name; });
    return match == employees_.end() ? nullptr : &*match;
}

const Key* Registry::findKey(const std::string& id) const {
    const auto match = std::find_if(keys_.begin(), keys_.end(), [&](const Key& k) { return k.id == id; });
    return match == keys_.end() ? nullptr : &*match;
}

Employee* Registry::employee(const std::string& name) {
    return const_cast<Employee*>(static_cast<const Registry*>(this)->findEmployee(name));
}

Key* Registry::key(const std::string& id) {
    return const_cast<Key*>(static_cast<const Registry*>(this)->findKey(id));
}

std::vector<std::string> Registry::holders(const std::string& key) const {
    std::vector<std::string> names;
    for (const Employee& e : employees_) {
        if (std::find(e.keys.begin(), e.keys.end(), key) != e.keys.end()) {
            names.push_back(e.name);
        }
    }
    return names;
}

std::size_t Registry::issuedCount() const {
    std::size_t count = 0;
    for (const Employee& e : employees_) {
        count += e.keys.size();
    }
    return count;
}

std::size_t Registry::onHookCount() const {
    return static_cast<std::size_t>(std::count_if(keys_.begin(), keys_.end(),
                                                  [&](const Key& k) { return holders(k.id).empty(); }));
}

bool Registry::issue(const std::string& name, const std::string& id, std::string& error) {
    Employee* target = employee(name);
    if (!target) {
        error = "Employee not found.";
        return false;
    }
    if (target->keys.size() >= maxKeysPerEmployee) {
        error = "This employee already holds the maximum of five keys.";
        return false;
    }
    if (!validKey(id, error)) {
        return false;
    }
    if (std::find(target->keys.begin(), target->keys.end(), id) != target->keys.end()) {
        error = "This employee already holds that key.";
        return false;
    }
    if (!findKey(id)) {
        keys_.push_back(Key{id, ""});  // issuing a new identifier catalogues it
    }
    target->keys.push_back(id);
    record(EventKind::Issue, name, id);
    return true;
}

bool Registry::giveBack(const std::string& name, const std::string& id, std::string& error) {
    Employee* target = employee(name);
    if (!target) {
        error = "Employee not found.";
        return false;
    }
    const auto match = std::find(target->keys.begin(), target->keys.end(), id);
    if (match == target->keys.end()) {
        error = "This employee does not hold that key.";
        return false;
    }
    target->keys.erase(match);
    record(EventKind::Return, name, id);
    return true;
}

bool Registry::addEmployee(const std::string& name, std::string& error) {
    if (!validName(name, error)) {
        return false;
    }
    if (findEmployee(name)) {
        error = "There is already an employee called " + name + ".";
        return false;
    }
    if (employees_.size() >= maxEmployees) {
        error = "The registry is full.";
        return false;
    }
    employees_.push_back(Employee{name, {}});
    record(EventKind::AddEmployee, name, "");
    return true;
}

bool Registry::removeEmployee(const std::string& name, std::string& error) {
    const Employee* target = findEmployee(name);
    if (!target) {
        error = "Employee not found.";
        return false;
    }
    if (!target->keys.empty()) {
        error = name + " still holds keys. Return them first.";
        return false;
    }
    employees_.erase(std::remove_if(employees_.begin(), employees_.end(),
                                    [&](const Employee& e) { return e.name == name; }),
                     employees_.end());
    record(EventKind::RemoveEmployee, name, "");
    return true;
}

bool Registry::addKey(const std::string& id, const std::string& label, std::string& error) {
    if (!validKey(id, error) || !validLabel(label, error)) {
        return false;
    }
    if (findKey(id)) {
        error = "Key " + id + " is already in the cabinet.";
        return false;
    }
    keys_.push_back(Key{id, label});
    record(EventKind::AddKey, "", id);
    return true;
}

bool Registry::setLabel(const std::string& id, const std::string& label, std::string& error) {
    Key* target = key(id);
    if (!target) {
        error = "Key not found.";
        return false;
    }
    if (!validLabel(label, error)) {
        return false;
    }
    target->label = label;
    record(EventKind::LabelKey, "", id);
    return true;
}

void Registry::restore(std::vector<Key> newKeys, std::vector<Employee> newEmployees, std::vector<Event> newHistory) {
    keys_ = std::move(newKeys);
    employees_ = std::move(newEmployees);
    history_ = std::move(newHistory);
    // Every held key belongs in the catalogue, even if the file didn't list it.
    for (const Employee& e : employees_) {
        for (const std::string& id : e.keys) {
            if (!findKey(id)) {
                keys_.push_back(Key{id, ""});
            }
        }
    }
    changed_ = false;
}

void Registry::record(EventKind kind, const std::string& employee, const std::string& key) {
    history_.push_back(Event{clock_(), kind, employee, key});
    if (history_.size() > historyLimit) {
        history_.erase(history_.begin(), history_.begin() + static_cast<std::ptrdiff_t>(history_.size() - historyLimit));
    }
    changed_ = true;
}

bool Registry::validName(const std::string& name, std::string& error) {
    if (name.empty() || std::isspace(static_cast<unsigned char>(name.front()))
        || std::isspace(static_cast<unsigned char>(name.back()))) {
        error = "Names can't be empty or start or end with a space.";
        return false;
    }
    if (name.size() > maxNameLength) {
        error = "Names can be at most 40 characters.";
        return false;
    }
    if (name.find('|') != std::string::npos || name.find('\t') != std::string::npos) {
        error = "Names can't contain | or tabs.";
        return false;
    }
    return true;
}

bool Registry::validKey(const std::string& id, std::string& error) {
    if (id.empty() || std::any_of(id.begin(), id.end(), [](unsigned char c) { return std::isspace(c) != 0; })) {
        error = "Key identifiers cannot contain whitespace.";
        return false;
    }
    if (id.size() > maxKeyLength) {
        error = "Key identifiers can be at most 16 characters.";
        return false;
    }
    if (id.find('|') != std::string::npos) {
        error = "Key identifiers can't contain |.";
        return false;
    }
    return true;
}

bool Registry::validLabel(const std::string& label, std::string& error) {
    if (label.size() > maxLabelLength) {
        error = "Labels can be at most 32 characters.";
        return false;
    }
    if (label.find('|') != std::string::npos) {
        error = "Labels can't contain |.";
        return false;
    }
    return true;
}

std::string Registry::systemClock() {
    const std::time_t now = std::time(nullptr);
    std::tm local{};
#ifdef _WIN32
    localtime_s(&local, &now);
#else
    localtime_r(&now, &local);
#endif
    char buffer[20];
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M", &local);
    return buffer;
}

const char* eventName(EventKind kind) {
    switch (kind) {
        case EventKind::Issue: return "issue";
        case EventKind::Return: return "return";
        case EventKind::AddEmployee: return "add-employee";
        case EventKind::RemoveEmployee: return "remove-employee";
        case EventKind::AddKey: return "add-key";
        case EventKind::LabelKey: return "label-key";
    }
    return "issue";
}

bool parseEventName(const std::string& text, EventKind& kind) {
    const EventKind all[] = {EventKind::Issue, EventKind::Return, EventKind::AddEmployee,
                             EventKind::RemoveEmployee, EventKind::AddKey, EventKind::LabelKey};
    for (const EventKind candidate : all) {
        if (text == eventName(candidate)) {
            kind = candidate;
            return true;
        }
    }
    return false;
}

}  // namespace kms
