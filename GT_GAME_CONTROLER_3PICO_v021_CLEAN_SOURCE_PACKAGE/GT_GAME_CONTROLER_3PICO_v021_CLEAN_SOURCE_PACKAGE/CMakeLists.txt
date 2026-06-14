cmake_minimum_required(VERSION 3.13)

# Set PICO_SDK_PATH in environment or pass -DPICO_SDK_PATH=/path/to/pico-sdk
if(NOT DEFINED PICO_SDK_PATH)
  if(DEFINED ENV{PICO_SDK_PATH})
    set(PICO_SDK_PATH $ENV{PICO_SDK_PATH})
  else()
    message(FATAL_ERROR "PICO_SDK_PATH is not set")
  endif()
endif()
include(${PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(gt_game_controler_3pico_v021 C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(piko1
  firmware/mouse/mouse_main.c
  firmware/mouse/mouse_usb_descriptors.c
)
target_include_directories(piko1 PRIVATE firmware/mouse)
target_compile_definitions(piko1 PRIVATE PLAYER_ID=1 PIN_ENABLE=19)
target_link_libraries(piko1 PRIVATE pico_stdlib hardware_adc hardware_flash tinyusb_device tinyusb_board)
pico_add_extra_outputs(piko1)

add_executable(piko2
  firmware/mouse/mouse_main.c
  firmware/mouse/mouse_usb_descriptors.c
)
target_include_directories(piko2 PRIVATE firmware/mouse)
target_compile_definitions(piko2 PRIVATE PLAYER_ID=2 PIN_ENABLE=19)
target_link_libraries(piko2 PRIVATE pico_stdlib hardware_adc hardware_flash tinyusb_device tinyusb_board)
pico_add_extra_outputs(piko2)

add_executable(controller
  firmware/controller/keyboard_main.c
  firmware/controller/keyboard_usb_descriptors.c
)
target_include_directories(controller PRIVATE firmware/controller)
target_link_libraries(controller PRIVATE pico_stdlib hardware_flash tinyusb_device tinyusb_board)
pico_add_extra_outputs(controller)
