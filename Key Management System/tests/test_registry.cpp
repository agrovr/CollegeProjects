// Unit tests for the registry and its file formats.

#include "core/Registry.h"
#include "core/RegistryFile.h"

#include <functional>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace kms;

namespace {

int failures = 0;

void fail(const char* file, int line, const char* condition) {
    ++failures;
    std::cerr << "  FAILED " << file << ":" << line << "  " << condition << "\n";
}

#define CHECK(condition) ((condition) ? (void)0 : fail(__FILE__, __LINE__, #condition))

Registry::Clock fixedClock() {
    return [] { return std::string("2026-10-02 09:30"); };
}

const char* const sample = "2\nYa Hoo\n3 AHC102 AHC200 AHC111\nMichael Lee\n2 AHC303 AHC200\n";

Registry loaded(const std::string& text = sample) {
    Registry registry(fixedClock());
    std::istringstream input(text);
    const ReadResult result = readRegistry(input, registry);
    CHECK(result.ok);
    return registry;
}

void readsTheClassicFormat() {
    Registry registry(fixedClock());
    std::istringstream input(sample);
    const ReadResult result = readRegistry(input, registry);
    CHECK(result.ok);
    CHECK(result.format == Format::Classic);
    CHECK(registry.employees().size() == 2);
    CHECK(registry.keys().size() == 4);  // AHC102, AHC200, AHC111, AHC303
    CHECK(registry.issuedCount() == 5);
    CHECK(registry.onHookCount() == 0);
    CHECK(!registry.changed());
}

void findsHolders() {
    const Registry registry = loaded();
    const auto holders = registry.holders("AHC200");
    CHECK(holders.size() == 2);
    CHECK(holders[0] == "Ya Hoo");
    CHECK(registry.holders("NOPE").empty());
    CHECK(registry.findEmployee("Michael Lee") != nullptr);
    CHECK(registry.findEmployee("michael lee") == nullptr);
}

void issuesAndReturnsKeys() {
    Registry registry = loaded();
    std::string error;
    CHECK(registry.issue("Michael Lee", "AHC111", error));
    CHECK(registry.findEmployee("Michael Lee")->keys.size() == 3);
    CHECK(registry.changed());
    CHECK(registry.giveBack("Ya Hoo", "AHC102", error));
    CHECK(registry.holders("AHC102").empty());
    CHECK(registry.onHookCount() == 1);
    CHECK(registry.history().size() == 2);
    CHECK(registry.history()[0].kind == EventKind::Issue);
    CHECK(registry.history()[0].when == "2026-10-02 09:30");
}

void enforcesTheRules() {
    Registry registry = loaded();
    std::string error;
    CHECK(!registry.issue("Nobody", "AHC1", error));
    CHECK(error == "Employee not found.");
    CHECK(!registry.issue("Ya Hoo", "AHC200", error));
    CHECK(error == "This employee already holds that key.");
    CHECK(!registry.issue("Ya Hoo", "AH C1", error));
    CHECK(error == "Key identifiers cannot contain whitespace.");
    CHECK(registry.issue("Ya Hoo", "K4", error));
    CHECK(registry.issue("Ya Hoo", "K5", error));
    CHECK(!registry.issue("Ya Hoo", "K6", error));
    CHECK(error == "This employee already holds the maximum of five keys.");
    CHECK(!registry.giveBack("Michael Lee", "K4", error));
    CHECK(error == "This employee does not hold that key.");
}

void issuingANewIdentifierCataloguesIt() {
    Registry registry = loaded();
    std::string error;
    CHECK(registry.findKey("LAB9") == nullptr);
    CHECK(registry.issue("Michael Lee", "LAB9", error));
    CHECK(registry.findKey("LAB9") != nullptr);
}

void managesEmployeesAndKeys() {
    Registry registry = loaded();
    std::string error;
    CHECK(registry.addEmployee("Ana Ruiz", error));
    CHECK(!registry.addEmployee("Ana Ruiz", error));
    CHECK(!registry.addEmployee(" Padded", error));
    CHECK(!registry.addEmployee("Pipe | Name", error));
    CHECK(!registry.addEmployee(std::string(41, 'a'), error));
    CHECK(!registry.removeEmployee("Ya Hoo", error));  // still holds keys
    CHECK(registry.removeEmployee("Ana Ruiz", error));
    CHECK(registry.findEmployee("Ana Ruiz") == nullptr);

    CHECK(registry.addKey("SRV1", "Server room", error));
    CHECK(!registry.addKey("SRV1", "", error));
    CHECK(registry.onHookCount() == 1);
    CHECK(registry.setLabel("AHC200", "Lab A", error));
    CHECK(registry.findKey("AHC200")->label == "Lab A");
    CHECK(!registry.setLabel("AHC200", std::string(33, 'x'), error));
    CHECK(!registry.setLabel("MISSING", "x", error));
}

void historyIsBounded() {
    Registry registry(fixedClock());
    std::string error;
    CHECK(registry.addEmployee("Sam", error));
    for (int i = 0; i < 600; ++i) {
        CHECK(registry.issue("Sam", "K1", error));
        CHECK(registry.giveBack("Sam", "K1", error));
    }
    CHECK(registry.history().size() == Registry::historyLimit);
}

void classicRoundTripIsExact() {
    const Registry registry = loaded();
    std::ostringstream output;
    std::string error;
    CHECK(writeRegistry(output, registry, Format::Classic, error));
    CHECK(output.str() == sample);
}

void versionTwoRoundTripKeepsEverything() {
    Registry registry = loaded();
    std::string error;
    CHECK(registry.setLabel("AHC102", "Server room", error));
    CHECK(registry.addKey("SPARE", "", error));
    CHECK(registry.issue("Michael Lee", "AHC111", error));

    std::stringstream file;
    CHECK(writeRegistry(file, registry, Format::V2, error));
    Registry copy(fixedClock());
    const ReadResult result = readRegistry(file, copy);
    CHECK(result.ok);
    CHECK(result.format == Format::V2);
    CHECK(copy.keys().size() == registry.keys().size());
    CHECK(copy.findKey("AHC102")->label == "Server room");
    CHECK(copy.findKey("SPARE") != nullptr);
    CHECK(copy.holders("SPARE").empty());
    CHECK(copy.findEmployee("Michael Lee")->keys.size() == 3);
    CHECK(copy.history().size() == registry.history().size());
    CHECK(copy.history().back().kind == EventKind::Issue);
    CHECK(copy.history().back().employee == "Michael Lee");
}

void rejectsBrokenFiles() {
    const std::vector<std::string> bad = {
        "",
        "two\nYa Hoo\n0\n",
        "1\n\n0\n",
        "2\nYa Hoo\n0\nYa Hoo\n0\n",
        "1\nYa Hoo\n6 A B C D E F\n",
        "1\nYa Hoo\n2 A\n",
        "1\nYa Hoo\n1 A extra\n",
        "1\nYa Hoo\n2 A A\n",
        "KEY_REGISTRY_V2\nA | B\n",
        "KEY_REGISTRY_V2\n[keys]\nA | B | C\n",
        "KEY_REGISTRY_V2\n[keys]\nA\nA\n",
        "KEY_REGISTRY_V2\n[employees]\nSam | A B C D E F\n",
        "KEY_REGISTRY_V2\n[history]\nwhen | teleport | Sam | A\n",
    };
    for (const std::string& text : bad) {
        Registry registry(fixedClock());
        std::istringstream input(text);
        const ReadResult result = readRegistry(input, registry);
        CHECK(!result.ok);
        CHECK(!result.error.empty());
    }
}

void reportsTheFailingLine() {
    Registry registry(fixedClock());
    std::istringstream input("2\nYa Hoo\n1 A\nSam\n9 A\n");
    const ReadResult result = readRegistry(input, registry);
    CHECK(!result.ok);
    CHECK(result.error.rfind("Line 5:", 0) == 0);
}

void exportsCsv() {
    Registry registry = loaded();
    std::string error;
    CHECK(registry.setLabel("AHC303", "Dock, north", error));
    CHECK(registry.addKey("SPARE", "", error));
    const std::string csv = toCsv(registry);
    CHECK(csv.rfind("key,label,holder\n", 0) == 0);
    CHECK(csv.find("AHC200,,Ya Hoo\n") != std::string::npos);
    CHECK(csv.find("AHC200,,Michael Lee\n") != std::string::npos);
    CHECK(csv.find("AHC303,\"Dock, north\",Michael Lee\n") != std::string::npos);
    CHECK(csv.find("SPARE,,\n") != std::string::npos);
}

}  // namespace

int main() {
    const std::vector<std::pair<const char*, std::function<void()>>> tests = {
        {"reads the classic format", readsTheClassicFormat},
        {"finds holders", findsHolders},
        {"issues and returns keys", issuesAndReturnsKeys},
        {"enforces the rules", enforcesTheRules},
        {"issuing a new identifier catalogues it", issuingANewIdentifierCataloguesIt},
        {"manages employees and keys", managesEmployeesAndKeys},
        {"history is bounded", historyIsBounded},
        {"classic round trip is exact", classicRoundTripIsExact},
        {"version 2 round trip keeps everything", versionTwoRoundTripKeepsEverything},
        {"rejects broken files", rejectsBrokenFiles},
        {"reports the failing line", reportsTheFailingLine},
        {"exports CSV", exportsCsv},
    };
    for (const auto& [name, test] : tests) {
        const int before = failures;
        test();
        std::cout << (failures == before ? "PASS  " : "FAIL  ") << name << '\n';
    }
    std::cout << '\n' << tests.size() << " tests, " << failures << " failed checks\n";
    return failures == 0 ? 0 : 1;
}
