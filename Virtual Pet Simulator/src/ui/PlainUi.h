#ifndef VPET_UI_PLAINUI_H
#define VPET_UI_PLAINUI_H

#include "core/Session.h"

#include <cstdint>
#include <iosfwd>
#include <memory>
#include <string>

namespace vpet {

// Line-based menus for pipes, scripts and terminals without full-screen support.
class PlainUi {
public:
    PlainUi(std::istream& input, std::ostream& output, std::uint32_t seed);

    void open(std::unique_ptr<Pet> pet);
    int run();

private:
    bool createPet();
    bool loadPet();
    void interact();
    void showStatus() const;
    void savePet();
    int readChoice(const std::string& prompt, int minimum, int maximum);
    std::string readLine(const std::string& prompt);

    std::istream& in_;
    std::ostream& out_;
    std::uint32_t seed_;
    std::unique_ptr<Session> session_;
};

}  // namespace vpet

#endif
