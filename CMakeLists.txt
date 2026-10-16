cmake_minimum_required(VERSION 3.20)
project(ParallelComputingAssignments LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(Threads REQUIRED)
include(CheckCXXSourceCompiles)
set(CMAKE_REQUIRED_LIBRARIES Threads::Threads)
check_cxx_source_compiles("
    #include <barrier>
    int main() {
        std::barrier<> gate(1);
        gate.arrive_and_wait();
    }
" PC_HAS_STD_BARRIER)
unset(CMAKE_REQUIRED_LIBRARIES)
if(NOT PC_HAS_STD_BARRIER)
    message(FATAL_ERROR "A C++20 compiler and standard library with std::barrier are required. See README.md.")
endif()

include(CTest)
add_subdirectory(assignments/assignment1)
