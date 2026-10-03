#include "core/SaveFile.h"
#include "ui/App.h"
#include "ui/PlainUi.h"
#include "ui/Terminal.h"

#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <utility>
#include <iostream>
#include <string>

namespace {

void printUsage() {
    std::cout << "Usage: virtual-pet [options] [save-file]\n\n"
                 "  --plain      use numbered line menus instead of the full-screen interface\n"
                 "  --seed N     seed for random events (default: from the clock)\n"
                 "  --help       show this help\n\n"
                 "The full-screen interface starts when both input and output are a terminal.\n"
                 "Set NO_COLOR to turn colours off.\n";
}

}  // namespace

int main(int argc, char* argv[]) {
    bool plain = false;
    std::uint32_t seed = static_cast<std::uint32_t>(std::chrono::steady_clock::now().time_since_epoch().count());
    std::string savePath;

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--plain") {
            plain = true;
        } else if (arg == "--seed" && i + 1 < argc) {
            seed = static_cast<std::uint32_t>(std::strtoul(argv[++i], nullptr, 10));
        } else if (arg == "--help" || arg == "-h") {
            printUsage();
            return 0;
        } else if (!arg.empty() && arg[0] != '-') {
            savePath = arg;
        } else {
            std::cerr << "Unknown option: " << arg << "\n\n";
            printUsage();
            return 2;
        }
    }

    std::unique_ptr<vpet::Pet> loaded;
    if (!savePath.empty()) {
        vpet::LoadResult result = vpet::loadFromFile(savePath);
        if (!result.pet) {
            std::cerr << result.error << '\n';
            return 1;
        }
        loaded = std::move(result.pet);
    }

    if (plain || !vpet::Terminal::interactive()) {
        vpet::PlainUi ui(std::cin, std::cout, seed);
        if (loaded) {
            ui.open(std::move(loaded));
        }
        return ui.run();
    }

    const bool color = std::getenv("NO_COLOR") == nullptr;
    vpet::Terminal terminal;
    vpet::App app(terminal, seed, color);
    if (loaded) {
        app.open(std::move(loaded));
    }
    return app.run();
}
