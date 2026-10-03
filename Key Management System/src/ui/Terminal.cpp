#include "ui/Terminal.h"

#include <algorithm>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <iostream>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <conio.h>
#include <io.h>
#include <windows.h>
#ifndef ENABLE_VIRTUAL_TERMINAL_PROCESSING
#define ENABLE_VIRTUAL_TERMINAL_PROCESSING 0x0004
#endif
#else
#include <sys/ioctl.h>
#include <sys/select.h>
#include <termios.h>
#include <unistd.h>
#endif

namespace kms {

namespace {

const char* const enterScreen = "\x1b[?1049h\x1b[?25l\x1b[H";
const char* const leaveScreen = "\x1b[0m\x1b[?25h\x1b[?1049l";

#ifdef _WIN32
DWORD savedInputMode = 0;
DWORD savedOutputMode = 0;
UINT savedOutputCodePage = 0;
#else
termios savedTermios{};
#endif
bool active = false;

void restoreTerminal() {
    if (!active) {
        return;
    }
    active = false;
    std::fputs(leaveScreen, stdout);
    std::fflush(stdout);
#ifdef _WIN32
    SetConsoleMode(GetStdHandle(STD_INPUT_HANDLE), savedInputMode);
    SetConsoleMode(GetStdHandle(STD_OUTPUT_HANDLE), savedOutputMode);
    SetConsoleOutputCP(savedOutputCodePage);
#else
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &savedTermios);
#endif
}

void onSignal(int signal) {
    restoreTerminal();
    std::signal(signal, SIG_DFL);
    std::raise(signal);
}

#ifndef _WIN32
int readByte(int timeoutMs) {
    fd_set set;
    FD_ZERO(&set);
    FD_SET(STDIN_FILENO, &set);
    timeval tv{timeoutMs / 1000, (timeoutMs % 1000) * 1000};
    if (select(STDIN_FILENO + 1, &set, nullptr, nullptr, timeoutMs < 0 ? nullptr : &tv) <= 0) {
        return -1;
    }
    unsigned char byte = 0;
    return ::read(STDIN_FILENO, &byte, 1) == 1 ? byte : -1;
}
#endif

KeyPress charKey(int c) {
    KeyPress key;
    if (c == '\r' || c == '\n') {
        key.type = KeyType::Enter;
    } else if (c == 27) {
        key.type = KeyType::Escape;
    } else if (c == 127 || c == 8) {
        key.type = KeyType::Backspace;
    } else if (c == '\t') {
        key.type = KeyType::Tab;
    } else if (c >= 32 && c < 127) {
        key.type = KeyType::Char;
        key.ch = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
    }
    return key;
}

}  // namespace

Terminal::Terminal() {
#ifdef _WIN32
    HANDLE in = GetStdHandle(STD_INPUT_HANDLE);
    HANDLE out = GetStdHandle(STD_OUTPUT_HANDLE);
    GetConsoleMode(in, &savedInputMode);
    GetConsoleMode(out, &savedOutputMode);
    savedOutputCodePage = GetConsoleOutputCP();
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleMode(out, savedOutputMode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
    SetConsoleMode(in, savedInputMode & ~(ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT));
#else
    tcgetattr(STDIN_FILENO, &savedTermios);
    termios raw = savedTermios;
    raw.c_lflag &= static_cast<tcflag_t>(~(ICANON | ECHO));
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
#endif
    active = true;
    std::atexit(restoreTerminal);
    std::signal(SIGINT, onSignal);
    std::signal(SIGTERM, onSignal);
    write(enterScreen);
}

Terminal::~Terminal() {
    restoreTerminal();
}

KeyPress Terminal::readKey(int timeoutMs) {
#ifdef _WIN32
    const DWORD start = GetTickCount();
    while (!_kbhit()) {
        if (static_cast<int>(GetTickCount() - start) >= timeoutMs) {
            return {};
        }
        Sleep(10);
    }
    int c = _getch();
    if (c == 0 || c == 224) {
        KeyPress key;
        switch (_getch()) {
            case 72: key.type = KeyType::Up; break;
            case 80: key.type = KeyType::Down; break;
            case 75: key.type = KeyType::Left; break;
            case 77: key.type = KeyType::Right; break;
            default: break;
        }
        return key;
    }
    return charKey(c);
#else
    const int c = readByte(timeoutMs);
    if (c < 0) {
        return {};
    }
    if (c == 27) {
        // Arrow keys arrive as ESC [ A..D (or ESC O A..D). A lone ESC is the Escape key.
        const int next = readByte(25);
        if (next == '[' || next == 'O') {
            KeyPress key;
            switch (readByte(25)) {
                case 'A': key.type = KeyType::Up; break;
                case 'B': key.type = KeyType::Down; break;
                case 'C': key.type = KeyType::Right; break;
                case 'D': key.type = KeyType::Left; break;
                default: break;
            }
            return key;
        }
        return charKey(27);
    }
    return charKey(c);
#endif
}

void Terminal::size(int& columns, int& rows) const {
    columns = 100;
    rows = 30;
#ifdef _WIN32
    CONSOLE_SCREEN_BUFFER_INFO info;
    if (GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &info)) {
        columns = info.srWindow.Right - info.srWindow.Left + 1;
        rows = info.srWindow.Bottom - info.srWindow.Top + 1;
    }
#else
    winsize ws{};
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == 0 && ws.ws_col > 0) {
        columns = ws.ws_col;
        rows = ws.ws_row;
    }
#endif
}

void Terminal::write(const std::string& bytes) {
    std::fwrite(bytes.data(), 1, bytes.size(), stdout);
    std::fflush(stdout);
}

bool Terminal::interactive() {
#ifdef _WIN32
    return _isatty(_fileno(stdin)) && _isatty(_fileno(stdout));
#else
    return isatty(STDIN_FILENO) && isatty(STDOUT_FILENO);
#endif
}

// --- Canvas --------------------------------------------------------------------------------------

std::vector<std::string> splitUtf8(const std::string& text) {
    std::vector<std::string> glyphs;
    for (std::size_t i = 0; i < text.size();) {
        const unsigned char c = static_cast<unsigned char>(text[i]);
        const std::size_t length = c < 0x80 ? 1 : (c >> 5) == 0x6 ? 2 : (c >> 4) == 0xE ? 3 : 4;
        glyphs.push_back(text.substr(i, length));
        i += length;
    }
    return glyphs;
}

std::size_t utf8Length(const std::string& text) {
    std::size_t count = 0;
    for (const char c : text) {
        if ((static_cast<unsigned char>(c) & 0xC0) != 0x80) {
            ++count;
        }
    }
    return count;
}

Canvas::Canvas(int columns, int rows, const Style& base)
    : cells_(static_cast<std::size_t>(columns * rows), Cell{" ", base}), columns_(columns), rows_(rows) {}

void Canvas::text(int x, int y, const std::string& utf8, const Style& style) {
    if (y < 0 || y >= rows_) {
        return;
    }
    for (const std::string& glyph : splitUtf8(utf8)) {
        if (x >= 0 && x < columns_) {
            cells_[static_cast<std::size_t>(y * columns_ + x)] = Cell{glyph, style};
        }
        ++x;
    }
}

void Canvas::fill(int x, int y, int width, int height, const Style& style) {
    for (int row = y; row < y + height; ++row) {
        text(x, row, std::string(static_cast<std::size_t>(std::max(0, width)), ' '), style);
    }
}

void Canvas::box(int x, int y, int width, int height, const Style& border, const std::string& title) {
    box(x, y, width, height, border, title, border);
}

void Canvas::box(int x, int y, int width, int height, const Style& border, const std::string& title,
                 const Style& titleStyle) {
    if (width < 2 || height < 2) {
        return;
    }
    std::string top = "╭";
    std::string bottom = "╰";
    for (int i = 0; i < width - 2; ++i) {
        top += "─";
        bottom += "─";
    }
    top += "╮";
    bottom += "╯";
    text(x, y, top, border);
    text(x, y + height - 1, bottom, border);
    for (int row = y + 1; row < y + height - 1; ++row) {
        text(x, row, "│", border);
        text(x + width - 1, row, "│", border);
    }
    if (!title.empty()) {
        text(x + 2, y, " " + title + " ", titleStyle);
    }
}

void Canvas::meter(int x, int y, int width, int value, const Style& full, const Style& empty) {
    // Eighth-block partials give a smooth fill.
    static const char* const partials[] = {"", "▏", "▎", "▍", "▌", "▋", "▊", "▉"};
    const int eighths = std::clamp(value, 0, 100) * width * 8 / 100;
    for (int i = 0; i < width; ++i) {
        const int cell = std::clamp(eighths - i * 8, 0, 8);
        if (cell == 8) {
            text(x + i, y, "█", full);
        } else if (cell > 0) {
            Style partial = full;
            partial.bg = empty.fg;
            text(x + i, y, partials[cell], partial);
        } else {
            text(x + i, y, "█", empty);
        }
    }
}

std::string Canvas::render(bool color) const {
    std::string out = "\x1b[H";
    out.reserve(cells_.size() * 12);
    const Style* last = nullptr;
    char sgr[96];
    for (int y = 0; y < rows_; ++y) {
        if (y > 0) {
            out += "\r\n";
        }
        for (int x = 0; x < columns_; ++x) {
            const Cell& cell = cells_[static_cast<std::size_t>(y * columns_ + x)];
            const Style& s = cell.style;
            if (color && (!last || s.fg.r != last->fg.r || s.fg.g != last->fg.g || s.fg.b != last->fg.b
                          || s.bg.r != last->bg.r || s.bg.g != last->bg.g || s.bg.b != last->bg.b
                          || s.bold != last->bold || s.dim != last->dim)) {
                std::snprintf(sgr, sizeof(sgr), "\x1b[0;%s%s38;2;%d;%d;%d;48;2;%d;%d;%dm", s.bold ? "1;" : "",
                              s.dim ? "2;" : "", s.fg.r, s.fg.g, s.fg.b, s.bg.r, s.bg.g, s.bg.b);
                out += sgr;
                last = &s;
            }
            out += cell.glyph;
        }
    }
    return out;
}

}  // namespace kms
