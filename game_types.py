# NOTES:
# Tested under Python 3.8.0
# Requires the Pygame module

TILESIZE = 32, 32
TILESET_DIR = "."
DEFAULT_TILESET = "blue"

import os
import gui as _gui
import time
import struct
# import pygame

import scripts
from guipygame import *
from serializer import *


class StopGame(RuntimeError):
    pass

class Tileset():

    """
>>> # Tileset container class. Caches tilesets with the same name:
>>> x = Tileset("blue.png", "blue")
>>> y = Tileset("./blue.png", "blue")
>>> x is y
True
"""

    cache = {}

    def __new__(cls, ctx, filename, name):
        if name in cls.cache:
            return cls.cache[name]
        return super(Tileset, cls).__new__(Tileset)
    
    def __init__(self, ctx, filename, name):
        if hasattr(self, "name"):
            # Init'd twice
            return
        self.ctx = ctx

        self.name = name
        img = self.ctx.load_image(filename)

        self.tiles = []
        for y in range(img.h // TILESIZE[1]):
            row = []
            for x in range(img.w // TILESIZE[0]):
                row.append(ctx.empty_image(*TILESIZE))
                ctx.blit(row[-1], img, (0, 0), (x * TILESIZE[0], y * TILESIZE[1], TILESIZE[0], TILESIZE[1]))
            self.tiles += row

        self.img = img

        Tileset.cache[name] = self

    def __iter__(self):
        return iter(self.tiles)

    def __getitem__(self, x):
        return self.tiles[x]

# @Serializable("game_types::TileLayer", exclude=["tileset", "_surface"])
@UserSerializable("game_types::TileLayer")
class TileLayer():

    # __slots__ = ["_layer", "tileset", "_surface", "tileset_name"]

    def __init__(self, tileset, layerdata):
        self._layer = layerdata
        self.tileset = tileset
        self.tileset_name = tileset.name
        self._surface = None
        self.ctx = _gui.Context.current_ctx

    def set_ctx(self, ctx):
        self.ctx = ctx

    def __init_deserialize__(self):
        self.ctx = _gui.Context.current_ctx
        self.tileset  = Tileset(self.ctx, os.path.join(TILESET_DIR, self.tileset_name + ".png"), self.tileset_name)
        self._surface = None

    def draw(self, image, pos):
        if self._surface is None:
            self._regen_surface()
        self.ctx.blit(image, self._surface, pos)

    def _regen_surface(self):
        if len(self) == 0:
            self._surface = self.ctx.empty_image(0, 0)
            return
        
        size = len(self._layer[0]) * TILESIZE[0], len(self._layer) * TILESIZE[1]
        self._surface = self.ctx.empty_image(*size)
        for y, row in enumerate(self):
            for x, cell in enumerate(row):
                # print(self.tileset[cell])
                self.ctx.blit(self._surface, self.tileset[cell], (x * TILESIZE[0], y * TILESIZE[1]))

    def __iter__(self):
        return iter(self._layer)

    def __getitem__(self, x):
        return self._layer[x]

    def __setitem__(self, x, y):
        # Invalidate surface, forcing redraw
        self._surface = None
        self._layer[x] = y

    def __len__(self):
        return len(self._layer)

    def dump(self):
        res = serialize(len(self._layer[0])) + serialize(len(self._layer)) + serialize(self.tileset.name)
        for y in range(len(self._layer)):
            for x in range(len(self._layer[0])):
                d = serialize(self._layer[y][x])
                dtype = d[0]
                res += d[1:]

        return bytes([dtype]) + res

    @classmethod
    def load(cls, data):
        ctx = _gui.Context.current_ctx
        
        dtype = data[0:1]
        offs = 1
        width, offs = deserialize(data, offs)
        height, offs = deserialize(data, offs)
        tileset_name, offs = deserialize(data, offs)
        tileset = Tileset(ctx, os.path.join(TILESET_DIR, tileset_name + ".png"), tileset_name)

        layer = []
        for y in range(height):
            row = []
            for x in range(width):
                v, doffs = deserialize(dtype + data[offs:], 0)
                offs += doffs - 1
                row.append(v)
            layer.append(row)
        
        return cls(tileset, layer)

@Serializable("Entity", exclude=["script", "map"])
class Entity():

    __slots__ = ["name", "script", "script_name", "attributes", "map"]

    def __init__(self, name, attributes, script, map):
        self.name = name
        self.script = scripts.SCRIPTS[script]
        self.script_name = script
        self.attributes = attributes
        self.map = map

    def __init_deserialize__(self):
        # self.map will be set by the Map object after it's deserialized
        self.script = scripts.SCRIPTS[self.script_name]

    def draw(self, surface, offset):
        self.script.draw(self, surface, offset)

    def update(self):
        self.script.update(self)

    def send_message(self, ename, name, arg):
        for ent in self.map.entities:
            if ent.name == ename:
                ent.on_message(self, name, arg)

    def on_message(self, sender, name, arg):
        self.script.on_message(self, sender, name, arg)

@UserSerializable("Map")
class Map():

    def __init__(self, layers, entities):
        self.layers = layers
        self.entities = entities

    def draw(self, surface, pos):
        self.layers[0].draw(surface, pos)
        self.layers[1].draw(surface, pos)
        for entity in self.entities:
            entity.draw(surface, pos)
        self.layers[2].draw(surface, pos)

    def update(self):
        for entity in self.entites:
            entity.update()

    def dump(self):
        res = b""
        res += serialize(self.layers)
        res += serialize(self.entities)
        return res

    @classmethod
    def load(cls, data):
        i = 0
        layers, i = deserialize(data, i)
        entities, i = deserialize(data, i)
        res = cls(layers, entities)
        for ent in entities:
            ent.map = res

        return res
