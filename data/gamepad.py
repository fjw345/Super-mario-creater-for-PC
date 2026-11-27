"""Read SDL's standard controller buttons, including left-stick directions."""

import pygame as pg
from pygame._sdl2 import controller


BUTTONS = (
    pg.CONTROLLER_BUTTON_A, pg.CONTROLLER_BUTTON_B,
    pg.CONTROLLER_BUTTON_X, pg.CONTROLLER_BUTTON_Y,
    pg.CONTROLLER_BUTTON_BACK, pg.CONTROLLER_BUTTON_START,
    pg.CONTROLLER_BUTTON_DPAD_LEFT, pg.CONTROLLER_BUTTON_DPAD_RIGHT,
    pg.CONTROLLER_BUTTON_DPAD_UP, pg.CONTROLLER_BUTTON_DPAD_DOWN,
)
STICK_DIRECTIONS = (
    (pg.CONTROLLER_AXIS_LEFTX, pg.CONTROLLER_BUTTON_DPAD_LEFT, pg.CONTROLLER_BUTTON_DPAD_RIGHT),
    (pg.CONTROLLER_AXIS_LEFTY, pg.CONTROLLER_BUTTON_DPAD_UP, pg.CONTROLLER_BUTTON_DPAD_DOWN),
)
STICK_DEAD_ZONE = round(32767 * 0.35)


class Gamepads:
    def __init__(self):
        self.devices = {}
        try:
            controller.init()
        except pg.error:
            return
        self.refresh()

    def refresh(self):
        """Rescan after hotplug events, retaining open devices by instance ID."""
        if not controller.get_init():
            return

        connected = {}
        for index in range(controller.get_count()):
            if not controller.is_controller(index):
                continue
            try:
                instance_id = pg.joystick.Joystick(index).get_instance_id()
                pad = self.devices.get(instance_id)
                if pad is None:
                    pad = controller.Controller(index)
                connected[instance_id] = pad
            except pg.error:
                # A device may disappear between enumeration and opening it.
                continue

        for instance_id in self.devices.keys() - connected.keys():
            self.devices[instance_id].quit()
        self.devices = connected

    def pressed_buttons(self):
        pressed = set()
        for pad in self.devices.values():
            if not pad.attached():
                continue
            pressed.update(button for button in BUTTONS if pad.get_button(button))
            for axis, negative, positive in STICK_DIRECTIONS:
                value = pad.get_axis(axis)
                if value < -STICK_DEAD_ZONE:
                    pressed.add(negative)
                elif value > STICK_DEAD_ZONE:
                    pressed.add(positive)
        return pressed
