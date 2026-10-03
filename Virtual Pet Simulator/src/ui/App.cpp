#include "ui/App.h"

#include "core/SaveFile.h"
#include "ui/Art.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <utility>

namespace vpet {

namespace {

constexpr int frameMs = 80;
constexpr int minColumns = 88;
constexpr int minRows = 26;

// --- Palette -------------------------------------------------------------------------------------

constexpr Color background{24, 18, 38};
constexpr Color panel{34, 26, 52};
constexpr Color nightPanel{14, 12, 30};
constexpr Color cream{246, 238, 252};
constexpr Color muted{140, 128, 168};
constexpr Color faint{86, 76, 112};
constexpr Color track{46, 38, 70};
constexpr Color pink{255, 93, 143};
constexpr Color lilac{176, 132, 255};
constexpr Color teal{56, 214, 190};
constexpr Color gold{255, 204, 92};
constexpr Color red{255, 98, 98};
constexpr Color orange{255, 140, 66};

Style style(Color fg, Color bg = background, bool bold = false) {
    Style s;
    s.fg = fg;
    s.bg = bg;
    s.bold = bold;
    return s;
}

Color accentFor(const std::string& species) {
    if (species == "Unicorn") {
        return lilac;
    }
    if (species == "Mystic Cat") {
        return teal;
    }
    return orange;
}

Color mix(Color a, Color b, double t) {
    t = std::clamp(t, 0.0, 1.0);
    return Color{static_cast<std::uint8_t>(a.r + (b.r - a.r) * t), static_cast<std::uint8_t>(a.g + (b.g - a.g) * t),
                 static_cast<std::uint8_t>(a.b + (b.b - a.b) * t)};
}

const std::vector<std::string> speciesNames = {"Dragon", "Unicorn", "Mystic Cat"};

const std::vector<std::string> speciesBlurbs = {
    "Proud and fiery. Loves to fly, needs discipline.",
    "Gentle and radiant. Can heal itself with light.",
    "Curious and clever. Mischief comes naturally.",
};

const std::vector<std::string> logo = {
    R"(██╗   ██╗██╗██████╗ ████████╗██╗   ██╗ █████╗ ██╗         ██████╗ ███████╗████████╗)",
    R"(██║   ██║██║██╔══██╗╚══██╔══╝██║   ██║██╔══██╗██║         ██╔══██╗██╔════╝╚══██╔══╝)",
    R"(██║   ██║██║██████╔╝   ██║   ██║   ██║███████║██║         ██████╔╝█████╗     ██║   )",
    R"(╚██╗ ██╔╝██║██╔══██╗   ██║   ██║   ██║██╔══██║██║         ██╔═══╝ ██╔══╝     ██║   )",
    R"( ╚████╔╝ ██║██║  ██║   ██║   ╚██████╔╝██║  ██║███████╗    ██║     ███████╗   ██║   )",
    R"(  ╚═══╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝    ╚═╝     ╚══════╝   ╚═╝   )",
};

std::string truncate(const std::string& text, std::size_t width) {
    const std::vector<std::string> glyphs = splitUtf8(text);
    if (glyphs.size() <= width) {
        return text;
    }
    std::string out;
    for (std::size_t i = 0; i + 1 < width; ++i) {
        out += glyphs[i];
    }
    return out + "…";
}

std::vector<std::string> wrap(const std::string& text, std::size_t width) {
    std::vector<std::string> lines;
    std::string line;
    std::string word;
    auto flush = [&]() {
        if (word.empty()) {
            return;
        }
        if (!line.empty() && line.size() + 1 + word.size() > width) {
            lines.push_back(line);
            line.clear();
        }
        line += (line.empty() ? "" : " ") + word;
        word.clear();
    };
    for (char c : text) {
        if (c == ' ') {
            flush();
        } else {
            word += c;
        }
    }
    flush();
    if (!line.empty()) {
        lines.push_back(line);
    }
    return lines;
}

std::string spaced(const std::string& text) {
    std::string out;
    for (char c : text) {
        if (!out.empty()) {
            out += ' ';
        }
        out += static_cast<char>(c >= 'a' && c <= 'z' ? c - 'a' + 'A' : c);
    }
    return out;
}

int centered(int x, int width, std::size_t length) {
    return x + (width - static_cast<int>(length)) / 2;
}

}  // namespace

App::App(Terminal& terminal, std::uint32_t seed, bool color) : terminal_(terminal), seed_(seed), color_(color) {}

void App::open(std::unique_ptr<Pet> pet) {
    startPet(std::move(pet));
}

int App::run() {
    while (running_) {
        int columns = 0;
        int rows = 0;
        terminal_.size(columns, rows);
        Canvas canvas(columns, rows, style(cream));
        draw(canvas);
        terminal_.write(canvas.render(color_));
        const Key key = terminal_.readKey(frameMs);
        if (key.type != KeyType::None) {
            handle(key);
        }
        ++frame_;
    }
    return 0;
}

// --- Input -----------------------------------------------------------------------------------------

void App::handle(const Key& key) {
    if (overlay_ != Overlay::None) {
        handleOverlay(key);
        return;
    }
    switch (screen_) {
        case Screen::Title: handleTitle(key); break;
        case Screen::Species: handleSpecies(key); break;
        case Screen::Name: handleName(key); break;
        case Screen::Dashboard: handleDashboard(key); break;
        case Screen::Load: handleLoad(key); break;
    }
}

void App::handleTitle(const Key& key) {
    if (key.type == KeyType::Up) {
        titleChoice_ = (titleChoice_ + 2) % 3;
    } else if (key.type == KeyType::Down || key.type == KeyType::Tab) {
        titleChoice_ = (titleChoice_ + 1) % 3;
    }
    int choice = -1;
    if (key.type == KeyType::Enter) {
        choice = titleChoice_;
    } else if (key.is('n') || key.is('1')) {
        choice = 0;
    } else if (key.is('l') || key.is('2')) {
        choice = 1;
    } else if (key.is('q') || key.is('3') || key.type == KeyType::Escape) {
        choice = 2;
    }
    if (choice == 0) {
        screen_ = Screen::Species;
    } else if (choice == 1) {
        refreshSaves();
        loadChoice_ = 0;
        input_.clear();
        error_.clear();
        screen_ = Screen::Load;
    } else if (choice == 2) {
        running_ = false;
    }
}

void App::handleSpecies(const Key& key) {
    if (key.type == KeyType::Left) {
        speciesChoice_ = (speciesChoice_ + 2) % 3;
    } else if (key.type == KeyType::Right || key.type == KeyType::Tab) {
        speciesChoice_ = (speciesChoice_ + 1) % 3;
    } else if (key.type == KeyType::Char && key.ch >= '1' && key.ch <= '3') {
        speciesChoice_ = key.ch - '1';
    } else if (key.type == KeyType::Escape) {
        screen_ = Screen::Title;
    } else if (key.type == KeyType::Enter) {
        input_.clear();
        error_.clear();
        screen_ = Screen::Name;
    }
}

void App::handleName(const Key& key) {
    if (key.type == KeyType::Escape) {
        screen_ = Screen::Species;
    } else if (key.type == KeyType::Backspace) {
        if (!input_.empty()) {
            input_.pop_back();
        }
    } else if (key.type == KeyType::Char && input_.size() < 16) {
        const char c = key.ch;
        const bool allowed = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == ' ' || c == '-' || c == '\'';
        if (allowed && !(c == ' ' && input_.empty())) {
            // Capitalise the first letter of each word.
            const bool wordStart = input_.empty() || input_.back() == ' ' || input_.back() == '-';
            input_ += (wordStart && c >= 'a' && c <= 'z') ? static_cast<char>(c - 'a' + 'A') : c;
        }
    } else if (key.type == KeyType::Enter) {
        while (!input_.empty() && input_.back() == ' ') {
            input_.pop_back();
        }
        if (input_.empty()) {
            error_ = "Every pet needs a name.";
            return;
        }
        startPet(makePet(speciesNames[static_cast<std::size_t>(speciesChoice_)], input_));
    }
}

void App::handleDashboard(const Key& key) {
    if (key.is('f')) {
        act(Action::Feed);
    } else if (key.is('r')) {
        act(Action::Rest);
    } else if (key.is('p')) {
        act(Action::Play);
    } else if (key.is('1')) {
        act(Action::Special1);
    } else if (key.is('2')) {
        act(Action::Special2);
    } else if (key.is('w') || key.is(' ')) {
        act(Action::Wait);
    } else if (key.is('s')) {
        input_ = defaultSavePath();
        error_.clear();
        overlay_ = Overlay::Save;
    } else if (key.is('?') || key.is('h')) {
        overlay_ = Overlay::Help;
    } else if (key.is('q') || key.type == KeyType::Escape) {
        overlay_ = Overlay::Quit;
    }
}

void App::handleLoad(const Key& key) {
    const int count = static_cast<int>(saves_.size()) + 1;  // last entry: type a path
    const bool typing = loadChoice_ == count - 1;
    if (key.type == KeyType::Escape) {
        screen_ = Screen::Title;
        return;
    }
    if (key.type == KeyType::Up) {
        loadChoice_ = (loadChoice_ + count - 1) % count;
        error_.clear();
        return;
    }
    if (key.type == KeyType::Down || key.type == KeyType::Tab) {
        loadChoice_ = (loadChoice_ + 1) % count;
        error_.clear();
        return;
    }
    if (typing && key.type == KeyType::Backspace && !input_.empty()) {
        input_.pop_back();
        return;
    }
    if (typing && key.type == KeyType::Char && input_.size() < 120) {
        input_ += key.ch;
        return;
    }
    if (key.type == KeyType::Enter) {
        const std::string path = typing ? input_ : saves_[static_cast<std::size_t>(loadChoice_)];
        if (path.empty()) {
            error_ = "Type the path of a .sav file.";
            return;
        }
        LoadResult result = loadFromFile(path);
        if (!result.pet) {
            error_ = result.error;
            return;
        }
        startPet(std::move(result.pet));
        status_ = "Loaded " + path + ".";
    }
}

void App::handleOverlay(const Key& key) {
    if (overlay_ == Overlay::Help) {
        overlay_ = Overlay::None;
        return;
    }
    if (overlay_ == Overlay::Save) {
        if (key.type == KeyType::Escape) {
            overlay_ = Overlay::None;
        } else if (key.type == KeyType::Backspace) {
            if (!input_.empty()) {
                input_.pop_back();
            }
        } else if (key.type == KeyType::Char && input_.size() < 120) {
            input_ += key.ch;
        } else if (key.type == KeyType::Enter) {
            std::string error;
            if (saveToFile(input_, session_->pet(), error)) {
                status_ = "Saved to " + input_ + ".";
                overlay_ = Overlay::None;
            } else {
                error_ = error;
            }
        }
        return;
    }
    // Quit confirmation.
    if (key.is('y')) {
        std::string error;
        if (saveToFile(defaultSavePath(), session_->pet(), error)) {
            status_.clear();
            overlay_ = Overlay::None;
            session_.reset();
            screen_ = Screen::Title;
        } else {
            error_ = error;
        }
    } else if (key.is('n')) {
        overlay_ = Overlay::None;
        session_.reset();
        screen_ = Screen::Title;
    } else if (key.type == KeyType::Escape) {
        overlay_ = Overlay::None;
    }
}

void App::act(Action action) {
    last_ = session_->perform(action);
    hasOutcome_ = true;
    status_.clear();
    animationUntil_ = frame_ + 22;
    deltaUntil_ = frame_ + 30;
}

void App::startPet(std::unique_ptr<Pet> pet) {
    if (!pet) {
        return;
    }
    const std::string name = pet->name();
    const std::string species = pet->species();
    session_ = std::make_unique<Session>(std::move(pet), seed_);
    session_->note(name + " the " + species + " is ready for adventure.");
    hasOutcome_ = false;
    status_.clear();
    error_.clear();
    overlay_ = Overlay::None;
    screen_ = Screen::Dashboard;
}

void App::refreshSaves() {
    saves_.clear();
    std::error_code ec;
    for (const auto& entry : std::filesystem::directory_iterator(".", ec)) {
        if (entry.is_regular_file() && entry.path().extension() == ".sav") {
            saves_.push_back(entry.path().filename().string());
        }
    }
    std::sort(saves_.begin(), saves_.end());
    if (saves_.size() > 8) {
        saves_.resize(8);
    }
}

std::string App::defaultSavePath() const {
    std::string path;
    for (char c : session_->pet().name()) {
        if (c >= 'A' && c <= 'Z') {
            path += static_cast<char>(c - 'A' + 'a');
        } else if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) {
            path += c;
        } else if (!path.empty() && path.back() != '-') {
            path += '-';
        }
    }
    return (path.empty() ? std::string("pet") : path) + ".sav";
}

// --- Drawing ---------------------------------------------------------------------------------------

void App::draw(Canvas& canvas) const {
    const int columns = canvas.columns();
    const int rows = canvas.rows();
    if (columns < minColumns || rows < minRows) {
        char line[96];
        std::snprintf(line, sizeof(line), "Make the window at least %d x %d (now %d x %d).", minColumns, minRows,
                      columns, rows);
        canvas.text(std::max(0, (columns - static_cast<int>(utf8Length(line))) / 2), rows / 2, line, style(gold));
        return;
    }
    const int w = std::min(columns, 108);
    const int h = std::min(rows, 32);
    const int x = (columns - w) / 2;
    const int y = (rows - h) / 2;

    switch (screen_) {
        case Screen::Title: drawTitle(canvas, x, y, w, h); break;
        case Screen::Species: drawSpecies(canvas, x, y, w, h); break;
        case Screen::Name: drawName(canvas, x, y, w, h); break;
        case Screen::Dashboard: drawDashboard(canvas, x, y, w, h); break;
        case Screen::Load: drawLoad(canvas, x, y, w, h); break;
    }
    if (overlay_ != Overlay::None) {
        drawOverlay(canvas, x, y, w, h);
    }
}

void App::drawFooter(Canvas& canvas, int x, int y, int w,
                     const std::vector<std::pair<std::string, std::string>>& keys) const {
    int cx = x;
    for (const auto& [key, label] : keys) {
        const int width = static_cast<int>(utf8Length(key) + utf8Length(label)) + 4;
        if (cx + width > x + w) {
            break;
        }
        canvas.text(cx, y, " " + key + " ", style(background, pink, true));
        canvas.text(cx + static_cast<int>(utf8Length(key)) + 2, y, " " + label, style(muted));
        cx += width + 1;
    }
}

void App::drawTitle(Canvas& canvas, int x, int y, int w, int h) const {
    canvas.box(x, y, w, h, style(faint));
    // Logo with a pink -> lilac -> teal sweep that drifts slowly.
    const int logoWidth = static_cast<int>(utf8Length(logo[0]));
    const int lx = centered(x, w, static_cast<std::size_t>(logoWidth));
    const int ly = y + 3;
    for (std::size_t row = 0; row < logo.size(); ++row) {
        const std::vector<std::string> glyphs = splitUtf8(logo[row]);
        for (std::size_t col = 0; col < glyphs.size(); ++col) {
            const double phase = static_cast<double>(col) / logoWidth * 0.9 + static_cast<double>(frame_) * 0.006;
            const double t = 1.0 - std::fabs(std::fmod(phase, 2.0) - 1.0);
            const Color c = t < 0.5 ? mix(pink, lilac, t * 2) : mix(lilac, teal, (t - 0.5) * 2);
            canvas.text(lx + static_cast<int>(col), ly + static_cast<int>(row), glyphs[col],
                        style(glyphs[col] == "█" ? c : mix(c, background, 0.45)));
        }
    }
    const std::string tagline = "Raise a Dragon, a Unicorn or a Mystic Cat, one hour at a time.";
    canvas.text(centered(x, w, tagline.size()), ly + 8, tagline, style(muted));

    // Three portraits that bob out of step.
    const int py = ly + 11;
    for (int i = 0; i < 3; ++i) {
        const std::string& species = speciesNames[static_cast<std::size_t>(i)];
        const int px = x + w / 2 - 27 + i * 20;
        const int bob = ((frame_ / 6) + i) % 2;
        const std::vector<std::string> portrait = creaturePortrait(species);
        for (std::size_t row = 0; row < portrait.size(); ++row) {
            canvas.text(px, py + static_cast<int>(row) - bob, portrait[row], style(accentFor(species), background, true));
        }
        canvas.text(centered(px, 7, species.size()), py + 4, species, style(accentFor(species)));
    }

    const std::vector<std::string> items = {"New pet", "Load a pet", "Quit"};
    const std::vector<std::string> hotkeys = {"N", "L", "Q"};
    const int my = py + 7;
    for (int i = 0; i < 3; ++i) {
        const bool selected = i == titleChoice_;
        const std::string label = (selected ? "▸ " : "  ") + items[static_cast<std::size_t>(i)];
        const int mx = centered(x, w, 18);
        canvas.text(mx, my + i, " " + hotkeys[static_cast<std::size_t>(i)] + " ",
                    selected ? style(background, pink, true) : style(muted, panel));
        canvas.text(mx + 4, my + i, label, selected ? style(cream, background, true) : style(muted));
    }
    drawFooter(canvas, x + 2, y + h - 2, w - 4, {{"↑↓", "Choose"}, {"Enter", "Select"}, {"Q", "Quit"}});
}

void App::drawSpecies(Canvas& canvas, int x, int y, int w, int h) const {
    canvas.box(x, y, w, h, style(faint), "CHOOSE A COMPANION", style(pink, background, true));
    const int cardWidth = (w - 8) / 3;
    const int cardHeight = h - 6;
    for (int i = 0; i < 3; ++i) {
        const std::string& species = speciesNames[static_cast<std::size_t>(i)];
        const bool selected = i == speciesChoice_;
        const Color accent = accentFor(species);
        const int cx = x + 2 + i * (cardWidth + 2);
        const int cy = y + 2;
        canvas.fill(cx + 1, cy + 1, cardWidth - 2, cardHeight - 2, style(cream, selected ? panel : background));
        canvas.box(cx, cy, cardWidth, cardHeight, selected ? style(accent, background, true) : style(faint));
        const Style text = style(cream, selected ? panel : background);
        canvas.text(centered(cx, cardWidth, species.size() * 2 - 1), cy + 1, spaced(species),
                    style(accent, selected ? panel : background, true));

        const bool blink = selected && frame_ % 40 < 2;
        const std::vector<std::string> art =
            creatureArt(species, LifeStage::Adult, faceFor(selected ? Mood::Joyful : Mood::Content, blink));
        const int bob = selected ? static_cast<int>((frame_ / 7) % 2) : 0;
        for (std::size_t row = 0; row < art.size(); ++row) {
            const Color c = mix(accent, cream, 0.35 - 0.35 * static_cast<double>(row) / static_cast<double>(art.size()));
            canvas.text(centered(cx, cardWidth, art[row].size()), cy + 3 + static_cast<int>(row) - bob, art[row],
                        style(selected ? c : mix(c, background, 0.5), selected ? panel : background, selected));
        }

        auto pet = makePet(species, "x");
        const auto actions = pet->specialActions();
        const int ty = cy + 14;
        canvas.text(cx + 3, ty, "Abilities", style(muted, selected ? panel : background));
        canvas.text(cx + 3, ty + 1, "✦ " + actions[0].name, text);
        canvas.text(cx + 3, ty + 2, "✦ " + actions[1].name, text);
        const std::vector<std::string> blurb = wrap(speciesBlurbs[static_cast<std::size_t>(i)], static_cast<std::size_t>(cardWidth - 6));
        for (std::size_t line = 0; line < blurb.size(); ++line) {
            canvas.text(cx + 3, ty + 4 + static_cast<int>(line), blurb[line], style(muted, selected ? panel : background));
        }
        if (selected && cy + cardHeight - 2 > ty + 4 + static_cast<int>(blurb.size())) {
            const std::string choose = "▸ Press Enter";
            canvas.text(centered(cx, cardWidth, utf8Length(choose)), cy + cardHeight - 2, choose,
                        style(accent, panel, true));
        }
    }
    drawFooter(canvas, x + 2, y + h - 2, w - 4, {{"←→", "Browse"}, {"Enter", "Choose"}, {"Esc", "Back"}});
}

void App::drawName(Canvas& canvas, int x, int y, int w, int h) const {
    const std::string& species = speciesNames[static_cast<std::size_t>(speciesChoice_)];
    const Color accent = accentFor(species);
    canvas.box(x, y, w, h, style(faint), "A NEW " + spaced(species), style(accent, background, true));

    const std::vector<std::string> art = creatureArt(species, LifeStage::Hatchling, faceFor(Mood::Content, frame_ % 36 < 2));
    const int ay = y + (h - static_cast<int>(art.size())) / 2 - 2;
    for (std::size_t row = 0; row < art.size(); ++row) {
        canvas.text(x + 6, ay + static_cast<int>(row), art[row], style(mix(accent, cream, 0.2), background, true));
    }

    const int fx = x + 38;
    const int fy = y + h / 2 - 4;
    canvas.text(fx, fy, "Your egg is hatching.", style(muted));
    canvas.text(fx, fy + 1, "What will you call your " + species + "?", style(cream, background, true));
    canvas.box(fx, fy + 3, 36, 3, style(accent));
    const bool cursorOn = (frame_ / 6) % 2 == 0;
    canvas.text(fx + 2, fy + 4, input_ + (cursorOn ? "▌" : " "), style(cream, background, true));
    if (!error_.empty()) {
        canvas.text(fx, fy + 7, error_, style(red));
    } else {
        canvas.text(fx, fy + 7, "Up to 16 letters, numbers, spaces or dashes.", style(faint));
    }
    drawFooter(canvas, x + 2, y + h - 2, w - 4, {{"Enter", "Hatch"}, {"Esc", "Back"}});
}

void App::drawLoad(Canvas& canvas, int x, int y, int w, int h) const {
    canvas.box(x, y, w, h, style(faint), "LOAD A PET", style(pink, background, true));
    int ly = y + 3;
    canvas.text(x + 4, ly, saves_.empty() ? "No .sav files in this folder." : "Saves in this folder", style(muted));
    ly += 2;
    for (std::size_t i = 0; i < saves_.size(); ++i) {
        const bool selected = static_cast<int>(i) == loadChoice_;
        std::string detail;
        LoadResult info = loadFromFile(saves_[i]);
        if (info.pet) {
            detail = info.pet->name() + " the " + info.pet->species() + " · " + stageName(info.pet->stage()) + " · " +
                     std::to_string(info.pet->ageHours()) + "h old";
        } else {
            detail = info.error;
        }
        canvas.text(x + 4, ly, selected ? "▸" : " ", style(pink, background, true));
        canvas.text(x + 6, ly, saves_[i], selected ? style(cream, background, true) : style(muted));
        canvas.text(x + 32, ly, truncate(detail, static_cast<std::size_t>(w - 36)),
                    style(info.pet ? (selected ? accentFor(info.pet->species()) : faint) : red));
        ++ly;
    }
    ++ly;
    const bool typing = loadChoice_ == static_cast<int>(saves_.size());
    canvas.text(x + 4, ly, typing ? "▸" : " ", style(pink, background, true));
    canvas.text(x + 6, ly, "Path:", typing ? style(cream, background, true) : style(muted));
    canvas.box(x + 12, ly - 1, w - 18, 3, typing ? style(pink) : style(faint));
    const bool cursorOn = typing && (frame_ / 6) % 2 == 0;
    canvas.text(x + 14, ly, truncate(input_, static_cast<std::size_t>(w - 24)) + (cursorOn ? "▌" : ""), style(cream));
    if (!error_.empty()) {
        canvas.text(x + 4, ly + 3, error_, style(red));
    }
    drawFooter(canvas, x + 2, y + h - 2, w - 4, {{"↑↓", "Choose"}, {"Enter", "Load"}, {"Esc", "Back"}});
}

void App::drawCreature(Canvas& canvas, int x, int y, int w, int h) const {
    const Pet& pet = session_->pet();
    const Color accent = accentFor(pet.species());
    const bool night = session_->isNight();
    const Color bg = night ? nightPanel : panel;
    canvas.fill(x + 1, y + 1, w - 2, h - 2, style(cream, bg));
    canvas.box(x, y, w, h, style(mix(accent, bg, 0.35), background));

    // Sky: stars at night, a soft sun by day.
    if (night) {
        const int stars[][2] = {{3, 2}, {9, 1}, {w - 5, 2}, {w - 10, 4}, {5, 5}, {w - 4, 7}};
        for (int i = 0; i < 6; ++i) {
            const bool twinkle = (frame_ / 5 + i) % 4 == 0;
            canvas.text(x + stars[i][0], y + stars[i][1], twinkle ? "✦" : "·", style(twinkle ? gold : muted, bg));
        }
    } else {
        canvas.text(x + w - 5, y + 2, "☼", style(gold, bg, true));
    }

    const bool animating = hasOutcome_ && frame_ < animationUntil_;
    const Animation animation = animating ? last_.animation : Animation::None;
    const Mood mood = pet.mood();
    const bool blink = frame_ % 46 < 2;
    const std::vector<std::string> art = creatureArt(pet.species(), pet.stage(), faceFor(
        animation == Animation::Sleep ? Mood::Sleepy : animation == Animation::Play || animation == Animation::Special ? Mood::Joyful : mood,
        blink));
    const int aw = static_cast<int>(art[0].size());
    const int ah = static_cast<int>(art.size());
    const bool still = mood == Mood::Unwell || mood == Mood::Sleepy || animation == Animation::Sleep;
    const int bob = still ? 0 : static_cast<int>((frame_ / 7) % 2);
    const bool flying = animation == Animation::Special && pet.species() == "Dragon" && last_.action == Action::Special1;
    const int hop = animation == Animation::Play ? static_cast<int>((frame_ / 3) % 2)
                  : flying ? 1 + static_cast<int>((frame_ / 4) % 2) : 0;
    const int ax = x + (w - aw) / 2;
    const int ay = y + (h - ah) / 2 + 1 - bob - hop;

    // Particles behind the creature.
    auto particle = [&](int px, int py, const std::string& glyph, Color c) {
        if (px > x && px < x + w - 1 && py > y && py < y + h - 1) {
            canvas.text(px, py, glyph, style(c, bg, true));
        }
    };
    const bool sleepy = animation == Animation::Sleep || (animation == Animation::None && mood == Mood::Sleepy);
    if (sleepy) {
        for (int k = 0; k < 3; ++k) {
            const int phase = static_cast<int>((frame_ + k * 7) % 21);
            particle(ax + aw - 4 + k + phase / 7, ay + 1 - phase / 7, k == 2 ? "Z" : "z", lilac);
        }
    }
    switch (animation) {
        case Animation::Eat:
            for (int k = 0; k < 4; ++k) {
                const int phase = static_cast<int>((frame_ + k * 3) % 8);
                particle(ax + aw / 2 - 4 + k * 3, ay + 5 + phase / 2, k % 2 ? "∘" : "°", gold);
            }
            break;
        case Animation::Play:
            for (int k = 0; k < 4; ++k) {
                const int phase = static_cast<int>((frame_ + k * 5) % 18);
                const int side = k % 2 ? ax + aw + 1 : ax - 2;
                particle(side + (k / 2), ay + ah - 2 - phase / 2, "♥", pink);
            }
            break;
        case Animation::Special: {
            const bool first = last_.action == Action::Special1;
            const double cx = ax + aw / 2.0;
            const double cy = ay + ah / 2.0;
            if (pet.species() == "Dragon" && first) {
                // Flight: gusts of wind sweep under the wings.
                for (int k = 0; k < 6; ++k) {
                    const int drift = static_cast<int>((frame_ * 2 + k * 5) % (w - 4));
                    particle(x + 2 + drift, ay + ah - 2 + (k % 3), k % 2 ? "~" : "≈", mix(cream, lilac, 0.4));
                }
            } else if (pet.species() == "Dragon") {
                // Flame: a flickering jet from the snout.
                for (int k = 0; k < 7; ++k) {
                    const bool hot = (frame_ + k) % 3 == 0;
                    particle(ax + aw - 3 + k, ay + 4 + static_cast<int>((frame_ / 2 + k) % 2), k % 2 ? "≈" : "~", hot ? gold : orange);
                }
            } else if (pet.species() == "Unicorn" && first) {
                // Healing: soft crosses rise around the body.
                for (int k = 0; k < 5; ++k) {
                    const int phase = static_cast<int>((frame_ + k * 4) % 16);
                    particle(ax - 1 + k * (aw + 2) / 4, ay + ah - 1 - phase / 2, "+", teal);
                }
            } else if (pet.species() == "Mystic Cat" && first) {
                // Telekinesis: a toy floats above the head, wobbling.
                const int wobble = static_cast<int>(std::lround(std::sin(static_cast<double>(frame_) * 0.4) * 2));
                particle(static_cast<int>(cx) + wobble, ay - 1 - static_cast<int>((frame_ / 4) % 2), "◆", gold);
                particle(static_cast<int>(cx) + wobble - 2, ay, "·", teal);
                particle(static_cast<int>(cx) + wobble + 2, ay, "·", teal);
            } else {
                // Spell and trick: sparkles orbit the creature.
                const bool unicorn = pet.species() == "Unicorn";
                for (int k = 0; k < 6; ++k) {
                    const double angle = static_cast<double>(frame_) * 0.35 + k * 1.047;
                    particle(static_cast<int>(cx + std::cos(angle) * (aw / 2.0 + 3)),
                             static_cast<int>(cy + std::sin(angle) * (ah / 2.0 + 0.5)),
                             unicorn ? (k % 2 ? "✧" : "✦") : (k % 2 ? "*" : "°"), unicorn ? lilac : teal);
                }
            }
            break;
        }
        case Animation::Refuse:
            particle(ax + aw / 2, ay - 1, (frame_ / 4) % 2 ? "?" : " ", gold);
            particle(ax + aw / 2 + 2, ay - 1, "…", muted);
            break;
        case Animation::Event:
            particle(ax + aw / 2, ay - 1, "!", gold);
            break;
        default:
            if (mood == Mood::Joyful && (frame_ / 10) % 6 == 0) {
                particle(ax + aw, ay, "♪", pink);
            }
            break;
    }

    // The creature, drawn with transparent spaces and a soft vertical gradient.
    for (int row = 0; row < ah; ++row) {
        const Color c = mix(mix(accent, cream, 0.3), accent, static_cast<double>(row) / ah);
        const std::string& line = art[static_cast<std::size_t>(row)];
        for (int col = 0; col < aw; ++col) {
            if (line[static_cast<std::size_t>(col)] != ' ') {
                canvas.text(ax + col, ay + row, std::string(1, line[static_cast<std::size_t>(col)]),
                            style(mood == Mood::Unwell ? mix(c, muted, 0.5) : c, bg, true));
            }
        }
    }

    // A speech bubble for the current reaction.
    if (animating) {
        std::string bubble;
        switch (last_.animation) {
            case Animation::Eat: bubble = "nom nom"; break;
            case Animation::Sleep: bubble = "zzz…"; break;
            case Animation::Play: bubble = "wheee!"; break;
            case Animation::Special: {
                const bool first = last_.action == Action::Special1;
                const std::string& species = session_->pet().species();
                bubble = species == "Dragon" ? (first ? "whoosh!" : "fwoosh!")
                       : species == "Unicorn" ? (first ? "✚ glow" : "✦ shine!")
                       : (first ? "hmmm…" : "ta-da!");
                break;
            }
            case Animation::Refuse: bubble = "hmph."; break;
            case Animation::Event: bubble = "oh!"; break;
            default: break;
        }
        if (!bubble.empty()) {
            const std::string text = "( " + bubble + " )";
            canvas.text(centered(x, w, utf8Length(text)), y + 1, text, style(cream, bg, true));
        }
    }
}

void App::drawDashboard(Canvas& canvas, int x, int y, int w, int h) const {
    const Pet& pet = session_->pet();
    const Stats& s = pet.stats();
    const Color accent = accentFor(pet.species());

    canvas.box(x, y, w, h, style(faint), "VIRTUAL PET", style(pink, background, true));
    const std::string clock = " " + session_->clockLabel() + (session_->isNight() ? "  ☾ " : "  ☼ ");
    canvas.text(x + w - 2 - static_cast<int>(utf8Length(clock)), y, clock,
                style(session_->isNight() ? lilac : gold, background, true));

    const int footerY = y + h - 2;
    const int journalHeight = 8;
    const int journalY = footerY - journalHeight - 1;
    const int panelX = x + 2;
    const int panelY = y + 2;
    const int panelW = 36;
    const int panelH = journalY - panelY;
    drawCreature(canvas, panelX, panelY, panelW, panelH);

    // Identity.
    const int ix = panelX + panelW + 3;
    const int iw = x + w - 3 - ix;
    int iy = panelY;
    std::string upper;
    for (char c : pet.name()) {
        upper += static_cast<char>(c >= 'a' && c <= 'z' ? c - 'a' + 'A' : c);
    }
    canvas.text(ix, iy, upper, style(accent, background, true));
    canvas.text(ix + static_cast<int>(upper.size()) + 1, iy, "the " + pet.species(), style(muted));
    ++iy;
    const std::string stage = std::string(" ") + stageName(pet.stage()) + " ";
    canvas.text(ix, iy + 1, stage, style(background, accent, true));
    canvas.text(ix + static_cast<int>(stage.size()) + 1, iy + 1, std::to_string(pet.ageHours()) + "h old", style(muted));

    const Mood mood = pet.mood();
    const Color moodColor = mood == Mood::Joyful ? teal : mood == Mood::Content ? cream
                          : mood == Mood::Unwell ? red : gold;
    canvas.text(ix, iy + 3, "Mood", style(muted));
    canvas.text(ix + 6, iy + 3, "●", style(moodColor));
    canvas.text(ix + 8, iy + 3, moodName(mood), style(moodColor, background, true));

    const int full = (pet.bond() + 10) / 20;
    canvas.text(ix + 22, iy + 3, "Bond", style(muted));
    for (int i = 0; i < 5; ++i) {
        canvas.text(ix + 28 + i * 2, iy + 3, "♥", i < full ? style(pink, background, true) : style(faint));
    }

    // Meters.
    struct Row {
        const char* label;
        int value;
        int before;
        bool need;  // higher is worse
    };
    const Row rows[] = {
        {"Health", s.health, last_.before.health, false},
        {"Happiness", s.happiness, last_.before.happiness, false},
        {"Discipline", s.discipline, last_.before.discipline, false},
        {"Hunger", s.hunger, last_.before.hunger, true},
        {"Fatigue", s.fatigue, last_.before.fatigue, true},
        {"Boredom", s.boredom, last_.before.boredom, true},
    };
    const int metersTop = iy + 6;
    const int space = panelY + panelH - metersTop - 2;
    const int step = space >= 14 ? 2 : 1;
    const int gap = space >= 8 ? 2 : 0;  // a labelled break between wellbeing and needs
    canvas.text(ix, metersTop - 1, "WELLBEING", style(faint, background, true));
    if (gap) {
        canvas.text(ix, metersTop + 3 * step + gap - 1, "NEEDS", style(faint, background, true));
    }
    const int meterWidth = std::max(10, iw - 22);
    const bool showDelta = hasOutcome_ && frame_ < deltaUntil_;
    for (int i = 0; i < 6; ++i) {
        const Row& row = rows[i];
        const int ry = metersTop + i * step + (i >= 3 ? gap : 0);
        Color c;
        if (row.need) {
            c = row.value >= Pet::unmetNeedThreshold ? red : row.value > 40 ? gold : teal;
        } else {
            c = row.value >= 60 ? teal : row.value >= 30 ? gold : red;
        }
        const bool alarm = row.need && row.value >= Pet::unmetNeedThreshold && (frame_ / 5) % 2 == 0;
        canvas.text(ix, ry, row.label, style(alarm ? red : cream));
        canvas.meter(ix + 11, ry, meterWidth, row.value, style(c), style(track));
        char value[8];
        std::snprintf(value, sizeof(value), "%3d", row.value);
        canvas.text(ix + 12 + meterWidth, ry, value, style(c, background, true));
        const int delta = row.value - row.before;
        if (showDelta && delta != 0) {
            const bool good = row.need ? delta < 0 : delta > 0;
            char d[8];
            std::snprintf(d, sizeof(d), "%+d", delta);
            canvas.text(ix + 16 + meterWidth, ry, d, style(good ? teal : red, background, true));
        }
    }

    // Advice for the most pressing need.
    std::string advice;
    switch (mood) {
        case Mood::Hungry: advice = pet.name() + " is hungry. Try F to feed."; break;
        case Mood::Sleepy: advice = pet.name() + " can barely keep its eyes open. Try R to rest."; break;
        case Mood::Bored: advice = pet.name() + " is restless. Try P to play."; break;
        case Mood::Grumpy: advice = pet.name() + " is in a mood. Play or an ability may help."; break;
        case Mood::Unwell: advice = pet.name() + " feels unwell. Rest and food will help it recover."; break;
        default:
            advice = s.discipline < 25 ? pet.name() + " may ignore you. Abilities build discipline."
                                       : pet.name() + " is doing well.";
            break;
    }
    canvas.text(ix, panelY + panelH - 1, truncate(advice, static_cast<std::size_t>(iw)), style(muted));

    // Journal.
    canvas.box(panelX, journalY, w - 4, journalHeight + 1, style(faint), "JOURNAL", style(muted, background, true));
    const auto& log = session_->log();
    const int lines = journalHeight - 1;
    std::vector<std::string> entries(log.begin(), log.end());
    if (!status_.empty()) {
        entries.push_back(status_);
    }
    const int start = std::max(0, static_cast<int>(entries.size()) - lines);
    for (int i = start; i < static_cast<int>(entries.size()); ++i) {
        const bool newest = i == static_cast<int>(entries.size()) - 1;
        const bool isStatus = !status_.empty() && newest;
        canvas.text(panelX + 2, journalY + 1 + (i - start), newest ? "▸" : "·", style(newest ? pink : faint));
        canvas.text(panelX + 4, journalY + 1 + (i - start), truncate(entries[static_cast<std::size_t>(i)], static_cast<std::size_t>(w - 10)),
                    style(isStatus ? teal : newest ? cream : muted));
    }

    const auto actions = pet.specialActions();
    drawFooter(canvas, x + 2, footerY, w - 4,
               {{"F", "Feed"}, {"R", "Rest"}, {"P", "Play"}, {"1", actions[0].verb}, {"2", actions[1].verb},
                {"W", "Wait"}, {"S", "Save"}, {"?", "Help"}, {"Q", "Quit"}});
}

void App::drawOverlay(Canvas& canvas, int x, int y, int w, int h) const {
    int ow = 60;
    int oh = 9;
    std::vector<std::string> lines;
    std::string title;
    if (overlay_ == Overlay::Help) {
        title = "HOW IT WORKS";
        lines = {
            "Every action takes one hour. Hunger, fatigue and boredom",
            "rise each hour; at 75 or more they hurt health and mood.",
            "",
            "Nights (22:00 to 06:00) tire your pet faster, but resting",
            "at night restores more. Overfeeding a full pet backfires.",
            "",
            "Low discipline means your pet may ignore play and training.",
            "Abilities build discipline. Happy, cared-for hours build bond.",
            "",
            "Your pet grows: Hatchling, then Juvenile at 24h, Adult at 72h.",
            "",
            "Press any key to close.",
        };
        ow = 66;
    } else if (overlay_ == Overlay::Save) {
        title = "SAVE";
        lines = {"Save as:", "", "", "", "Enter to save · Esc to cancel"};
    } else {
        std::string upper;
        for (char c : session_->pet().name()) {
            upper += static_cast<char>(c >= 'a' && c <= 'z' ? c - 'a' + 'A' : c);
        }
        title = "LEAVE " + upper + "?";
        lines = {"Save before you go?", "", "Y  Save to " + defaultSavePath() + " and leave",
                 "N  Leave without saving", "Esc  Stay"};
    }
    oh = static_cast<int>(lines.size()) + 4;
    const int ox = x + (w - ow) / 2;
    const int oy = y + (h - oh) / 2;
    canvas.fill(ox, oy, ow, oh, style(cream, background));
    canvas.fill(ox + 1, oy + 1, ow - 2, oh - 2, style(cream, panel));
    canvas.box(ox, oy, ow, oh, style(pink, background, true), title, style(pink, background, true));
    for (std::size_t i = 0; i < lines.size(); ++i) {
        canvas.text(ox + 3, oy + 2 + static_cast<int>(i), lines[i], style(i + 1 == lines.size() ? muted : cream, panel));
    }
    if (overlay_ == Overlay::Save) {
        canvas.box(ox + 3, oy + 3, ow - 6, 3, style(pink, panel));
        const bool cursorOn = (frame_ / 6) % 2 == 0;
        canvas.text(ox + 5, oy + 4, truncate(input_, static_cast<std::size_t>(ow - 12)) + (cursorOn ? "▌" : " "),
                    style(cream, panel, true));
    }
    if (!error_.empty() && overlay_ != Overlay::Help) {
        canvas.text(ox + 3, oy + oh - 1, " " + error_ + " ", style(red, background, true));
    }
}

}  // namespace vpet
