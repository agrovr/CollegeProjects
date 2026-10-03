#ifndef KMS_UI_APP_H
#define KMS_UI_APP_H

#include "core/Registry.h"
#include "core/RegistryFile.h"
#include "ui/Terminal.h"

#include <string>
#include <vector>

namespace kms {

// The full-screen key cabinet.
class App {
public:
    App(Terminal& terminal, bool color);

    // Start on the dashboard with an open registry, or on the open screen when path is empty.
    void open(Registry registry, const std::string& path, Format format);
    int run();

private:
    enum class Screen { Open, Dashboard, History };
    enum class Focus { Employees, Cabinet };
    enum class Dialog { None, Issue, Return, AddEmployee, RemoveEmployee, AddKey, Label, Save, Export, Quit, Help };

    struct Choice {
        std::string value;   // employee name or key id
        std::string detail;  // shown beside it
        bool enabled = true;
    };

    // Input
    void handle(const KeyPress& key);
    void handleOpen(const KeyPress& key);
    void handleDashboard(const KeyPress& key);
    void handleHistory(const KeyPress& key);
    void handleDialog(const KeyPress& key);
    bool editText(std::string& text, const KeyPress& key, std::size_t limit);
    void openDialog(Dialog dialog);
    void confirmDialog();
    void toast(const std::string& message, bool good = true);

    // Data helpers
    std::vector<const Employee*> visibleEmployees() const;
    std::vector<const kms::Key*> visibleKeys() const;
    const Employee* selectedEmployee() const;
    const kms::Key* selectedKey() const;
    std::vector<Choice> dialogChoices() const;
    void refreshFiles();
    void openPath(const std::string& path);

    // Drawing
    void draw(Canvas& canvas) const;
    void drawOpen(Canvas& canvas, int x, int y, int w, int h) const;
    void drawDashboard(Canvas& canvas, int x, int y, int w, int h) const;
    void drawEmployees(Canvas& canvas, int x, int y, int w, int h) const;
    void drawCabinet(Canvas& canvas, int x, int y, int w, int h) const;
    void drawDetails(Canvas& canvas, int x, int y, int w, int h) const;
    void drawActivity(Canvas& canvas, int x, int y, int w, int h) const;
    void drawHistory(Canvas& canvas, int x, int y, int w, int h) const;
    void drawDialog(Canvas& canvas, int x, int y, int w, int h) const;
    void drawFooter(Canvas& canvas, int x, int y, int w,
                    const std::vector<std::pair<std::string, std::string>>& keys) const;

    Terminal& terminal_;
    bool color_;
    bool running_ = true;
    long frame_ = 0;

    Screen screen_ = Screen::Open;
    Focus focus_ = Focus::Employees;
    Dialog dialog_ = Dialog::None;

    Registry registry_;
    std::string path_;
    Format format_ = Format::V2;

    int employeeIndex_ = 0;
    int keyIndex_ = 0;
    int historyOffset_ = 0;
    std::string filter_;
    bool searching_ = false;

    // Open screen
    std::vector<std::string> files_;
    int openIndex_ = 0;
    std::string openPathInput_;
    std::string openError_;

    // Dialog state
    std::string field1_;
    std::string field2_;
    int fieldIndex_ = 0;
    int choiceIndex_ = 0;
    std::string dialogError_;
    Format saveFormat_ = Format::V2;

    std::string toast_;
    bool toastGood_ = true;
    long toastUntil_ = 0;
};

}  // namespace kms

#endif
