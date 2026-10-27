cmake_minimum_required(VERSION 3.22.1)
project(x3touch C)

# La capa táctil vive en el árbol del juego, no en android/: así el mismo .c
# que corren los tests de escritorio es el que se empaqueta en el APK.
set(X3_TOUCH_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../../../src/platform/android")

add_library(x3touch SHARED
    ${X3_TOUCH_DIR}/x3_touch_controls.c
    ${CMAKE_CURRENT_SOURCE_DIR}/x3_touch_controls_jni.c)

target_include_directories(x3touch PRIVATE ${X3_TOUCH_DIR})
target_compile_options(x3touch PRIVATE -Wall -Wextra)
