from gui import *
import time
import pygame as _pygame
import warnings

class PygameContext(Context):

    class MainloopExit(Exception):
        pass

    def __init__(self, width, height):
        _pygame.init()
        self._screen_size = Vector2(width, height)
        self.display = _pygame.display.set_mode((width, height))
        self.draw_commands = []
        self.font_cache = {}
        self.key_timings = {}
        self.last_specials = []
        self.clock = _pygame.time.Clock()
        self.intervals = []
        self.title("PygameContext")

    def get_frametime(self):
        return self.clock.get_time() / 1000

    def set_interval(self, cb, t):
        self.intervals.append((cb, t, time.perf_counter()))

    def screen_size(self, new=None):
        if new is not None:
            self._screen_size = new
            self.display = _pygame.display.set_mode((new.x, new.y))
        return self._screen_size

    def fill_image(self, img, color):
        img.data.fill(color)

    def empty_image(self, w, h):
        x = _pygame.Surface((w, h), _pygame.SRCALPHA)
        return Image(x.convert_alpha(), w, h)

    def blit(self, dst, src, loc, bbox=None):
        if type(dst) != _pygame.Surface:
            dst = dst.data
        else:
            warnings.warn(UserWarning("dst: Using Pygame surfaces with Context.blit will not work with other Context types"))
        if type(src) != _pygame.Surface:
            src = src.data
        else:
            warnings.warn(UserWarning("src: Using Pygame surfaces with Context.blit will not work with other Context types"))
        if bbox is None:
            dst.blit(src, loc)
        else:
            dst.blit(src, loc, bbox)

    def PYGAMEsurface_to_image(self, surf):
        return Image(surf, surf.get_width(), surf.get_height())

    def draw_text(self, fontname, fontsize, text, color, pos):
        self.draw_commands.append(("text", fontname, fontsize, text, color, pos))

    def draw_image(self, image, pos):
        self.draw_commands.append(("image", image, pos))

    def draw_line(self, start, end, color):
        self.draw_commands.append(("line", start, end, color))

    def get_pressed_keymap(self):
        """Returns a list of all pressed keys. To check if a key is pressed, use:
>>> keys = ctx.get_pressed_keymap()
>>> keys[ord("lowercase key goes here")]
Note: Non-printable characters are implementation-dependent.
Note 2: This function should not be used. Instead, use Widget.bind()"""
        
        return _pygame.key.get_pressed()

    def cursor_position(self, new=None):
        if new is not None:
            _pygame.mouse.set_pos(new.x, new.y)
        return Vector2(*_pygame.mouse.get_pos())

    def is_left_pressed(self):
        return _pygame.mouse.get_pressed()[0]

    def is_mid_pressed(self):
        return _pygame.mouse.get_pressed()[1]

    def is_right_pressed(self):
        return _pygame.mouse.get_pressed()[2]

    def title(self, new=None):
        if new is not None:
            self._title = new
            _pygame.display.set_caption(self._title)
        return self._title

    def flush(self):
        for i in self.draw_commands:
            if i[0] == "text":
                if (i[1], i[2]) not in self.font_cache:
                    self.font_cache[i[1], i[2]] = _pygame.font.SysFont(i[1], i[2])

                surf = self.font_cache[i[1], i[2]].render(i[3], True, i[4])
                self.display.blit(surf, (i[5].x, i[5].y))

            elif i[0] == "image":
                self.display.blit(i[1].data, (i[2].x, i[2].y))

            elif i[0] == "line":
                _pygame.draw.line(self.display, i[3], (i[1].x, i[1].y), (i[2].x, i[2].y))

        self.draw_commands.clear()

    def load_image(self, path_or_file, namehint=""):
        surf = _pygame.image.load(path_or_file, namehint)
        surf.convert_alpha()

        return Image(surf, surf.get_width(), surf.get_height())

    def get_text_dimensions(self, fontname, fontsize, text):
        if (fontname, fontsize) not in self.font_cache:
            self.font_cache[fontname, fontsize] = _pygame.font.SysFont(fontname, fontsize)

        font = self.font_cache[fontname, fontsize]

        return Vector2(*font.size(text))

    def mainloop(self, toplevel):
        while 1:
            self.clock.tick(60)
            self.display.fill(0)
            try:
                self.tick(toplevel)
            except self.MainloopExit:
                break

    def get_fps(self):
        return self.clock.get_fps()

    def get_special_keys(self):
        mods = _pygame.key.get_mods()
        tmap = {
            _pygame.KMOD_LSHIFT: SpecialKeys.LSHFT,
            _pygame.KMOD_RSHIFT: SpecialKeys.RSHFT,
            _pygame.KMOD_LCTRL:  SpecialKeys.LCTRL,
            _pygame.KMOD_RCTRL:  SpecialKeys.RCTRL,
            _pygame.KMOD_LALT:   SpecialKeys.LALT,
            _pygame.KMOD_RALT:   SpecialKeys.RALT
        }
        keys = _pygame.key.get_pressed()
        kmap = {
            _pygame.K_LEFT:  SpecialKeys.LARR,
            _pygame.K_RIGHT: SpecialKeys.RARR,
            _pygame.K_UP:    SpecialKeys.UARR,
            _pygame.K_DOWN:  SpecialKeys.DARR
        }
        return [tmap[k] for k in tmap if mods & k] + [kmap[k] for k in kmap if keys[k]]

    def scale_image(self, image, newres):
        surf = _pygame.transform.scale(image.data, (newres.x, newres.y))
        return Image(surf, surf.get_width(), surf.get_height())

    def PYGAMEtick_without_event_get(self, toplevel, events):
        """PygameContext-only function"""
        for event in events:
            if event.type == _pygame.QUIT:
                raise self.MainloopExit

            elif event.type == _pygame.KEYDOWN:
                if event.key < 128:
                    toplevel.onEvent(Event(EventType.KEYDOWN, event.key))
                    toplevel.onEvent(Event(EventType.KEYHELD, event.key))

                    self.key_timings[event.key] = time.perf_counter()

            elif event.type == _pygame.KEYUP:
                if event.key < 128:
                    toplevel.onEvent(Event(EventType.KEYUP, event.key))

                    if event.key in self.key_timings:
                        del self.key_timings[event.key]

            elif event.type == _pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    etype = EventType.LEFTCLICK
                
                elif event.button == 3:
                    etype = EventType.RIGHTCLICK

                elif event.button == 4:
                    etype = EventType.SCROLLUP

                elif event.button == 5:
                    etype = EventType.SCROLLDOWN

                else:
                    continue
                
                toplevel.onEvent(Event(etype, Vector2(*_pygame.mouse.get_pos())))

            elif event.type == _pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    etype = EventType.LEFTRELEASE
                
                elif event.button == 3:
                    etype = EventType.RIGHTRELEASE

                else:
                    continue

                toplevel.onEvent(Event(etype, Vector2(*_pygame.mouse.get_pos())))

        specials = self.get_special_keys()
        for i in specials:
            if i not in self.last_specials:
                self.key_timings[i] = time.perf_counter()
                toplevel.onEvent(Event(EventType.KEYHELD, i))

        for i in self.last_specials:
            if i not in specials:
                del self.key_timings[i]

        self.last_specials = specials

        for key in self.key_timings:
            if time.perf_counter() - self.key_timings[key] > 0.4:
                toplevel.onEvent(Event(EventType.KEYHELD, key))

        for i, (cb, interval, last_fired) in enumerate(self.intervals):
            t = time.perf_counter()
            if t - last_fired > interval:
                cb()
                self.intervals[i] = (cb, interval, t)

        toplevel.render()
        self.flush()
        _pygame.display.flip()

    def tick(self, toplevel):
        self.PYGAMEtick_without_event_get(toplevel, _pygame.event.get())

if __name__ == "__main__":
    import random

    def on_focus(self, e):
        self.attrs["color"] = [255, 255, 255]

    def on_unfocus(self, e):
        self.attrs["color"] = [128, 128, 128]
    
    ctx = PygameContext(640, 480)

    toplevel = TableLayout(ctx, None, dim=Vector2(2, 10), maxsize=Vector2(640, 480))
    toplevel.setColExpanding(0, True)
    for i in range(10):
        entry = Entry(ctx, toplevel, width=200, fontname="Terminus", fontsize=32, color=[255, 255, 255])
        label = Label(ctx, toplevel, fontname="Arial", fontsize=20, color=[128, 128, 128], text="%s Entry %d: " % (random.randint(1, 10) * "!", i))

        label.bind(EventType.FOCUSED, on_focus)
        label.bind(EventType.UNFOCUSED, on_unfocus)

        toplevel.add(label, pos=Vector2(0, i))
        toplevel.add(entry, pos=Vector2(1, i))

        if i % 2 == 1:
            toplevel.setRowExpanding(i, True)

    ctx.mainloop(toplevel)
