#ifndef VPET_UI_APP_H
#define VPET_UI_APP_H

#include "core/Session.h"
#include "ui/Terminal.h"

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace vpet {

// The full-screen terminal interface.
class App {
public:
    App(Terminal& terminal, std::uint32_t seed, bool color);

    // Optionally start straight on the dashboard with a loaded pet.
    void open(std::unique_ptr<Pet> pet);

    int run();

private:
    enum class Screen { Title, Species, Name, Dashboard, Load };
    enum class Overlay { None, Help, Save, Quit };

    void handle(const Key& key);
    void handleTitle(const Key& key);
    void handleSpecies(const Key& key);
    void handleName(const Key& key);
    void handleDashboard(const Key& key);
    void handleLoad(const Key& key);
    void handleOverlay(const Key& key);

    void draw(Canvas& canvas) const;
    void drawTitle(Canvas& canvas, int x, int y, int w, int h) const;
    void drawSpecies(Canvas& canvas, int x, int y, int w, int h) const;
    void drawName(Canvas& canvas, int x, int y, int w, int h) const;
    void drawDashboard(Canvas& canvas, int x, int y, int w, int h) const;
    void drawLoad(Canvas& canvas, int x, int y, int w, int h) const;
    void drawOverlay(Canvas& canvas, int x, int y, int w, int h) const;
    void drawCreature(Canvas& canvas, int x, int y, int w, int h) const;
    void drawFooter(Canvas& canvas, int x, int y, int w, const std::vector<std::pair<std::string, std::string>>& keys) const;

    void act(Action action);
    void startPet(std::unique_ptr<Pet> pet);
    void refreshSaves();
    std::string defaultSavePath() const;

    Terminal& terminal_;
    std::uint32_t seed_;
    bool color_;
    bool running_ = true;
    long frame_ = 0;

    Screen screen_ = Screen::Title;
    Overlay overlay_ = Overlay::None;
    int titleChoice_ = 0;
    int speciesChoice_ = 0;
    int loadChoice_ = 0;
    std::string input_;
    std::string error_;
    std::vector<std::string> saves_;

    std::unique_ptr<Session> session_;
    Outcome last_;
    bool hasOutcome_ = false;
    long animationUntil_ = 0;
    long deltaUntil_ = 0;
    std::string status_;
};

}  // namespace vpet

#endif
