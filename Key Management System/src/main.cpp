#include "core/Registry.h"
#include "core/RegistryFile.h"
#include "ui/App.h"
#include "ui/PlainUi.h"
#include "ui/Terminal.h"

#include <cstdlib>
#include <iostream>
#include <string>
#include <utility>

namespace {

void printUsage() {
    std::cout << "Usage: key-management [--plain] [registry-file]\n\n"
                 "  --plain   use the original numbered menu instead of the full-screen interface\n"
                 "  --help    show this help\n\n"
                 "The full-screen interface starts when both input and output are a terminal.\n"
                 "Registry files may be in the classic course format or version 2. Set NO_COLOR\n"
                 "to turn colours off.\n";
}

std::string readLine(const std::string& prompt) {
    while (true) {
        std::cout << prompt << std::flush;
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

}  // namespace

int main(int argc, char* argv[]) {
    bool plain = false;
    std::string path;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--plain") {
            plain = true;
        } else if (arg == "--help" || arg == "-h") {
            printUsage();
            return 0;
        } else if (!arg.empty() && arg[0] != '-') {
            path = arg;
        } else {
            std::cerr << "Unknown option: " << arg << "\n\n";
            printUsage();
            return 2;
        }
    }

    const bool interactive = !plain && kms::Terminal::interactive();
    if (!interactive) {
        if (path.empty()) {
            path = readLine("Registry file: ");
            if (path.empty()) {
                std::cerr << "No registry file was provided.\n";
                return 1;
            }
        }
        kms::Registry registry;
        const kms::ReadResult result = kms::loadRegistry(path, registry);
        if (!result.ok) {
            std::cerr << result.error << '\n';
            return 1;
        }
        kms::PlainUi ui(std::cin, std::cout, registry, result.format);
        return ui.run();
    }

    kms::Registry registry;
    kms::Format format = kms::Format::V2;
    if (!path.empty()) {
        const kms::ReadResult result = kms::loadRegistry(path, registry);
        if (!result.ok) {
            std::cerr << result.error << '\n';
            return 1;
        }
        format = result.format;
    }

    const bool color = std::getenv("NO_COLOR") == nullptr;
    kms::Terminal terminal;
    kms::App app(terminal, color);
    if (!path.empty()) {
        app.open(std::move(registry), path, format);
    }
    return app.run();
}
