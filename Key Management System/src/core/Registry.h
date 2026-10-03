#ifndef KMS_CORE_REGISTRY_H
#define KMS_CORE_REGISTRY_H

#include <cstddef>
#include <functional>
#include <string>
#include <vector>

namespace kms {

struct Key {
    std::string id;     // e.g. AHC102
    std::string label;  // what it opens, e.g. "Server room" (may be empty)
};

struct Employee {
    std::string name;
    std::vector<std::string> keys;  // in the order they were issued
};

enum class EventKind { Issue, Return, AddEmployee, RemoveEmployee, AddKey, LabelKey };

struct Event {
    std::string when;  // "YYYY-MM-DD HH:MM"
    EventKind kind;
    std::string employee;
    std::string key;
};

// Who holds which keys. Every change is validated, recorded in the history and marks the
// registry as changed until it is saved.
class Registry {
public:
    static constexpr std::size_t maxKeysPerEmployee = 5;
    static constexpr std::size_t maxEmployees = 10000;
    static constexpr std::size_t maxNameLength = 40;
    static constexpr std::size_t maxKeyLength = 16;
    static constexpr std::size_t maxLabelLength = 32;
    static constexpr std::size_t historyLimit = 500;

    using Clock = std::function<std::string()>;

    explicit Registry(Clock clock = {});

    // Queries.
    const std::vector<Employee>& employees() const { return employees_; }
    const std::vector<Key>& keys() const { return keys_; }
    const std::vector<Event>& history() const { return history_; }
    const Employee* findEmployee(const std::string& name) const;
    const Key* findKey(const std::string& id) const;
    std::vector<std::string> holders(const std::string& key) const;
    std::size_t issuedCount() const;   // keys currently out, counting each copy
    std::size_t onHookCount() const;   // catalogued keys nobody holds
    bool changed() const { return changed_; }

    // Commands. Each returns false and sets `error` when the change is not allowed.
    bool issue(const std::string& employee, const std::string& key, std::string& error);
    bool giveBack(const std::string& employee, const std::string& key, std::string& error);
    bool addEmployee(const std::string& name, std::string& error);
    bool removeEmployee(const std::string& name, std::string& error);
    bool addKey(const std::string& id, const std::string& label, std::string& error);
    bool setLabel(const std::string& id, const std::string& label, std::string& error);

    // Used by the file reader, which validates as it goes and records no history.
    void restore(std::vector<Key> newKeys, std::vector<Employee> newEmployees, std::vector<Event> newHistory);
    void markSaved() { changed_ = false; }

    static bool validName(const std::string& name, std::string& error);
    static bool validKey(const std::string& id, std::string& error);
    static bool validLabel(const std::string& label, std::string& error);
    static std::string systemClock();

private:
    Employee* employee(const std::string& name);
    Key* key(const std::string& id);
    void record(EventKind kind, const std::string& employee, const std::string& key);

    Clock clock_;
    std::vector<Key> keys_;
    std::vector<Employee> employees_;
    std::vector<Event> history_;
    bool changed_ = false;
};

const char* eventName(EventKind kind);
bool parseEventName(const std::string& text, EventKind& kind);

}  // namespace kms

#endif
