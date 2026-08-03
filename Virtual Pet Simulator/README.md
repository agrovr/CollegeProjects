# Virtual Pet Simulator

A portable C++ console game for creating and caring for a virtual creature. Each species has distinct abilities, while shared health and mood systems respond to feeding, rest, play, training, and the passage of time.

## Features

- Dragon, Unicorn, and Mystic Cat species with unique actions
- Six bounded state values that evolve after every interaction
- Versioned save files with validation and support for names containing spaces
- Menu input that recovers cleanly from invalid entries
- Polymorphic species behavior without platform-specific dependencies

## Build

```bash
cmake -S . -B build
cmake --build build
```

Alternatively, compile directly with a C++17 compiler:

```bash
g++ -std=c++17 -Wall -Wextra -Wpedantic main.cpp Game.cpp Pet.cpp Dragon.cpp Unicorn.cpp MysticCat.cpp -o virtual-pet
```

## Run

```bash
./build/virtual-pet
```

On multi-configuration generators, the executable may be located in `build/Debug` or `build/Release`.

## Save files

The simulator writes a compact, versioned text format containing the creature type, quoted name, and validated state values. Save files use the `.sav` extension by convention and are intended to be created through the application.
