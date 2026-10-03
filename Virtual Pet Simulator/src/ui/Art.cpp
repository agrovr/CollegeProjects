#include "ui/Art.h"

#include <algorithm>

namespace vpet {

namespace {

// Raw strings keep the backslashes readable. Each block is trimmed and padded on use.
const std::vector<std::string> dragonGrown = {
    R"(   /\              /\   )",
    R"(  /  \  _/\__/\_  /  \  )",
    R"(  \   \/        \/   /  )",
    R"(   \  |  @    #  |  /   )",
    R"(    \ |    &&    | /    )",
    R"(     \ \  \__/  / /     )",
    R"(    __\ \______/ /__,   )",
    R"(   /  /|        |\   \  )",
    R"(  ~~~/_|        |_\~~~  )",
};

const std::vector<std::string> dragonHatchling = {
    R"(        _/\__/\_        )",
    R"(       /        \       )",
    R"(      |  @    #  |      )",
    R"(      |    &&    |      )",
    R"(   .-~~\________/~~-.   )",
    R"(  ( \/\/\/\/\/\/\/\/ )  )",
    R"(   \                /   )",
    R"(    '-.__________.-'    )",
};

const std::vector<std::string> unicornGrown = {
    R"(          /\            )",
    R"(         /  \           )",
    R"(     ,.~/____\~.,       )",
    R"(    ( .-'    '-. )      )",
    R"(   (  |  @    #  |      )",
    R"(    ) |    &&    |)     )",
    R"(   (   \   ..   /       )",
    R"(    '~~/'------'\       )",
    R"(      /  |    |  \      )",
    R"(     (__/      \__)     )",
};

const std::vector<std::string> unicornHatchling = {
    R"(           /\           )",
    R"(       ,.~/__\~.,       )",
    R"(      ( .-'  '-. )      )",
    R"(     (  | @  # |  )     )",
    R"(      ) |  &&  | (      )",
    R"(     (   \_.._/   )     )",
    R"(      '~~/    \~~'      )",
    R"(        (_/  \_)        )",
};

const std::vector<std::string> catGrown = {
    R"(     /\_       _/\      )",
    R"(    /   \_____/   \     )",
    R"(   |   .       .   |    )",
    R"(   |    @     #    |    )",
    R"( =-|       &&      |-=  )",
    R"(   |               |    )",
    R"(    \_____________/  )  )",
    R"(     |  |     |  |  (   )",
    R"(     (__)     (__)__/   )",
};

const std::vector<std::string> catHatchling = {
    R"(       /\_____/\        )",
    R"(      /  .   .  \       )",
    R"(     |  @     #  |      )",
    R"(   =-|    &&     |-=    )",
    R"(      \         /  )    )",
    R"(       \_______/  (     )",
    R"(        (_) (_)__/      )",
};

const std::vector<std::string>& templateFor(const std::string& species, LifeStage stage) {
    const bool young = stage == LifeStage::Hatchling;
    if (species == "Unicorn") {
        return young ? unicornHatchling : unicornGrown;
    }
    if (species == "Mystic Cat") {
        return young ? catHatchling : catGrown;
    }
    return young ? dragonHatchling : dragonGrown;
}

}  // namespace

Face faceFor(Mood mood, bool blinking) {
    Face face{'o', 'o', {'_', '_'}};
    switch (mood) {
        case Mood::Joyful: face = {'^', '^', {'v', 'v'}}; break;
        case Mood::Content: face = {'o', 'o', {'u', 'u'}}; break;
        case Mood::Hungry: face = {'o', 'o', {'O', 'O'}}; break;
        case Mood::Sleepy: face = {'-', '-', {'o', '.'}}; break;
        case Mood::Bored: face = {'=', '=', {'_', '_'}}; break;
        case Mood::Grumpy: face = {'>', '<', {'^', '^'}}; break;
        case Mood::Unwell: face = {'x', 'x', {'~', '~'}}; break;
    }
    if (blinking && mood != Mood::Sleepy && mood != Mood::Unwell) {
        face.leftEye = '-';
        face.rightEye = '-';
    }
    return face;
}

std::vector<std::string> creatureArt(const std::string& species, LifeStage stage, const Face& face) {
    std::vector<std::string> lines = templateFor(species, stage);
    std::size_t width = 0;
    for (std::string& line : lines) {
        bool firstMouth = true;
        for (char& c : line) {
            if (c == '@') {
                c = face.leftEye;
            } else if (c == '#') {
                c = face.rightEye;
            } else if (c == '&') {
                c = firstMouth ? face.mouth[0] : face.mouth[1];
                firstMouth = false;
            }
        }
        width = std::max(width, line.size());
    }
    for (std::string& line : lines) {
        line.resize(width, ' ');
    }
    return lines;
}

std::vector<std::string> creaturePortrait(const std::string& species) {
    if (species == "Unicorn") {
        return {R"(  /\   )", R"( (^v^) )", R"( /|_|\ )"};
    }
    if (species == "Mystic Cat") {
        return {R"( /\_/\ )", R"(( o.o ))", R"( > ^ < )"};
    }
    return {R"( /\_/\ )", R"(( ^w^ ))", R"(/)~~(\ )"};
}

}  // namespace vpet
