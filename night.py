#!/usr/bin/python

import click
import pydbus
import logging
import enum
import dataclasses
from gi.repository.GLib import Variant


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


NORMAL_LEVEL = 6495
FACTOR = 0.8
LEVEL_COUNT = 5


class EIcon(enum.Enum):
    sunrise = 'daytime-sunrise-symbolic'
    sunset = 'daytime-sunset-symbolic'


@dataclasses.dataclass
class DLevel:
    min_level: int
    mid_level: int
    max_level: int
    level: int


def _wrap_variants(dict_):
    def _wrap_one(v):
        for type_, tag in {
                str: 's',
                int: 'u',
                float: 'd',
                # 'b': GLib.Variant.new_boolean,
                # 'y': GLib.Variant.new_byte,
                # 'n': GLib.Variant.new_int16,
                # 'q': GLib.Variant.new_uint16,
                # 'i': GLib.Variant.new_int32,
                # 'u': GLib.Variant.new_uint32,
                # 'x': GLib.Variant.new_int64,
                # 't': GLib.Variant.new_uint64,
                # 'h': GLib.Variant.new_handle,
                # 'd': GLib.Variant.new_double,
                # 's': GLib.Variant.new_string,
                # 'o': GLib.Variant.new_object_path,
                # 'g': GLib.Variant.new_signature,
                # 'v': GLib.Variant.new_variant,
        }.items():
            if isinstance(v, type_):
                return Variant(tag, v)
        else:
            raise NotImplementedError("Unknown type: %r" % v)

    return {
        k: _wrap_one(v)
        for k, v in dict_.items()
    }


class Notifier:
    def __init__(self):
        self._shell = pydbus.SessionBus().get('org.gnome.Shell')

    def send_notify(self, icon: EIcon, level: DLevel, label: str):
        params = {
            'icon': icon.value,
            'level': (level.level - level.min_level) / (level.mid_level - level.min_level),
            'max_level': (level.max_level - level.min_level) / (level.mid_level - level.min_level),
            'label': label,
        }
        LOGGER.info("Sending notify: %r", params)
        self._shell.ShowOSD(_wrap_variants(params))


class ColorManager:
    def __init__(self):
        pass

    def _get_color_obj(self):
        return pydbus.SessionBus().get('org.gnome.SettingsDaemon.Color')

    def get_color(self):
        return self._get_color_obj().Temperature

    def set_color(self, value: int) -> None:
        self._get_color_obj().Temperature = value


@click.group(help="Simple tool to manage color temperature")
def main():
    pass


@main.command("get", help="Print current color temperature")
def get_color():
    color = ColorManager().get_color()
    print(color)


@main.command("set", help="Set color temperature from 1000 to 10000 (Kelvins)")
@click.argument("temp", type=int)
def set_color(temp):
    ColorManager().set_color(temp)


@main.command("reset", help=f"Reset color temperature to {NORMAL_LEVEL}")
def reset_color():
    ColorManager().set_color(NORMAL_LEVEL)


@main.command("loop", help=f"Change temperature in loop of {LEVEL_COUNT} levels")
def loop():
    color_manager = ColorManager()
    temp = color_manager.get_color()

    levels = [int(NORMAL_LEVEL * (FACTOR**alpha)) for alpha in range(0, LEVEL_COUNT + 1)]

    for level, new_level in zip(levels, levels[1:] + levels[:1]):
        if temp >= level:
            break
    else:
        new_level = levels[0]

    if new_level >= temp:
        icon = EIcon.sunrise
    else:
        icon = EIcon.sunset

    color_manager.set_color(new_level)
    Notifier().send_notify(icon, DLevel(0, NORMAL_LEVEL, 8000, new_level), f"{new_level}K")


if __name__ == "__main__":
    main()
