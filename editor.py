## Usage:
# Arrow keys - move
# + - Edit next level
# - - Edit previous level
# w - Change width
# h - Change height
# 1 - Switch to layer 1
# 2 - Switch to layer 2
# 3 - Switch to layer 3
# Use left mouse button to:
#   Select region in tileset
#   Draw selected tileset region onto tilemap
# Use right mouse button to:
#   Select region in tilemap and fill it in
# S - Save
# Z - Undo (TODO)

# import pygame
import tkinter as tk
from game_types import *
import guipygame as gui
from tkinter import messagebox

TILESET_WIDTH = 256
CAMSPEED = 256
SCROLLSPEED = 100
DEFAULT_TILESET = ("blue.png", "blue")

# TODO: Refactor partial_update_selection and update_selections
# TODO: Improve performance

class MutableContainer():

    __slots__ = ["value"]

    def __init__(self, value):
        self.value = value

class Editor():

    def __init__(self):
        self.tileset_left_pressed = False
        self.tilemap_right_pressed = False
        self.tilemap_left_pressed = False
        self.scr_input_on = False
        
        self.level = None
        self.layers = None
        self.current_map = None
        self.tileset_name = DEFAULT_TILESET

        self.tileset_scrollval = 0
        self.selection_tileset = [0, 0, 1, 1]
        self.selection_tilemap = [0, 0, 0, 0]
        self.left_pressed = False
        self.right_pressed = False
        self.time_left_pressed = 0
        self.camx = 0
        self.camy = 0
        self.camx_f = 0
        self.camy_f = 0
        self.save_time = -(1 << 20)

        self.current_layer = 0

        # Set up gui
        
        self.ctx = gui.PygameContext(800 + TILESET_WIDTH + 2, 600)

        self.toplevel_table = None
        self.toplevel = gui.PlaceLayout(None)
        self.toplevel_table = gui.TableLayout(self.toplevel,
                                        dim=gui.Vector2(2, 1), maxsize=self.ctx.screen_size(),
                                        margin=gui.Vector2(0, 0))
        self.toplevel.add(self.toplevel_table, pos=gui.Vector2(0, 0))
        self.tileset_image = None
        self.tileset_img_layout = None

        self.tilemap_img_layout = gui.PlaceLayout(self.toplevel_table,
                                                  minsize=gui.Vector2(800, 600), maxsize=gui.Vector2(800, 600))
        self.tilemap_img_container = self.ctx.empty_image(0, 0)
        self.tilemap_img_widget = gui.ImageWidget(self.tilemap_img_layout,
                                                  image=self.tilemap_img_container)
        self.toplevel_table.add(self.tilemap_img_layout,
                          pos=gui.Vector2(0, 0))
        self.tilemap_img_layout.add(self.tilemap_img_widget,
                          pos=gui.Vector2(0, 0))
        self.tilemap_lines = [gui.Line(self.tilemap_img_layout,
                                           start=gui.Vector2(0, 0), end=gui.Vector2(0, 0), color=[255, 255, 255]) for _ in range(4)]
        for i in self.tilemap_lines:
            self.tilemap_img_layout.add(i, pos=gui.Vector2(0, 0))
        # self.reload_tileset_image()
        self.change_level(0)

        self.toplevel_table.name = "toplevel table"
        self.toplevel.name = "toplevel"
        self.tilemap_img_layout.name = "tilemap img layout"
        self.tilemap_img_widget.name = "tilemap img widget"
        self.tileset_img_layout.name = "tileset img layout"
        self.tileset_img_container.name = "tileset img widget"

    def display_error(self, msg1, msg2):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(msg1, msg2, master=root)
        root.destroy()

    def change_level(self, to):
        if to >= 0:
            self.level = to
            try:
                with open(f"level{self.level}", "rb") as f:
                    self.current_map = deserialize(f.read(), 0)[0]
                    self.layers = self.current_map.layers
                    for layer in self.layers:
                        layer.set_ctx(self.ctx)
                
            except FileNotFoundError:
                self.load_default_map()

            except ValueError as e:
                self.display_error("Invalid map file", e)
                self.load_default_map()

            if self.toplevel_table is not None:
                self.reload_tileset_image()

            self.reload_tilemap_image()

    def reload_tilemap_image(self):
        self.tilemap_img_container = self.ctx.empty_image(
            len(self.layers[0][0]) * TILESIZE[0],
            len(self.layers[0]) * TILESIZE[1]
        )
        self.tilemap_img_widget.attrs["image"] = self.tilemap_img_container
        self.ctx.fill_image(self.tilemap_img_container, [0xC0, 0xC0, 0xC0])
        for layer in self.layers:
            layer.draw(self.tilemap_img_container, (0, 0))

    def load_default_map(self):
        self.layers = [
            TileLayer(Tileset(self.ctx, *DEFAULT_TILESET), []),
            TileLayer(Tileset(self.ctx, *DEFAULT_TILESET), []),
            TileLayer(Tileset(self.ctx, *DEFAULT_TILESET), []),
        ]
        self.current_map = Map(self.layers, set())
        
        for layer in self.layers:
            self.add_rows(layer._layer, 16)
            self.add_columns(layer._layer, 16)
            layer.set_ctx(self.ctx)
            layer._regen_surface()

    def reload_tileset_image(self):
        self.tileset_image = self.ctx.empty_image(self.layers[0].tileset.img.w, self.layers[0].tileset.img.h)
        self.ctx.fill_image(self.tileset_image, [0xc0, 0xc0, 0xc0])
        self.ctx.blit(self.tileset_image, self.layers[0].tileset.img, (0, 0))

        try:
            self.toplevel_table.remove(self.tileset_img_layout)
        except LookupError:
            pass
        self.tileset_img_layout = gui.PlaceLayout(self.toplevel_table,
                                                  size=gui.Vector2(self.tileset_image.w, self.tileset_image.h))
        self.tileset_img_container = gui.ImageWidget(self.tileset_img_layout,
                                                     image=self.tileset_image)
        self.toplevel_table.add(self.tileset_img_layout,
                          pos=gui.Vector2(1, 0))
        self.tileset_img_layout.add(self.tileset_img_container,
                                    pos=gui.Vector2(0, 0))

        self.tileset_lines = [
            gui.Line(self.tileset_img_layout,
                     start=gui.Vector2(0, 0), end=gui.Vector2(0, 0), color=[255, 255, 255])
            for i in range(4)
        ]
        for i in self.tileset_lines:
            self.tileset_img_layout.add(i, pos=gui.Vector2(0, 0))


        self.tileset_img_container.bind(gui.EventType.LEFTCLICK, self.on_tileset_left_clicked)
        self.tileset_img_container.bind(gui.EventType.LEFTRELEASE, self.on_tileset_left_released)
        for i in self.tileset_lines:
            i.bind(gui.EventType.LEFTCLICK, self.on_tileset_left_clicked)
            i.bind(gui.EventType.LEFTRELEASE, self.on_tileset_left_released)

    def update_selection_lines(self, selection, line_array, xoffs, yoffs):
        x = selection[0] * 32 + xoffs
        y = selection[1] * 32 + yoffs
        sx = selection[2] * 32
        sy = selection[3] * 32
        
        line_array[0].attrs["start"] = gui.Vector2(x, y)
        line_array[0].attrs["end"] = gui.Vector2(x + sx, y)

        line_array[1].attrs["start"] = gui.Vector2(x, y + sy)
        line_array[1].attrs["end"] = gui.Vector2(x + sx, y + sy)

        line_array[2].attrs["start"] = gui.Vector2(x, y)
        line_array[2].attrs["end"] = gui.Vector2(x, y + sy)

        line_array[3].attrs["start"] = gui.Vector2(x + sx, y)
        line_array[3].attrs["end"] = gui.Vector2(x + sx, y + sy)
    

    def change_tileset_dialog(self):
        self.scr_input(self.change_tileset_dialog_cb, "Tileset name: ")

    def change_tileset_dialog_cb(self, new_tileset_name):
        b = True
        for layer in self.layers:
            try:
                layer.tileset = Tileset(self.ctx, os.path.join(TILESET_DIR, new_tileset_name + ".png"), new_tileset_name)
            except Exception as e:
                print(str(e))
                b = False
                break
            layer._surface = None
        if b:
            self.tileset_name = new_tileset_name
            self.reload_tileset_image()
            self.reload_tilemap_image()

    def add_rows(self, table, n):
        table += [[] for _ in range(n)]

    def add_columns(self, table, n):
        for i in table:
            i += [0 for _ in range(n)]

    def remove_rows(self, table, n):
        for _ in range(n):
            table.pop()

    def remove_columns(self, table, n):
        for row in table:
            for _ in range(n):
                row.pop()        

    def tileset_scroll_up(self, w, e):
        self.tileset_scrollval -= SCROLLSPEED

        cid = self.tileset_img_layout.getChildID(self.tileset_img_container)
        self.tileset_img_layout.children[cid][1]["pos"] = gui.Vector2(0, -self.tileset_scrollval)

    def tileset_scroll_down(self, w, e):
        self.tileset_scrollval += SCROLLSPEED

        cid = self.tileset_img_layout.getChildID(self.tileset_img_container)
        self.tileset_img_layout.children[cid][1]["pos"] = gui.Vector2(0, -self.tileset_scrollval)

    def handle_keyup(self, w, e):
        if self.scr_input_on:
            return gui.CallNextEventHandler
        
        if e.value == b"-"[0]:
            self.change_level(self.level - 1)
            
        elif e.value == b"="[0]:
            self.change_level(self.level + 1)

        elif e.value == b"t"[0]:
            self.change_tileset_dialog()

        elif e.value == b"h"[0]:
            self.scr_input(self.set_height_cb, "Height: ")
            return gui.CallNextEventHandler

        elif e.value == b"w"[0]:
            self.scr_input(self.set_width_cb, "Width: ")
            return gui.CallNextEventHandler

        elif e.value == b"1"[0]:
            self.current_layer = 0
        elif e.value == b"2"[0]:
            self.current_layer = 1
        elif e.value == b"3"[0]:
            self.current_layer = 2

        elif e.value == b"s"[0]:
            self.save_time = time.perf_counter()
            # TileLayer.save_layers(f"level{self.level}", self.layers)
            with open(f"level{self.level}", "wb") as f:
                f.write(serialize(self.current_map))

        else:
            return gui.CallNextEventHandler

    def set_width_cb(self, text):
        width = int(text)
        for layer in self.layers:
            if len(layer[0]) < width:
                self.add_columns(layer._layer, width - len(layer[0]))
                
            elif len(layer[0]) > width:
                self.remove_columns(layer._layer, len(layer[0]) - width)
                layer._regen_surface()

    def set_height_cb(self, text):
        height = int(text)
        for layer in self.layers:
            if len(layer) < height:
                difference = height - len(layer)
                self.add_rows(layer._layer, difference)
                self.add_columns(layer[-difference:], len(layer[0]))
            
            elif len(layer) > height:
                self.remove_rows(layer._layer, len(layer) - height)
                layer._regen_surface()

    def handle_keyheld(self, w, e):
        dt = self.ctx.get_frametime()
        
        if e.value == gui.SpecialKeys.LARR:
            self.camx_f -= CAMSPEED * dt
        elif e.value == gui.SpecialKeys.UARR:
            self.camy_f -= CAMSPEED * dt
        elif e.value == gui.SpecialKeys.DARR:
            self.camy_f += CAMSPEED * dt
        elif e.value == gui.SpecialKeys.RARR:
            self.camx_f += CAMSPEED * dt

        cid = self.tilemap_img_layout.getChildID(self.tilemap_img_widget)
        self.camx = int(self.camx_f)
        self.camy = int(self.camy_f)
        self.tilemap_img_layout.children[cid][1]["pos"] = Vector2(-self.camx, -self.camy)

    def on_tileset_left_clicked(self, widget, e):
        self.tileset_left_pressed = True
        e.value -= self.tileset_img_container.getTopLevelPosition()
        # e.value += gui.Vector2(0, self.tileset_scrollval)
        self.selection_tileset = [
            e.value.x // TILESIZE[0], e.value.y // TILESIZE[1],
            1, 1
        ]
        print(self.selection_tileset)

    def on_tileset_left_released(self, widget, e):
        self.tileset_left_pressed = False
        # self.selection_tileset = [0, 0, 0, 0]

    def on_tilemap_left_clicked(self, widget, e):
        self.tilemap_left_pressed = True
        self.selection_tilemap = [
            (e.value.x + self.camx) // TILESIZE[0], (e.value.y + self.camy) // TILESIZE[1],
            self.selection_tileset[2], self.selection_tileset[3]
        ]

    def on_tilemap_right_clicked(self, widget, e):
        self.tilemap_right_pressed = True
        self.selection_tilemap = [
            (e.value.x + self.camx) // TILESIZE[0], (e.value.y + self.camy) // TILESIZE[1],
            1, 1
        ]

    def on_tilemap_right_released(self, widget, e):
        self.fill_tilemap_area()
        self.tilemap_right_pressed = False
        self.selection_tilemap = [0, 0, 0, 0]

    def on_tilemap_left_released(self, widget, e):
        self.fill_tilemap_area()
        self.tilemap_left_pressed = False
        self.selection_tilemap = [0, 0, 0, 0]

    def fill_tilemap_area(self):
        ts_w = self.layers[0].tileset.img.w // TILESIZE[0]
        for x in range(self.selection_tilemap[0], self.selection_tilemap[0] + self.selection_tilemap[2]):
            for y in range(self.selection_tilemap[1], self.selection_tilemap[1] + self.selection_tilemap[3]):
                tsx = (x - self.selection_tilemap[0]) % self.selection_tileset[2] + self.selection_tileset[0]
                tsy = (y - self.selection_tilemap[1]) % self.selection_tileset[3] + self.selection_tileset[1]
                try:
                    self.layers[self.current_layer][y][x] = ts_w * tsy + tsx
                except IndexError:
                    pass
        
        self.layers[self.current_layer]._regen_surface()
        self.reload_tilemap_image()
    
    def run(self):
        self.toplevel.bind(gui.EventType.KEYUP, self.handle_keyup)
        self.toplevel.bind(gui.EventType.KEYHELD, self.handle_keyheld)
        self.toplevel.bind(gui.EventType.SCROLLUP, self.tileset_scroll_up)
        self.toplevel.bind(gui.EventType.SCROLLDOWN, self.tileset_scroll_down)
        
        self.tilemap_img_widget.bind(gui.EventType.LEFTCLICK, self.on_tilemap_left_clicked)
        self.tilemap_img_widget.bind(gui.EventType.LEFTRELEASE, self.on_tilemap_left_released)
        self.tilemap_img_widget.bind(gui.EventType.RIGHTCLICK, self.on_tilemap_right_clicked)
        self.tilemap_img_widget.bind(gui.EventType.RIGHTRELEASE, self.on_tilemap_right_released)
        for i in self.tilemap_lines:
            i.bind(gui.EventType.LEFTCLICK, self.on_tilemap_left_clicked)
            i.bind(gui.EventType.LEFTRELEASE, self.on_tilemap_left_released)
            i.bind(gui.EventType.RIGHTCLICK, self.on_tilemap_right_clicked)
            i.bind(gui.EventType.RIGHTRELEASE, self.on_tilemap_right_released)

        self.tileset_img_container.bind(gui.EventType.LEFTCLICK, self.on_tileset_left_clicked)
        self.tileset_img_container.bind(gui.EventType.LEFTRELEASE, self.on_tileset_left_released)
        for i in self.tileset_lines:
            i.bind(gui.EventType.LEFTCLICK, self.on_tileset_left_clicked)
            i.bind(gui.EventType.LEFTRELEASE, self.on_tileset_left_released)
        
        self.ctx.set_interval(self.update, 1/30)
        self.ctx.mainloop(self.toplevel)

    def tile_box_logic(self, old_pos, new_pos, selection):
        if new_pos.x > old_pos.x:
            selection[2] = max((new_pos.x - old_pos.x) // TILESIZE[0], 1)
        else:
            selection[0] = (new_pos.x + self.camx) // TILESIZE[0]
            selection[2] = max((old_pos.x - new_pos.x) // TILESIZE[0], 1)
        
        if new_pos.y > old_pos.y:
            selection[3] = max((new_pos.y - old_pos.y) // TILESIZE[1], 1)
        else:
            selection[1] = (new_pos.y + self.camy) // TILESIZE[1]
            selection[3] = max((old_pos.y - new_pos.y) // TILESIZE[1], 1)
        
    def update(self):
        width, height = len(self.layers[0][0]), len(self.layers[0])
        save_message = "Saved!" if time.perf_counter() - self.save_time < 0.4 else ""
        self.ctx.title("Width %d, height %d, current layer %d | %.2f FPS | Editing level%d | %s" % (
            width, height, self.current_layer + 1, self.ctx.get_fps(), self.level, save_message
        ))
        if self.tilemap_right_pressed:
            old_pos = gui.Vector2(self.selection_tilemap[0] * 32 - self.camx, self.selection_tilemap[1] * 32 - self.camy)
            new_pos = self.ctx.cursor_position()
            self.tile_box_logic(old_pos, new_pos, self.selection_tilemap)

        if self.tileset_left_pressed:
            old_pos = gui.Vector2(self.selection_tileset[0] * 32, self.selection_tileset[1] * 32)
            new_pos = self.ctx.cursor_position() - self.tileset_img_container.getTopLevelPosition() # + gui.Vector2(0, self.tileset_scrollval)
            self.tile_box_logic(old_pos, new_pos, self.selection_tileset)

        if self.tilemap_left_pressed:
            new_pos = self.ctx.cursor_position()
            self.selection_tilemap = [
                (new_pos.x + self.camx) // TILESIZE[0], (new_pos.y + self.camy) // TILESIZE[1],
                self.selection_tileset[2], self.selection_tileset[3]
            ]
        
        self.update_selection_lines(self.selection_tileset, self.tileset_lines, 0, -self.tileset_scrollval)
        self.update_selection_lines(self.selection_tilemap, self.tilemap_lines, -self.camx, -self.camy)

    def _scr_input_cb(self, widget, e):
        if e.value in b"\r\n":
            self.toplevel.remove(self.scr_dialog_table)
            self.scr_input_on = False
            self.scr_input_cb(self.scr_input_entry.text)
        else:
            return gui.CallNextEventHandler

    def scr_input(self, cb, prompt):
        self.scr_input_on = True
        self.scr_input_cb = cb
        
        self.scr_dialog_table = gui.TableLayout(self.toplevel,
                                       dim=gui.Vector2(2, 1), maxsize=gui.Vector2(100, 100))
        self.toplevel.add(self.scr_dialog_table,
                          pos=gui.Vector2(800 // 2, 600 // 2))
        
        label = gui.Label(self.scr_dialog_table,
                          text=prompt, color=[255, 255, 255], fontname="Arial", fontsize=20)
        self.scr_dialog_table.add(label,
                         pos=gui.Vector2(0, 0))

        self.scr_input_entry = gui.Entry(self.scr_dialog_table,
                          color=[255, 255, 255], fontname="Arial", fontsize=20, width=200)
        self.scr_dialog_table.add(self.scr_input_entry,
                         pos=gui.Vector2(1, 0))
        # TODO: Don't do this
        self.scr_input_entry.front.bind(gui.EventType.KEYUP, self._scr_input_cb)
        self.scr_input_entry.back.bind(gui.EventType.KEYUP, self._scr_input_cb)


if __name__ == "__main__":
    editor = Editor()
    editor.run()
