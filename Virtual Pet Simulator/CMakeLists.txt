cmake_minimum_required(VERSION 3.16)
project(VirtualPetSimulator LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Game rules, with no terminal code, so they can be tested on their own.
add_library(vpet_core STATIC
    src/core/Pet.cpp
    src/core/Session.cpp
    src/core/SaveFile.cpp
    src/core/species/Dragon.cpp
    src/core/species/Unicorn.cpp
    src/core/species/MysticCat.cpp
    src/ui/Art.cpp
)
target_include_directories(vpet_core PUBLIC src)

add_executable(virtual-pet
    src/main.cpp
    src/ui/App.cpp
    src/ui/PlainUi.cpp
    src/ui/Terminal.cpp
)
target_link_libraries(virtual-pet PRIVATE vpet_core)

foreach(target vpet_core virtual-pet)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4 /permissive- /utf-8)
        target_compile_definitions(${target} PRIVATE _CRT_SECURE_NO_WARNINGS)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
    endif()
endforeach()

include(CTest)
if(BUILD_TESTING)
    add_executable(vpet_tests tests/test_core.cpp)
    target_link_libraries(vpet_tests PRIVATE vpet_core)
    if(MSVC)
        target_compile_options(vpet_tests PRIVATE /W4 /utf-8)
        target_compile_definitions(vpet_tests PRIVATE _CRT_SECURE_NO_WARNINGS)
    else()
        target_compile_options(vpet_tests PRIVATE -Wall -Wextra -Wpedantic)
    endif()
    add_test(NAME core COMMAND vpet_tests)
endif()
