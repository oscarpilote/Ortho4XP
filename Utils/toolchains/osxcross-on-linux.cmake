# This file is intented to be used as a toolchain file for cmake
# crosscompiling for OSX from Linux with o64-clang (osxcross).

set(CMAKE_SYSTEM_NAME Darwin)
set(TOOLCHAIN_PREFIX x86_64-apple-darwin20.2)

set(CMAKE_FIND_ROOT_PATH /usr/local/osxcross)
set(CMAKE_C_COMPILER ${CMAKE_FIND_ROOT_PATH}/bin/o64-clang)
set(CMAKE_CXX_COMPILER ${CMAKE_FIND_ROOT_PATH}/bin/o64-clang++)

# SHELL: needed to avoid cmake 3.12+ option de-duplication by default.
add_compile_options(-mmacosx-version-min=10.10 "SHELL:-arch x86_64" "SHELL:-arch arm64")
add_link_options(-mmacosx-version-min=10.10 "SHELL:-arch x86_64" "SHELL:-arch arm64")

set(CMAKE_OSX_SYSROOT ${CMAKE_FIND_ROOT_PATH}/SDK/MacOSX11.1.sdk)

set(OPENGL_FRAMEWORK_DIR ${CMAKE_FIND_ROOT_PATH}/SDK/MacOSX11.1.sdk/System/Library/Frameworks/OpenGL.framework)

set(OPENGL_gl_LIBRARY ${OPENGL_FRAMEWORK_DIR}/OpenGL.tbd)
set(OPENGL_INCLUDE_DIR ${OPENGL_FRAMEWORK_DIR}/Headers)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
