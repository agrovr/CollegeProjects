cmake_minimum_required(VERSION 3.16)
project(KeyManagementSystem LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# The registry and its file formats, with no terminal code, so they can be tested on their own.
add_library(kms_core STATIC
    src/core/Registry.cpp
    src/core/RegistryFile.cpp
)
target_include_directories(kms_core PUBLIC src)

add_executable(key-management
    src/main.cpp
    src/ui/App.cpp
    src/ui/PlainUi.cpp
    src/ui/Terminal.cpp
)
target_link_libraries(key-management PRIVATE kms_core)

foreach(target kms_core key-management)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4 /permissive- /utf-8)
        target_compile_definitions(${target} PRIVATE _CRT_SECURE_NO_WARNINGS)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
    endif()
endforeach()

include(CTest)
if(BUILD_TESTING)
    add_executable(kms_tests tests/test_registry.cpp)
    target_link_libraries(kms_tests PRIVATE kms_core)
    if(MSVC)
        target_compile_options(kms_tests PRIVATE /W4 /utf-8)
        target_compile_definitions(kms_tests PRIVATE _CRT_SECURE_NO_WARNINGS)
    else()
        target_compile_options(kms_tests PRIVATE -Wall -Wextra -Wpedantic)
    endif()
    add_test(NAME registry COMMAND kms_tests)
endif()
