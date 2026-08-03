cmake_minimum_required(VERSION 3.16)
project(VirtualPetSimulator LANGUAGES CXX)

add_executable(virtual-pet
    main.cpp
    Game.cpp
    Pet.cpp
    Dragon.cpp
    Unicorn.cpp
    MysticCat.cpp
)

target_compile_features(virtual-pet PRIVATE cxx_std_17)

if(MSVC)
    target_compile_options(virtual-pet PRIVATE /W4 /permissive-)
else()
    target_compile_options(virtual-pet PRIVATE -Wall -Wextra -Wpedantic)
endif()
