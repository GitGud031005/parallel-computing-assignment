# Build scaffold only. Add real benchmark/test targets during milestone M1.
add_library(pc_a1_options INTERFACE)
target_compile_features(pc_a1_options INTERFACE cxx_std_20)
target_include_directories(pc_a1_options INTERFACE "${CMAKE_CURRENT_SOURCE_DIR}/include")
target_link_libraries(pc_a1_options INTERFACE Threads::Threads)
if(MSVC)
    target_compile_options(pc_a1_options INTERFACE /W4 /permissive-)
else()
    target_compile_options(pc_a1_options INTERFACE -Wall -Wextra -Wpedantic)
endif()

message(STATUS "Assignment 1 scaffold: algorithms, executables, and tests are not implemented yet.")
