#ifndef KMS_UI_TERMINAL_H
#define KMS_UI_TERMINAL_H

#include <cstdint>
#include <string>
#include <vector>

namespace kms {

// --- Keyboard ----------------------------------------------------------------------------------

enum class KeyType { None, Char, Enter, Escape, Backspace, Up, Down, Left, Right, Tab };

struct KeyPress {
    KeyType type = KeyType::None;
    char ch = 0;  // for KeyType::Char, lowercased for letters

    bool is(char c) const { return type == KeyType::Char && ch == c; }
};

// Puts the terminal into a full-screen, unbuffered, no-echo mode for the lifetime of the object,
// and restores it on destruction (and on Ctrl+C).
class Terminal {
public:
    Terminal();
    ~Terminal();
    Terminal(const Terminal&) = delete;
    Terminal& operator=(const Terminal&) = delete;

    // Waits up to timeoutMs for a key. Returns KeyType::None on timeout.
    KeyPress readKey(int timeoutMs);

    // Current size in columns and rows.
    void size(int& columns, int& rows) const;

    void write(const std::string& bytes);

    static bool interactive();  // stdin and stdout are both terminals
};

// --- Drawing -----------------------------------------------------------------------------------

struct Color {
    std::uint8_t r = 0, g = 0, b = 0;
};

struct Style {
    Color fg{236, 228, 246};
    Color bg{20, 23, 28};
    bool bold = false;
    bool dim = false;
};

// A grid of styled cells. Text is UTF-8 and every code point is treated as one column wide,
// so only single-width symbols are used in the interface.
class Canvas {
public:
    Canvas(int columns, int rows, const Style& base);

    int columns() const { return columns_; }
    int rows() const { return rows_; }

    void text(int x, int y, const std::string& utf8, const Style& style);
    void fill(int x, int y, int width, int height, const Style& style);
    void box(int x, int y, int width, int height, const Style& border, const std::string& title = "");
    void box(int x, int y, int width, int height, const Style& border, const std::string& title,
             const Style& titleStyle);
    // A horizontal meter of `width` cells filled to value/100.
    void meter(int x, int y, int width, int value, const Style& full, const Style& empty);

    std::string render(bool color) const;

private:
    struct Cell {
        std::string glyph = " ";
        Style style;
    };

    std::vector<Cell> cells_;
    int columns_;
    int rows_;
};

std::vector<std::string> splitUtf8(const std::string& text);
std::size_t utf8Length(const std::string& text);

}  // namespace kms

#endif
