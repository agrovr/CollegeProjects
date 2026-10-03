#include "ui/App.h"

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <utility>

namespace kms {

namespace {

constexpr int frameMs = 100;
constexpr int minColumns = 96;
constexpr int minRows = 26;

// --- Palette: brushed steel, safety red, brass-amber tags -------------------------------------

constexpr Color background{20, 23, 28};
constexpr Color panel{30, 34, 41};
constexpr Color line{60, 66, 77};
constexpr Color cream{232, 235, 239};
constexpr Color muted{139, 148, 158};
constexpr Color faint{86, 94, 106};
constexpr Color red{224, 49, 56};
constexpr Color amber{242, 183, 5};
constexpr Color steel{190, 198, 207};
constexpr Color green{70, 192, 98};
constexpr Color track{44, 49, 58};
constexpr Color ink{20, 23, 28};

Style style(Color fg, Color bg = background, bool bold = false) {
    Style s;
    s.fg = fg;
    s.bg = bg;
    s.bold = bold;
    return s;
}

std::string upper(const std::string& text) {
    std::string out = text;
    for (char& c : out) {
        c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    }
    return out;
}

bool containsInsensitive(const std::string& haystack, const std::string& needle) {
    if (needle.empty()) {
        return true;
    }
    return upper(haystack).find(upper(needle)) != std::string::npos;
}

std::string fit(const std::string& text, std::size_t width) {
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

std::string pad(const std::string& text, std::size_t width) {
    std::string out = fit(text, width);
    const std::size_t length = utf8Length(out);
    return length < width ? out + std::string(width - length, ' ') : out;
}

int centerX(int x, int width, std::size_t length) {
    return x + (width - static_cast<int>(length)) / 2;
}

const std::vector<std::string> keyArt = {
    R"(    .--.                         )",
    R"(   /.-. '----------------------. )",
    R"(   \'-' .--"--""--"--"-""--"-"' )",
    R"(    '--'                         )",
};

const std::vector<std::string> logo = {
    R"(██   ██ ███████ ██    ██     ██████  ███████  ██████  ██ ███████ ████████ ██████  ██    ██)",
    R"(██  ██  ██       ██  ██      ██   ██ ██      ██       ██ ██         ██    ██   ██  ██  ██ )",
    R"(█████   █████     ████       ██████  █████   ██   ███ ██ ███████    ██    ██████    ████  )",
    R"(██  ██  ██         ██        ██   ██ ██      ██    ██ ██      ██    ██    ██   ██    ██   )",
    R"(██   ██ ███████    ██        ██   ██ ███████  ██████  ██ ███████    ██    ██   ██    ██   )",
};

}  // namespace

App::App(Terminal& terminal, bool color) : terminal_(terminal), color_(color) {
    refreshFiles();
}

void App::open(Registry registry, const std::string& path, Format format) {
    registry_ = std::move(registry);
    path_ = path;
    format_ = format;
    employeeIndex_ = 0;
    keyIndex_ = 0;
    filter_.clear();
    screen_ = Screen::Dashboard;
}

int App::run() {
    while (running_) {
        int columns = 0;
        int rows = 0;
        terminal_.size(columns, rows);
        Canvas canvas(columns, rows, style(cream));
        draw(canvas);
        terminal_.write(canvas.render(color_));
        const KeyPress key = terminal_.readKey(frameMs);
        if (key.type != KeyType::None) {
            handle(key);
        }
        ++frame_;
    }
    return 0;
}

// --- Data helpers ----------------------------------------------------------------------------------

std::vector<const Employee*> App::visibleEmployees() const {
    std::vector<const Employee*> list;
    for (const Employee& e : registry_.employees()) {
        bool match = containsInsensitive(e.name, filter_);
        for (const std::string& id : e.keys) {
            match = match || containsInsensitive(id, filter_);
        }
        if (match) {
            list.push_back(&e);
        }
    }
    return list;
}

std::vector<const kms::Key*> App::visibleKeys() const {
    std::vector<const kms::Key*> list;
    for (const kms::Key& k : registry_.keys()) {
        if (containsInsensitive(k.id, filter_) || containsInsensitive(k.label, filter_)) {
            list.push_back(&k);
        }
    }
    return list;
}

const Employee* App::selectedEmployee() const {
    const auto list = visibleEmployees();
    if (list.empty()) {
        return nullptr;
    }
    return list[static_cast<std::size_t>(std::clamp(employeeIndex_, 0, static_cast<int>(list.size()) - 1))];
}

const kms::Key* App::selectedKey() const {
    const auto list = visibleKeys();
    if (list.empty()) {
        return nullptr;
    }
    return list[static_cast<std::size_t>(std::clamp(keyIndex_, 0, static_cast<int>(list.size()) - 1))];
}

std::vector<App::Choice> App::dialogChoices() const {
    std::vector<Choice> choices;
    const Employee* employee = selectedEmployee();
    const kms::Key* key = selectedKey();
    if (dialog_ == Dialog::Issue && focus_ == Focus::Employees && employee) {
        for (const kms::Key& k : registry_.keys()) {
            if (std::find(employee->keys.begin(), employee->keys.end(), k.id) != employee->keys.end()) {
                continue;
            }
            if (!containsInsensitive(k.id, field1_) && !containsInsensitive(k.label, field1_)) {
                continue;
            }
            const auto holders = registry_.holders(k.id);
            choices.push_back(Choice{k.id, (k.label.empty() ? "" : k.label + " · ") +
                                               (holders.empty() ? "on hook" : std::to_string(holders.size()) + " out"),
                                     true});
        }
    } else if (dialog_ == Dialog::Issue && key) {
        for (const Employee& e : registry_.employees()) {
            if (std::find(e.keys.begin(), e.keys.end(), key->id) != e.keys.end() || !containsInsensitive(e.name, field1_)) {
                continue;
            }
            const bool full = e.keys.size() >= Registry::maxKeysPerEmployee;
            choices.push_back(Choice{e.name, std::to_string(e.keys.size()) + " of 5 keys" + (full ? " · full" : ""), !full});
        }
    } else if (dialog_ == Dialog::Return && focus_ == Focus::Employees && employee) {
        for (const std::string& id : employee->keys) {
            const kms::Key* k = registry_.findKey(id);
            choices.push_back(Choice{id, k ? k->label : "", true});
        }
    } else if (dialog_ == Dialog::Return && key) {
        for (const std::string& name : registry_.holders(key->id)) {
            choices.push_back(Choice{name, "", true});
        }
    }
    return choices;
}

void App::refreshFiles() {
    files_.clear();
    std::error_code ec;
    for (const auto& entry : std::filesystem::directory_iterator(".", ec)) {
        const std::string extension = entry.path().extension().string();
        if (entry.is_regular_file() && (extension == ".txt" || extension == ".reg" || extension == ".keys")) {
            files_.push_back(entry.path().filename().string());
        }
    }
    std::sort(files_.begin(), files_.end());
    if (files_.size() > 8) {
        files_.resize(8);
    }
}

void App::openPath(const std::string& path) {
    Registry registry;
    const ReadResult result = loadRegistry(path, registry);
    if (!result.ok) {
        openError_ = result.error;
        return;
    }
    open(std::move(registry), path, result.format);
    toast("Opened " + path + " (" + (result.format == Format::V2 ? "version 2" : "classic") + " format).");
}

void App::toast(const std::string& message, bool good) {
    toast_ = message;
    toastGood_ = good;
    toastUntil_ = frame_ + 40;
}

// --- Input -----------------------------------------------------------------------------------------

void App::handle(const KeyPress& key) {
    if (dialog_ != Dialog::None) {
        handleDialog(key);
        return;
    }
    switch (screen_) {
        case Screen::Open: handleOpen(key); break;
        case Screen::Dashboard: handleDashboard(key); break;
        case Screen::History: handleHistory(key); break;
    }
}

bool App::editText(std::string& text, const KeyPress& key, std::size_t limit) {
    if (key.type == KeyType::Backspace) {
        if (!text.empty()) {
            text.pop_back();
        }
        return true;
    }
    if (key.type == KeyType::Char && text.size() < limit) {
        text += key.ch;
        return true;
    }
    return false;
}

void App::handleOpen(const KeyPress& key) {
    const int count = static_cast<int>(files_.size()) + 2;  // files, "new registry", path input
    const int newIndex = static_cast<int>(files_.size());
    const int pathIndex = newIndex + 1;
    if (key.type == KeyType::Up) {
        openIndex_ = (openIndex_ + count - 1) % count;
        openError_.clear();
    } else if (key.type == KeyType::Down || key.type == KeyType::Tab) {
        openIndex_ = (openIndex_ + 1) % count;
        openError_.clear();
    } else if (key.type == KeyType::Escape || (openIndex_ != pathIndex && key.is('q'))) {
        running_ = false;
    } else if (openIndex_ == pathIndex && editText(openPathInput_, key, 200)) {
        openError_.clear();
    } else if (key.type == KeyType::Enter) {
        if (openIndex_ < newIndex) {
            openPath(files_[static_cast<std::size_t>(openIndex_)]);
        } else if (openIndex_ == newIndex) {
            open(Registry(), "registry.txt", Format::V2);
            toast("New registry. Add employees with A and keys with K.");
        } else if (!openPathInput_.empty()) {
            openPath(openPathInput_);
        }
    }
}

void App::handleDashboard(const KeyPress& key) {
    const int employees = static_cast<int>(visibleEmployees().size());
    const int keys = static_cast<int>(visibleKeys().size());

    if (searching_) {
        if (key.type == KeyType::Escape) {
            searching_ = false;
            filter_.clear();
        } else if (key.type == KeyType::Enter) {
            searching_ = false;
        } else if (editText(filter_, key, 24)) {
            employeeIndex_ = 0;
            keyIndex_ = 0;
        } else if (key.type == KeyType::Tab) {
            focus_ = focus_ == Focus::Employees ? Focus::Cabinet : Focus::Employees;
        }
        return;
    }

    if (key.type == KeyType::Tab) {
        focus_ = focus_ == Focus::Employees ? Focus::Cabinet : Focus::Employees;
    } else if (key.type == KeyType::Up || key.type == KeyType::Down || key.type == KeyType::Left || key.type == KeyType::Right) {
        if (focus_ == Focus::Employees) {
            if (key.type == KeyType::Right) {
                focus_ = Focus::Cabinet;
            } else if (key.type != KeyType::Left && employees > 0) {
                employeeIndex_ = (employeeIndex_ + (key.type == KeyType::Up ? employees - 1 : 1)) % employees;
            }
        } else if (keys > 0) {
            const int columns = 5;  // matches the cabinet grid
            if (key.type == KeyType::Left) {
                if (keyIndex_ % columns == 0) {
                    focus_ = Focus::Employees;
                } else {
                    --keyIndex_;
                }
            } else if (key.type == KeyType::Right) {
                keyIndex_ = std::min(keys - 1, keyIndex_ + 1);
            } else if (key.type == KeyType::Up) {
                keyIndex_ = std::max(0, keyIndex_ - columns);
            } else {
                keyIndex_ = std::min(keys - 1, keyIndex_ + columns);
            }
        }
    } else if (key.is('/')) {
        searching_ = true;
    } else if (key.type == KeyType::Escape && !filter_.empty()) {
        filter_.clear();
    } else if (key.is('i')) {
        openDialog(Dialog::Issue);
    } else if (key.is('r')) {
        openDialog(Dialog::Return);
    } else if (key.is('a')) {
        openDialog(Dialog::AddEmployee);
    } else if (key.is('d')) {
        openDialog(Dialog::RemoveEmployee);
    } else if (key.is('k')) {
        openDialog(Dialog::AddKey);
    } else if (key.is('l')) {
        openDialog(Dialog::Label);
    } else if (key.is('s')) {
        openDialog(Dialog::Save);
    } else if (key.is('x')) {
        openDialog(Dialog::Export);
    } else if (key.is('h')) {
        historyOffset_ = 0;
        screen_ = Screen::History;
    } else if (key.is('?')) {
        openDialog(Dialog::Help);
    } else if (key.is('q') || key.type == KeyType::Escape) {
        if (registry_.changed()) {
            openDialog(Dialog::Quit);
        } else {
            running_ = false;
        }
    }
}

void App::handleHistory(const KeyPress& key) {
    const int total = static_cast<int>(registry_.history().size());
    if (key.type == KeyType::Up) {
        historyOffset_ = std::min(std::max(0, total - 1), historyOffset_ + 1);
    } else if (key.type == KeyType::Down) {
        historyOffset_ = std::max(0, historyOffset_ - 1);
    } else if (key.type == KeyType::Escape || key.is('h') || key.is('q')) {
        screen_ = Screen::Dashboard;
    }
}

void App::openDialog(Dialog dialog) {
    dialogError_.clear();
    field1_.clear();
    field2_.clear();
    fieldIndex_ = 0;
    choiceIndex_ = 0;
    const Employee* employee = selectedEmployee();
    const kms::Key* key = selectedKey();
    const bool onEmployee = focus_ == Focus::Employees;

    if ((dialog == Dialog::Issue || dialog == Dialog::Return) && (onEmployee ? !employee : !key)) {
        toast(onEmployee ? "Select an employee first." : "Select a key first.", false);
        return;
    }
    if (dialog == Dialog::RemoveEmployee && !employee) {
        toast("Select an employee first.", false);
        return;
    }
    if (dialog == Dialog::Label) {
        if (!key) {
            toast("Select a key in the cabinet first.", false);
            return;
        }
        field1_ = key->label;
    }
    if (dialog == Dialog::Save) {
        field1_ = path_.empty() ? "registry.txt" : path_;
        saveFormat_ = format_;
    }
    if (dialog == Dialog::Export) {
        const std::string base = path_.empty() ? "registry" : std::filesystem::path(path_).stem().string();
        field1_ = base + ".csv";
    }
    dialog_ = dialog;
}

void App::confirmDialog() {
    std::string error;
    const Employee* employee = selectedEmployee();
    const kms::Key* key = selectedKey();
    switch (dialog_) {
        case Dialog::Issue:
        case Dialog::Return: {
            const auto choices = dialogChoices();
            std::string pick;
            if (!choices.empty()) {
                const Choice& choice = choices[static_cast<std::size_t>(std::clamp(choiceIndex_, 0, static_cast<int>(choices.size()) - 1))];
                if (!choice.enabled) {
                    dialogError_ = choice.value + " already holds five keys.";
                    return;
                }
                pick = choice.value;
            } else if (dialog_ == Dialog::Issue && focus_ == Focus::Employees && !field1_.empty()) {
                pick = field1_;  // a new key identifier
            } else {
                dialogError_ = "Nothing to choose.";
                return;
            }
            const std::string name = focus_ == Focus::Employees ? employee->name : pick;
            const std::string id = focus_ == Focus::Employees ? pick : key->id;
            const bool ok = dialog_ == Dialog::Issue ? registry_.issue(name, id, error) : registry_.giveBack(name, id, error);
            if (!ok) {
                dialogError_ = error;
                return;
            }
            toast(dialog_ == Dialog::Issue ? id + " issued to " + name + "." : id + " returned by " + name + ".");
            break;
        }
        case Dialog::AddEmployee:
            if (!registry_.addEmployee(field1_, error)) {
                dialogError_ = error;
                return;
            }
            filter_.clear();
            focus_ = Focus::Employees;
            employeeIndex_ = static_cast<int>(registry_.employees().size()) - 1;
            toast("Added " + field1_ + ".");
            break;
        case Dialog::RemoveEmployee: {
            const std::string name = employee->name;
            if (!registry_.removeEmployee(name, error)) {
                dialogError_ = error;
                return;
            }
            employeeIndex_ = std::max(0, employeeIndex_ - 1);
            toast("Removed " + name + ".");
            break;
        }
        case Dialog::AddKey:
            if (!registry_.addKey(field1_, field2_, error)) {
                dialogError_ = error;
                return;
            }
            filter_.clear();
            focus_ = Focus::Cabinet;
            keyIndex_ = static_cast<int>(registry_.keys().size()) - 1;
            toast(field1_ + " added to the cabinet.");
            break;
        case Dialog::Label:
            if (!registry_.setLabel(key->id, field1_, error)) {
                dialogError_ = error;
                return;
            }
            toast(key->id + (field1_.empty() ? " label cleared." : " now opens " + field1_ + "."));
            break;
        case Dialog::Save:
            if (field1_.empty()) {
                dialogError_ = "Enter a file name.";
                return;
            }
            if (!saveRegistry(field1_, registry_, saveFormat_, error)) {
                dialogError_ = error;
                return;
            }
            registry_.markSaved();
            path_ = field1_;
            format_ = saveFormat_;
            toast("Saved to " + path_ + ".");
            refreshFiles();
            break;
        case Dialog::Export: {
            std::ofstream output(field1_);
            output << toCsv(registry_);
            if (!output) {
                dialogError_ = "Unable to write " + field1_ + ".";
                return;
            }
            toast("Exported " + field1_ + ".");
            break;
        }
        case Dialog::Quit:
        case Dialog::Help:
        case Dialog::None:
            break;
    }
    dialog_ = Dialog::None;
}

void App::handleDialog(const KeyPress& key) {
    if (dialog_ == Dialog::Help) {
        dialog_ = Dialog::None;
        return;
    }
    if (dialog_ == Dialog::Quit) {
        if (key.is('y')) {
            std::string error;
            const std::string path = path_.empty() ? "registry.txt" : path_;
            if (saveRegistry(path, registry_, format_, error)) {
                running_ = false;
            } else {
                dialogError_ = error;
            }
        } else if (key.is('n')) {
            running_ = false;
        } else if (key.type == KeyType::Escape) {
            dialog_ = Dialog::None;
        }
        return;
    }
    if (dialog_ == Dialog::RemoveEmployee) {
        if (key.is('y') || key.type == KeyType::Enter) {
            confirmDialog();
        } else if (key.is('n') || key.type == KeyType::Escape) {
            dialog_ = Dialog::None;
        }
        return;
    }
    if (key.type == KeyType::Escape) {
        dialog_ = Dialog::None;
        return;
    }
    if (key.type == KeyType::Enter) {
        confirmDialog();
        return;
    }
    if (dialog_ == Dialog::Issue || dialog_ == Dialog::Return) {
        const int count = static_cast<int>(dialogChoices().size());
        if (key.type == KeyType::Up && count > 0) {
            choiceIndex_ = (choiceIndex_ + count - 1) % count;
        } else if (key.type == KeyType::Down && count > 0) {
            choiceIndex_ = (choiceIndex_ + 1) % count;
        } else if (editText(field1_, key, 24)) {
            choiceIndex_ = 0;
            dialogError_.clear();
        }
        return;
    }
    if (dialog_ == Dialog::Save && (key.type == KeyType::Tab || key.type == KeyType::Left || key.type == KeyType::Right)) {
        saveFormat_ = saveFormat_ == Format::V2 ? Format::Classic : Format::V2;
        return;
    }
    if (dialog_ == Dialog::AddKey && key.type == KeyType::Tab) {
        fieldIndex_ = 1 - fieldIndex_;
        return;
    }
    std::string& field = (dialog_ == Dialog::AddKey && fieldIndex_ == 1) ? field2_ : field1_;
    const std::size_t limit = dialog_ == Dialog::AddEmployee ? Registry::maxNameLength
                            : dialog_ == Dialog::AddKey && fieldIndex_ == 0 ? Registry::maxKeyLength
                            : dialog_ == Dialog::Save || dialog_ == Dialog::Export ? 200
                            : Registry::maxLabelLength;
    if (dialog_ == Dialog::AddKey && fieldIndex_ == 0 && key.type == KeyType::Char) {
        KeyPress upperKey = key;
        upperKey.ch = static_cast<char>(std::toupper(static_cast<unsigned char>(key.ch)));
        if (editText(field, upperKey, limit)) {
            dialogError_.clear();
        }
        return;
    }
    if (dialog_ == Dialog::AddEmployee && key.type == KeyType::Char) {
        // Capitalise the start of each word.
        KeyPress named = key;
        if (field.empty() || field.back() == ' ' || field.back() == '-') {
            named.ch = static_cast<char>(std::toupper(static_cast<unsigned char>(key.ch)));
        }
        if (editText(field, named, limit)) {
            dialogError_.clear();
        }
        return;
    }
    if (editText(field, key, limit)) {
        dialogError_.clear();
    }
}

// --- Drawing ---------------------------------------------------------------------------------------

void App::draw(Canvas& canvas) const {
    const int columns = canvas.columns();
    const int rows = canvas.rows();
    if (columns < minColumns || rows < minRows) {
        char message[96];
        std::snprintf(message, sizeof(message), "Make the window at least %d x %d (now %d x %d).", minColumns, minRows,
                      columns, rows);
        canvas.text(std::max(0, (columns - static_cast<int>(utf8Length(message))) / 2), rows / 2, message, style(amber));
        return;
    }
    const int w = std::min(columns, 116);
    const int h = std::min(rows, 34);
    const int x = (columns - w) / 2;
    const int y = (rows - h) / 2;
    switch (screen_) {
        case Screen::Open: drawOpen(canvas, x, y, w, h); break;
        case Screen::Dashboard: drawDashboard(canvas, x, y, w, h); break;
        case Screen::History: drawHistory(canvas, x, y, w, h); break;
    }
    if (dialog_ != Dialog::None) {
        drawDialog(canvas, x, y, w, h);
    }
}

void App::drawFooter(Canvas& canvas, int x, int y, int w,
                     const std::vector<std::pair<std::string, std::string>>& keys) const {
    int cx = x;
    for (const auto& [key, label] : keys) {
        const int width = static_cast<int>(utf8Length(key) + utf8Length(label)) + 3;
        if (cx + width > x + w) {
            break;
        }
        canvas.text(cx, y, " " + key + " ", style(cream, red, true));
        canvas.text(cx + static_cast<int>(utf8Length(key)) + 2, y, " " + label, style(muted));
        cx += width + 1;
    }
}

void App::drawOpen(Canvas& canvas, int x, int y, int w, int h) const {
    canvas.box(x, y, w, h, style(line));
    const bool roomy = h >= 30;
    const int sweep = static_cast<int>(frame_ % 70) - 10;
    int ky = y + 2;
    if (roomy) {
        // The key glints as a highlight sweeps along it.
        const int kx = centerX(x, w, utf8Length(keyArt[1]));
        for (std::size_t row = 0; row < keyArt.size(); ++row) {
            const std::vector<std::string> glyphs = splitUtf8(keyArt[row]);
            for (std::size_t col = 0; col < glyphs.size(); ++col) {
                if (glyphs[col] == " ") {
                    continue;
                }
                const int distance = std::abs(static_cast<int>(col) - sweep);
                const Color c = distance < 3 ? Color{255, 236, 170} : amber;
                canvas.text(kx + static_cast<int>(col), ky + static_cast<int>(row), glyphs[col], style(c, background, true));
            }
        }
        ky += 6;
    }
    // Brushed-metal wordmark: lighter at the top, with the same glint passing through.
    const int lx0 = centerX(x, w, utf8Length(logo[0]));
    for (std::size_t row = 0; row < logo.size(); ++row) {
        const std::vector<std::string> glyphs = splitUtf8(logo[row]);
        const double t = static_cast<double>(row) / static_cast<double>(logo.size() - 1);
        const Color base{static_cast<std::uint8_t>(238 - 90 * t), static_cast<std::uint8_t>(242 - 86 * t),
                         static_cast<std::uint8_t>(246 - 78 * t)};
        for (std::size_t col = 0; col < glyphs.size(); ++col) {
            if (glyphs[col] == " ") {
                continue;
            }
            const int distance = std::abs(static_cast<int>(col) / 1 - (sweep * 90) / 50 - static_cast<int>(row));
            const Color c = distance < 2 ? Color{255, 255, 255} : base;
            canvas.text(lx0 + static_cast<int>(col), ky + static_cast<int>(row), glyphs[col], style(c, background, true));
        }
    }
    const int ly = ky + 2;
    const std::string tagline = "Who has which key, at a glance.";
    canvas.text(centerX(x, w, tagline.size()), ly + 5, tagline, style(red, background, true));

    const int lx = x + w / 2 - 30;
    int ry = ly + 8;
    canvas.text(lx, ry, files_.empty() ? "No registry files in this folder." : "Open a registry", style(faint, background, true));
    ry += 1;
    for (std::size_t i = 0; i < files_.size(); ++i) {
        const bool selected = static_cast<int>(i) == openIndex_;
        canvas.text(lx, ry, selected ? "▸" : " ", style(red, background, true));
        canvas.text(lx + 2, ry, files_[i], selected ? style(cream, background, true) : style(muted));
        ++ry;
    }
    const bool onNew = openIndex_ == static_cast<int>(files_.size());
    canvas.text(lx, ry + 1, onNew ? "▸" : " ", style(red, background, true));
    canvas.text(lx + 2, ry + 1, "+ New empty registry", onNew ? style(cream, background, true) : style(muted));
    const bool onPath = openIndex_ == static_cast<int>(files_.size()) + 1;
    canvas.text(lx, ry + 3, onPath ? "▸" : " ", style(red, background, true));
    canvas.text(lx + 2, ry + 3, "Path:", onPath ? style(cream, background, true) : style(muted));
    const bool cursorOn = onPath && (frame_ / 5) % 2 == 0;
    canvas.text(lx + 8, ry + 3, pad(openPathInput_ + (cursorOn ? "▌" : ""), 50), style(cream, panel));
    if (!openError_.empty()) {
        canvas.text(lx, ry + 5, fit(openError_, 60), style(red, background, true));
    }
    drawFooter(canvas, x + 2, y + h - 2, w - 4, {{"↑↓", "Choose"}, {"Enter", "Open"}, {"Esc", "Quit"}});
}

void App::drawDashboard(Canvas& canvas, int x, int y, int w, int h) const {
    canvas.box(x, y, w, h, style(line), "KEY REGISTRY", style(red, background, true));
    std::string file = " " + (path_.empty() ? std::string("unsaved registry") : path_) + " · " +
                       (format_ == Format::V2 ? "v2" : "classic") + " ";
    canvas.text(x + w - 3 - static_cast<int>(utf8Length(file)) - (registry_.changed() ? 11 : 0), y, file, style(muted));
    if (registry_.changed()) {
        canvas.text(x + w - 14, y, " ● unsaved ", style(amber, background, true));
    }

    // Stat tiles.
    struct Tile {
        std::string label;
        std::size_t value;
        Color color;
    };
    const Tile tiles[] = {
        {"EMPLOYEES", registry_.employees().size(), cream},
        {"KEYS IN CABINET", registry_.keys().size(), steel},
        {"OUT NOW", registry_.issuedCount(), amber},
        {"ON THE HOOK", registry_.onHookCount(), green},
    };
    const int tileW = (w - 4 - 3 * 2) / 4;
    for (int i = 0; i < 4; ++i) {
        const int tx = x + 2 + i * (tileW + 2);
        canvas.fill(tx, y + 2, tileW, 3, style(cream, panel));
        canvas.text(tx, y + 2, "▎", style(tiles[i].color, panel));
        canvas.text(tx, y + 3, "▎", style(tiles[i].color, panel));
        canvas.text(tx, y + 4, "▎", style(tiles[i].color, panel));
        canvas.text(tx + 2, y + 2, tiles[i].label, style(muted, panel));
        canvas.text(tx + 2, y + 3, std::to_string(tiles[i].value), style(tiles[i].color, panel, true));
    }

    const int footerY = y + h - 2;
    const int bottomH = 8;
    const int bottomY = footerY - bottomH - 1;
    const int leftW = 40;
    const int top = y + 6;
    drawEmployees(canvas, x + 2, top, leftW, bottomY - top);
    drawCabinet(canvas, x + 2 + leftW + 1, top, w - 5 - leftW, bottomY - top);
    drawDetails(canvas, x + 2, bottomY, leftW, bottomH + 1);
    drawActivity(canvas, x + 2 + leftW + 1, bottomY, w - 5 - leftW, bottomH + 1);

    if (searching_ || !filter_.empty()) {
        const bool cursorOn = searching_ && (frame_ / 5) % 2 == 0;
        canvas.text(x + 2, footerY, " / ", style(ink, amber, true));
        canvas.text(x + 6, footerY, pad(filter_ + (cursorOn ? "▌" : ""), 26), style(cream, panel));
        canvas.text(x + 34, footerY, searching_ ? "Enter keep · Esc clear" : "Esc clears the filter", style(faint));
    } else {
        drawFooter(canvas, x + 2, footerY, w - 4,
                   {{"I", "Issue"}, {"R", "Return"}, {"A", "Employee"}, {"K", "Key"}, {"L", "Label"},
                    {"/", "Find"}, {"H", "History"}, {"S", "Save"}, {"?", "Help"}, {"Q", "Quit"}});
    }
    if (frame_ < toastUntil_ && !toast_.empty()) {
        const std::string text = " " + std::string(toastGood_ ? "✓ " : "! ") + toast_ + " ";
        canvas.text(x + w - 2 - static_cast<int>(utf8Length(text)), bottomY - 1, text,
                    style(ink, toastGood_ ? green : red, true));
    }
}

void App::drawEmployees(Canvas& canvas, int x, int y, int w, int h) const {
    const bool focused = focus_ == Focus::Employees;
    canvas.box(x, y, w, h, style(focused ? red : line), "EMPLOYEES", style(focused ? cream : muted, background, true));
    const auto list = visibleEmployees();
    const int rows = h - 2;
    const int selected = list.empty() ? -1 : std::clamp(employeeIndex_, 0, static_cast<int>(list.size()) - 1);
    const int first = std::max(0, std::min(selected - rows / 2, static_cast<int>(list.size()) - rows));
    if (list.empty()) {
        canvas.text(x + 2, y + 1, filter_.empty() ? "No employees yet. Press A." : "No matches.", style(faint));
    }
    for (int row = 0; row < rows && first + row < static_cast<int>(list.size()); ++row) {
        const int index = first + row;
        const Employee& e = *list[static_cast<std::size_t>(index)];
        const bool isSelected = index == selected;
        const Color bg = isSelected ? (focused ? Color{58, 30, 34} : panel) : background;
        canvas.fill(x + 1, y + 1 + row, w - 2, 1, style(cream, bg));
        canvas.text(x + 2, y + 1 + row, isSelected ? "▸" : " ", style(red, bg, true));
        canvas.text(x + 4, y + 1 + row, pad(e.name, static_cast<std::size_t>(w - 18)), style(isSelected ? cream : muted, bg, isSelected));
        // Five key slots.
        for (std::size_t slot = 0; slot < Registry::maxKeysPerEmployee; ++slot) {
            const bool used = slot < e.keys.size();
            canvas.text(x + w - 13 + static_cast<int>(slot) * 2, y + 1 + row, used ? "■" : "□", style(used ? amber : faint, bg));
        }
    }
    if (static_cast<int>(list.size()) > rows) {
        canvas.text(x + w - 8, y + h - 1, " " + std::to_string(selected + 1) + "/" + std::to_string(list.size()) + " ", style(faint));
    }
}

void App::drawCabinet(Canvas& canvas, int x, int y, int w, int h) const {
    const bool focused = focus_ == Focus::Cabinet;
    canvas.box(x, y, w, h, style(focused ? red : line), "CABINET", style(focused ? cream : muted, background, true));
    canvas.fill(x + 1, y + 1, w - 2, h - 2, style(cream, panel));
    const auto list = visibleKeys();
    if (list.empty()) {
        canvas.text(x + 3, y + 2, filter_.empty() ? "The cabinet is empty. Press K to add a key." : "No matching keys.",
                    style(faint, panel));
        return;
    }
    const int columns = 5;
    const int cellW = std::max(12, (w - 4) / columns);
    const int cellH = 4;
    const int visibleRows = std::max(1, (h - 2) / cellH);
    const int selected = std::clamp(keyIndex_, 0, static_cast<int>(list.size()) - 1);
    const int selectedRow = selected / columns;
    const int firstRow = std::max(0, selectedRow - visibleRows + 1);
    const Employee* employee = selectedEmployee();

    for (int i = firstRow * columns; i < static_cast<int>(list.size()) && i < (firstRow + visibleRows) * columns; ++i) {
        const kms::Key& k = *list[static_cast<std::size_t>(i)];
        const int cx = x + 2 + (i % columns) * cellW;
        const int cy = y + 1 + (i / columns - firstRow) * cellH;
        const auto holders = registry_.holders(k.id);
        const bool out = !holders.empty();
        const bool isSelected = focused && i == selected;
        const bool heldBySelected = !focused && employee &&
            std::find(employee->keys.begin(), employee->keys.end(), k.id) != employee->keys.end();
        const int tagW = cellW - 2;

        // Hook and ring.
        canvas.text(cx + tagW / 2, cy, "○", style(isSelected || heldBySelected ? cream : faint, panel));
        // The tag itself.
        const Color tagColor = isSelected ? red : out ? amber : steel;
        const Color textColor = isSelected ? cream : ink;
        std::string id = fit(k.id, static_cast<std::size_t>(tagW - 2));
        const int padLeft = (tagW - static_cast<int>(utf8Length(id))) / 2;
        canvas.fill(cx, cy + 1, tagW, 1, style(textColor, tagColor));
        canvas.text(cx + padLeft, cy + 1, id, style(textColor, tagColor, true));
        if (heldBySelected) {
            canvas.text(cx - 1, cy + 1, "▸", style(cream, panel, true));
        }
        // Label or status underneath.
        const std::string under = !k.label.empty() ? k.label : out ? std::to_string(holders.size()) + " out" : "on hook";
        canvas.text(cx, cy + 2, pad(fit(under, static_cast<std::size_t>(tagW)), static_cast<std::size_t>(tagW)),
                    style(out ? Color{214, 172, 64} : muted, panel));
    }
    const int totalRows = (static_cast<int>(list.size()) + columns - 1) / columns;
    if (totalRows > visibleRows) {
        canvas.text(x + w - 12, y + h - 1, " " + std::to_string(selected + 1) + "/" + std::to_string(list.size()) + " ", style(faint));
    }
}

void App::drawDetails(Canvas& canvas, int x, int y, int w, int h) const {
    canvas.box(x, y, w, h, style(line), "DETAILS", style(muted, background, true));
    const int tx = x + 2;
    int ty = y + 1;
    const std::size_t width = static_cast<std::size_t>(w - 4);
    if (focus_ == Focus::Employees) {
        const Employee* e = selectedEmployee();
        if (!e) {
            canvas.text(tx, ty, "Select an employee.", style(faint));
            return;
        }
        canvas.text(tx, ty, fit(upper(e->name), width), style(cream, background, true));
        canvas.text(tx, ty + 1, std::to_string(e->keys.size()) + " of 5 keys", style(muted));
        ty += 2;
        if (e->keys.empty()) {
            canvas.text(tx, ty, "Holds no keys.", style(faint));
        }
        for (const std::string& id : e->keys) {
            if (ty >= y + h - 1) {
                break;
            }
            const kms::Key* k = registry_.findKey(id);
            canvas.text(tx, ty, "■", style(amber));
            canvas.text(tx + 2, ty, pad(id, 9), style(cream, background, true));
            canvas.text(tx + 11, ty, fit(k && !k->label.empty() ? k->label : "", width - 11), style(muted));
            ++ty;
        }
    } else {
        const kms::Key* k = selectedKey();
        if (!k) {
            canvas.text(tx, ty, "Select a key.", style(faint));
            return;
        }
        canvas.text(tx, ty, k->id, style(cream, background, true));
        canvas.text(tx + static_cast<int>(k->id.size()) + 1, ty, fit(k->label.empty() ? "· no label (L)" : "· " + k->label, width - k->id.size() - 1),
                    style(muted));
        const auto holders = registry_.holders(k->id);
        canvas.text(tx, ty + 1, holders.empty() ? "On the hook" : "Held by " + std::to_string(holders.size()),
                    style(holders.empty() ? green : amber, background, true));
        ty += 2;
        for (const std::string& name : holders) {
            if (ty >= y + h - 1) {
                break;
            }
            canvas.text(tx, ty, "• " + fit(name, width - 2), style(cream));
            ++ty;
        }
    }
}

void App::drawActivity(Canvas& canvas, int x, int y, int w, int h) const {
    canvas.box(x, y, w, h, style(line), "ACTIVITY", style(muted, background, true));
    const auto& history = registry_.history();
    if (history.empty()) {
        canvas.text(x + 2, y + 1, "Changes you make appear here, with the time.", style(faint));
        return;
    }
    const int rows = h - 2;
    const int start = std::max(0, static_cast<int>(history.size()) - rows);
    for (int i = start; i < static_cast<int>(history.size()); ++i) {
        const Event& event = history[static_cast<std::size_t>(i)];
        const int ry = y + 1 + (i - start);
        std::string icon = "•";
        Color color = muted;
        std::string text;
        switch (event.kind) {
            case EventKind::Issue: icon = "→"; color = amber; text = event.key + " issued to " + event.employee; break;
            case EventKind::Return: icon = "←"; color = green; text = event.key + " returned by " + event.employee; break;
            case EventKind::AddEmployee: icon = "+"; color = cream; text = event.employee + " added"; break;
            case EventKind::RemoveEmployee: icon = "−"; color = red; text = event.employee + " removed"; break;
            case EventKind::AddKey: icon = "+"; color = steel; text = event.key + " added to the cabinet"; break;
            case EventKind::LabelKey: icon = "✎"; color = steel; text = event.key + " relabelled"; break;
        }
        const bool newest = i == static_cast<int>(history.size()) - 1;
        canvas.text(x + 2, ry, event.when.size() > 11 ? event.when.substr(11) : event.when, style(faint));
        canvas.text(x + 8, ry, icon, style(color, background, true));
        canvas.text(x + 10, ry, fit(text, static_cast<std::size_t>(w - 12)), style(newest ? cream : muted, background, newest));
    }
}

void App::drawHistory(Canvas& canvas, int x, int y, int w, int h) const {
    canvas.box(x, y, w, h, style(line), "HISTORY", style(red, background, true));
    const auto& history = registry_.history();
    const int rows = h - 5;
    canvas.text(x + 3, y + 2, pad("WHEN", 18) + pad("EVENT", 17) + pad("EMPLOYEE", 26) + "KEY", style(faint, background, true));
    if (history.empty()) {
        canvas.text(x + 3, y + 3, "No history yet. Changes made here are recorded and saved in version 2 files.", style(faint));
    }
    const int end = static_cast<int>(history.size()) - historyOffset_;
    const int start = std::max(0, end - rows);
    for (int i = start; i < end; ++i) {
        const Event& event = history[static_cast<std::size_t>(i)];
        const int ry = y + 3 + (i - start);
        const Color color = event.kind == EventKind::Issue ? amber : event.kind == EventKind::Return ? green
                          : event.kind == EventKind::RemoveEmployee ? red : steel;
        canvas.text(x + 3, ry, pad(event.when, 18), style(muted));
        canvas.text(x + 21, ry, pad(eventName(event.kind), 17), style(color, background, true));
        canvas.text(x + 38, ry, pad(event.employee, 26), style(cream));
        canvas.text(x + 64, ry, event.key, style(cream, background, true));
    }
    drawFooter(canvas, x + 2, y + h - 2, w - 4, {{"↑↓", "Scroll"}, {"Esc", "Back"}});
    const std::string count = std::to_string(history.size()) + " events";
    canvas.text(x + w - 3 - static_cast<int>(count.size()), y + h - 2, count, style(faint));
}

void App::drawDialog(Canvas& canvas, int x, int y, int w, int h) const {
    std::string title;
    std::vector<std::string> lines;
    int ow = 64;
    const Employee* employee = selectedEmployee();
    const kms::Key* key = selectedKey();
    const bool onEmployee = focus_ == Focus::Employees;
    switch (dialog_) {
        case Dialog::Issue:
            title = onEmployee ? "ISSUE A KEY TO " + upper(employee->name) : "ISSUE " + key->id + " TO";
            break;
        case Dialog::Return:
            title = onEmployee ? "RETURN A KEY FROM " + upper(employee->name) : "RETURN " + key->id + " FROM";
            break;
        case Dialog::AddEmployee: title = "ADD AN EMPLOYEE"; lines = {"Name"}; break;
        case Dialog::RemoveEmployee:
            title = "REMOVE EMPLOYEE";
            lines = {"Remove " + employee->name + " from the registry?", "", "Y  Remove      N  Keep"};
            break;
        case Dialog::AddKey: title = "ADD A KEY"; lines = {"Identifier", "", "", "What it opens (optional)"}; break;
        case Dialog::Label: title = "LABEL " + key->id; lines = {"What does it open?"}; break;
        case Dialog::Save: title = "SAVE"; lines = {"File"}; break;
        case Dialog::Export: title = "EXPORT CSV"; lines = {"File"}; break;
        case Dialog::Quit:
            title = "UNSAVED CHANGES";
            lines = {"Save before you go?", "", "Y  Save to " + (path_.empty() ? std::string("registry.txt") : path_),
                     "N  Quit without saving", "Esc  Stay"};
            break;
        case Dialog::Help:
            title = "KEYS";
            ow = 70;
            lines = {"Tab or ←→     move between employees and the cabinet",
                     "↑↓ ←→         choose an employee or a key",
                     "I / R         issue or return, for whatever is selected",
                     "A / D         add or remove an employee (only with no keys)",
                     "K / L         add a key to the cabinet, or label it",
                     "/             filter both lists as you type",
                     "H             full history",
                     "S / X         save (classic or version 2), export CSV",
                     "",
                     "Amber tags are out, steel tags are on the hook. Each employee",
                     "holds up to five keys; several people can hold copies of one key.",
                     "",
                     "Press any key to close."};
            break;
        case Dialog::None: return;
    }

    std::vector<Choice> choices;
    int oh = static_cast<int>(lines.size()) + 4;
    if (dialog_ == Dialog::Issue || dialog_ == Dialog::Return) {
        choices = dialogChoices();
        oh = std::min(h - 4, std::max(10, static_cast<int>(choices.size()) + 7));
    } else if (dialog_ == Dialog::AddEmployee || dialog_ == Dialog::Label || dialog_ == Dialog::Export) {
        oh = 8;
    } else if (dialog_ == Dialog::Save) {
        oh = 11;
    } else if (dialog_ == Dialog::AddKey) {
        oh = 11;
    }
    const int ox = x + (w - ow) / 2;
    const int oy = y + (h - oh) / 2;
    canvas.fill(ox, oy, ow, oh, style(cream, background));
    canvas.fill(ox + 1, oy + 1, ow - 2, oh - 2, style(cream, panel));
    canvas.box(ox, oy, ow, oh, style(red, background, true), fit(title, static_cast<std::size_t>(ow - 6)), style(cream, background, true));
    const int ix = ox + 3;
    const int iw = ow - 6;
    const bool cursorOn = (frame_ / 5) % 2 == 0;
    auto field = [&](int fy, const std::string& value, bool active) {
        canvas.fill(ix, fy, iw, 1, style(cream, active ? Color{48, 54, 64} : track));
        canvas.text(ix + 1, fy, fit(value, static_cast<std::size_t>(iw - 3)) + (active && cursorOn ? "▌" : ""), style(cream, active ? Color{48, 54, 64} : track, true));
    };

    if (dialog_ == Dialog::Issue || dialog_ == Dialog::Return) {
        field(oy + 2, field1_, true);
        if (field1_.empty()) {
            canvas.text(ix + 1, oy + 2, cursorOn ? "▌" : " ", style(cream, Color{48, 54, 64}));
            canvas.text(ix + 3, oy + 2, "type to filter", style(faint, Color{48, 54, 64}));
        }
        const int listTop = oy + 4;
        const int rows = oh - 7;
        const int selected = choices.empty() ? -1 : std::clamp(choiceIndex_, 0, static_cast<int>(choices.size()) - 1);
        const int first = std::max(0, std::min(selected - rows / 2, static_cast<int>(choices.size()) - rows));
        if (choices.empty()) {
            const bool canCreate = dialog_ == Dialog::Issue && onEmployee && !field1_.empty();
            canvas.text(ix, listTop, canCreate ? "Enter issues a new key: " + field1_ : "Nothing to choose here.",
                        style(canCreate ? amber : faint, panel));
        }
        for (int row = 0; row < rows && first + row < static_cast<int>(choices.size()); ++row) {
            const int index = first + row;
            const Choice& c = choices[static_cast<std::size_t>(index)];
            const bool isSelected = index == selected;
            const Color bg = isSelected ? Color{58, 30, 34} : panel;
            canvas.fill(ix, listTop + row, iw, 1, style(cream, bg));
            canvas.text(ix, listTop + row, isSelected ? "▸" : " ", style(red, bg, true));
            canvas.text(ix + 2, listTop + row, pad(c.value, 20), style(c.enabled ? cream : faint, bg, isSelected));
            canvas.text(ix + 23, listTop + row, fit(c.detail, static_cast<std::size_t>(iw - 24)), style(c.enabled ? muted : faint, bg));
        }
        canvas.text(ix, oy + oh - 2, "↑↓ choose · Enter confirm · Esc cancel", style(faint, panel));
    } else if (dialog_ == Dialog::AddEmployee || dialog_ == Dialog::Label || dialog_ == Dialog::Export) {
        canvas.text(ix, oy + 2, lines[0], style(muted, panel));
        field(oy + 3, field1_, true);
        canvas.text(ix, oy + oh - 2, "Enter confirm · Esc cancel", style(faint, panel));
    } else if (dialog_ == Dialog::AddKey) {
        canvas.text(ix, oy + 2, lines[0], style(muted, panel));
        field(oy + 3, field1_, fieldIndex_ == 0);
        canvas.text(ix, oy + 5, lines[3], style(muted, panel));
        field(oy + 6, field2_, fieldIndex_ == 1);
        canvas.text(ix, oy + oh - 2, "Tab next field · Enter add · Esc cancel", style(faint, panel));
    } else if (dialog_ == Dialog::Save) {
        canvas.text(ix, oy + 2, "File", style(muted, panel));
        field(oy + 3, field1_, true);
        canvas.text(ix, oy + 5, "Format", style(muted, panel));
        const bool v2 = saveFormat_ == Format::V2;
        canvas.text(ix + 8, oy + 5, " Version 2 ", v2 ? style(ink, amber, true) : style(muted, track));
        canvas.text(ix + 20, oy + 5, " Classic ", !v2 ? style(ink, amber, true) : style(muted, track));
        const bool losesData = !v2 && (!registry_.history().empty() ||
            std::any_of(registry_.keys().begin(), registry_.keys().end(), [](const kms::Key& k) { return !k.label.empty(); }));
        canvas.text(ix, oy + 7,
                    v2 ? "Keeps labels, unheld keys and the history." :
                    losesData ? "Classic keeps only who holds what. Labels and history are left out." :
                                "The original course format.",
                    style(losesData ? amber : faint, panel));
        canvas.text(ix, oy + oh - 2, "Tab switch format · Enter save · Esc cancel", style(faint, panel));
    } else {
        for (std::size_t i = 0; i < lines.size(); ++i) {
            canvas.text(ix, oy + 2 + static_cast<int>(i), lines[i], style(i + 1 == lines.size() ? faint : cream, panel));
        }
    }
    if (!dialogError_.empty()) {
        canvas.text(ix - 1, oy + oh - 1, " " + fit(dialogError_, static_cast<std::size_t>(ow - 6)) + " ", style(cream, red, true));
    }
}

}  // namespace kms
