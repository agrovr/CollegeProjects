cmake_minimum_required(VERSION 3.16)
project(KeyManagementSystem LANGUAGES CXX)

add_executable(key-management main.cpp)
target_compile_features(key-management PRIVATE cxx_std_17)

if(MSVC)
    target_compile_options(key-management PRIVATE /W4 /permissive-)
else()
    target_compile_options(key-management PRIVATE -Wall -Wextra -Wpedantic)
endif()
