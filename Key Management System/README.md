# Key Management System

A command-line registry for tracking which physical keys are issued to employees. The application loads an existing registry, supports common lookup and update operations, and exports the current state in the same portable text format.

## Features

- Look up keys by employee or employees by key
- Issue and return keys with duplicate and capacity checks
- Validate registry files before accepting their contents
- Preserve employee names that contain spaces
- Save the updated registry to a selected destination

## Build

```bash
cmake -S . -B build
cmake --build build
```

Alternatively, compile directly with a C++17 compiler:

```bash
g++ -std=c++17 -Wall -Wextra -Wpedantic main.cpp -o key-management
```

## Run

```bash
./build/key-management input_key.txt
```

On multi-configuration generators, the executable may be located in `build/Debug` or `build/Release`.

## Registry format

The first line stores the number of employees. Each employee then uses two lines: the employee name, followed by the number of issued keys and their identifiers.

```text
2
Ya Hoo
3 AHC102 AHC200 AHC111
Michael Lee
2 AHC303 AHC200
```
