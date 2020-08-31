from guibase import *

class PlaceLayout(Layout):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        if "maxsize" not in self.attrs:
            self.attrs["maxsize"] = Vector2(1<<32, 1<<32)
        if "minsize" not in self.attrs:
            self.attrs["minsize"] = Vector2(0, 0)

    def on_add(self, cid):
        kwargs = self.children[cid][1]
        
        assert "pos" in kwargs
        assert isinstance(kwargs["pos"], Vector2)

    def on_remove(self, cid):
        pass

    def getWidgetsToRender(self):
        # print([i[0] for i in self.children], self.children)
        return [i[0] for i in self.children if i is not None]

    def getChildPosition(self, child):
        cid = self.getChildID(child)
        attrs = self.children[cid][1]

        return attrs["pos"]

    def getDimensions(self):
        dim = Vector2(0, 0)
        for child, attrs in self.children:
            new_dim = attrs["pos"] + child.getDimensions()
            if new_dim.x > dim.x:
                dim.x = new_dim.x
            if new_dim.y > dim.y:
                dim.y = new_dim.y
        if dim.x > self.attrs["maxsize"].x:
            dim.x = self.attrs["maxsize"].x
        if dim.y > self.attrs["maxsize"].y:
            dim.y = self.attrs["maxsize"].y

        if dim.x < self.attrs["minsize"].x:
            dim.x = self.attrs["minsize"].x
        if dim.y < self.attrs["minsize"].y:
            dim.y = self.attrs["minsize"].y
        
        return dim

class TableLayout(Layout):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        assert "dim" in self.attrs
        assert "maxsize" in self.attrs
        if "margin" not in self.attrs:
            self.attrs["margin"] = Vector2(3, 3)

        self.table = [[-1 for _ in range(self.attrs["dim"].x)] for _ in range(self.attrs["dim"].y)]
        self.update_counter = 0
        self.last_update_counter = 0

        self._col_widths = []
        self._row_heights = []

        self.minimum_col_widths = [0 for _ in range(self.attrs["dim"].x)]
        self.minimum_row_heights = [0 for _ in range(self.attrs["dim"].y)]
        
        self.is_col_expanding = [False for _ in range(self.attrs["dim"].x)]
        self.is_row_expanding = [False for _ in range(self.attrs["dim"].y)]

    def setRowExpanding(self, r, b):
        self.is_row_expanding[r] = b

    def setColExpanding(self, c, b):
        self.is_col_expanding[c] = b

    def setMinimumColumnSize(self, c, s):
        self.minimum_col_widths[c] = s

    def setMinimumRowSize(self, r, s):
        self.minimum_row_heights[r] = s

    def getWidgetsToRender(self):
        res = []
        for i in self.table:
            for j in i:
                if j > -1:
                    res += self.children[j][0].getWidgetsToRender()
        return res

    def on_add(self, cid):
        attrs = self.children[cid][1]

        assert "pos" in attrs
        self.table[attrs["pos"].y][attrs["pos"].x] = cid

    def on_remove(self, cid):
        attrs = self.children[cid][1]

        self.table[attrs["pos"].y][attrs["pos"].x] = -1

    def setChildAttribute(self, c, k, v):
        self.update_counter += 1
        super().setChildAttribute(c, k, v)

    def getDimensions(self):
        if self.last_update_counter != self.update_counter:
            self._updateTableData()
        
        return Vector2(sum(self._col_widths), sum(self._row_heights))

    def getChildPosition(self, child):
        # print(self.children, child)
        cid = self.getChildID(child)

        if "_pos" in self.children[cid][1]:
            if self.children[cid][1]["_update_counter"] == self.update_counter:
                return self.children[cid][1]["_pos"]

        # If one cell has updated then you have to regenerate the whole table (this can be optimised)
        self._updateTableData()

        return self.children[cid][1]["_pos"]

    def _updateTableData(self):
        self._row_heights = []
        for ty, row in enumerate(self.table):
            maxy = self.minimum_row_heights[ty]
            for tx, cell in enumerate(row):
                if cell == -1:
                    continue
                cy = self.children[cell][0].getDimensions().y
                if cy > maxy:
                    maxy = cy
            self._row_heights.append(maxy + self.attrs["margin"].y * 2)
        
        self._col_widths = []
        for tx in range(len(self.table[0])):
            maxx = self.minimum_col_widths[tx]
            for ty in range(len(self.table)):
                cell = self.table[ty][tx]
                if cell == -1:
                    continue
                cx = self.children[cell][0].getDimensions().x
                if cx > maxx:
                    maxx = cx
            self._col_widths.append(maxx + self.attrs["margin"].x * 2)

        size_leftover = 0
        cnt = 0
        for i, x in enumerate(self.is_col_expanding):
            if not x:
                size_leftover += self._col_widths[i]
            else:
                cnt += 1
        size_leftover = self.attrs["maxsize"].x - size_leftover
        for i, x in enumerate(self.is_col_expanding):
            if x:
                self._col_widths[i] = max(self._col_widths[i], size_leftover // cnt)
        size_leftover = 0
        cnt = 0
        for i, x in enumerate(self.is_row_expanding):
            if not x:
                size_leftover += self._row_heights[i]
            else:
                cnt += 1
        size_leftover = self.attrs["maxsize"].y - size_leftover
        for i, x in enumerate(self.is_row_expanding):
            if x:
                self._row_heights[i] = max(self._row_heights[i], size_leftover // cnt)

        for ty, row in enumerate(self.table):
            for tx, cell in enumerate(row):
                self.children[cell][1]["_update_counter"] = self.update_counter
                self.children[cell][1]["_pos"] = Vector2(sum(self._col_widths[:tx]) + self.attrs["margin"].x, sum(self._row_heights[:ty]) + self.attrs["margin"].y)

        self.last_update_counter = self.update_counter

class Label(Widget):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        assert "fontname" in kwargs
        assert "fontsize" in kwargs
        assert "color" in kwargs
        assert "text" in kwargs

    def render(self):
        pos = self.getTopLevelPosition()
        self.context.draw_text(self.attrs["fontname"], self.attrs["fontsize"], self.attrs["text"], self.attrs["color"], pos)

    def getDimensions(self):
        return self.context.get_text_dimensions(self.attrs["fontname"], self.attrs["fontsize"], self.attrs["text"])

class ImageWidget(Widget):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        assert "image" in kwargs

    def render(self):
        pos = self.getTopLevelPosition()
        self.context.draw_image(self.attrs["image"], pos)

    def getDimensions(self):
        return Vector2(self.attrs["image"].w, self.attrs["image"].h)

class Entry(Layout):

    SHIFT_KEY_MAP = {
        '`': '~', '1': '!', '2': '@', '3': '#',
        '4': '$', '5': '%', '6': '^', '7': '&',
        '8': '*', '9': '(', '0': ')', '-': '_',
        '=': '+', '[': '{', ']': '}', '\\': '|',
        ';': ':', "'": '"', ',': '<', '.': '>',
        '/': '?'
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        assert "width" in kwargs
        assert "fontname" in kwargs
        assert "fontsize" in kwargs
        assert "color" in kwargs
        self.size  = Vector2(kwargs["width"], ctx.get_text_dimensions(kwargs["fontname"], kwargs["fontsize"], "Q").y)

        self.back = ImageWidget(ctx, self, image=ctx.scale_image(ctx.load_image("entry.png"), Vector2(self.size.x + 8, self.size.y + 8)))
        self.back.bind(EventType.KEYHELD, self.on_key_held)

        self.front = Label(ctx, self, fontname=kwargs["fontname"], fontsize=kwargs["fontsize"], text="", color=kwargs["color"])
        self.front.bind(EventType.KEYHELD, self.on_key_held)
        
        self.cursor_widget = Line(ctx, self, start=Vector2(4, 4), end=Vector2(4, self.size.y + 4), color=[255, 255, 255])

        self.text = ""
        self.scroll = 0
        self.cursor = 0
        self.cursorx = 0

        self.add(self.back)
        self.add(self.front)
        # Prevent new widgets from being added
        self.add = lambda *__, **_: None
        self.remove = lambda *__, **_: None

    def on_add(self, cid):
        pass

    def on_remove(self, cid):
        pass

    def getDimensions(self):
        return self.size + Vector2(8, 8)

    def getWidgetsToRender(self):
        if self.focused:
            return [self.back, self.front, self.cursor_widget]
        else:
            return [self.back, self.front]

    def getChildPosition(self, child):
        if child is self.cursor_widget:
            return Vector2(self.cursorx - self.cursor_widget.getDimensions().x // 2, 0)

        if child is self.back:
            return Vector2(0, 0)
        return Vector2(4, 4)

    def on_key_held(self, back, e):
        if e.type == EventType.KEYHELD:
            if e.value < 0:
                # Special key
                if e.value == SpecialKeys.LARR:
                    self.cursor -= 1
                    if self.cursor < 0:
                        self.cursor = 0
                elif e.value == SpecialKeys.RARR:
                    self.cursor += 1
                    if self.cursor > len(self.text):
                        self.cursor = len(self.text)
            else:
                # Normal key
                special_keys = self.context.get_special_keys()
                
                if e.value == b"\b"[0]:
                    if self.scroll > 0:
                        self.scroll -= 1
                    if self.cursor > 0:
                        self.cursor -= 1
                    self.text = self.text[:self.cursor] + self.text[self.cursor+1:]
                elif e.value in b"\r\n":
                    pass
                else:
                    s = chr(e.value)
                    if (SpecialKeys.LSHFT in special_keys) or (SpecialKeys.RSHFT in special_keys):
                        s = self.SHIFT_KEY_MAP.get(s, s.upper())
                    if self.cursor > len(self.text):
                        self.text += s
                    else:
                        self.text = self.text[:self.cursor] + s + self.text[self.cursor:]
                    self.cursor += 1

            while 1:
                self.updateText()
                if self.cursorx > self.size.x:
                    self.scroll += 1
                elif self.cursorx < 0:
                    self.scroll -= 1
                else:
                    break

            if self.scroll < 0:
                self.scroll = 0

    def updateText(self):
        self.front.attrs["text"] = ""
        i = 0
        self.cursorx = None
        if self.cursor - self.scroll == 0:
            self.cursorx = 0
        while self.front.getDimensions().x < self.size.x:
            if (i + self.scroll) >= len(self.text):
                break
            self.front.attrs["text"] += self.text[i + self.scroll]
            if self.cursor - self.scroll - 1 == i:
                self.cursorx = self.front.getDimensions().x
            i += 1

        if self.cursorx is None:
            if self.cursor - self.scroll < 0:
                self.cursorx = -10000000
            else:
                self.cursorx = 10000000

class Line(Widget):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        assert "start" in self.attrs
        assert "end" in self.attrs
        assert "color" in self.attrs

    def getDimensions(self):
        start = self.attrs["start"]
        end   = self.attrs["end"]
        return Vector2(max(start.x, end.x), max(start.y, end.y))

    def render(self):
        pos = self.getTopLevelPosition()
        start = self.attrs["start"]
        end   = self.attrs["end"]
        self.context.draw_line(start + pos, end + pos, self.attrs["color"])

class NullWidget(Widget):

    def __init__(self):
        pass

    def bind(self, event_type, callback):
        pass

    def getWidgetsToRender(self):
        return []

    def render(self):
        pass

    def setFocus(self):
        pass

    def clearFocus(self):
        pass

    def onEvent(self, event):
        pass

    def getDimensions(self):
        return Vector2(0, 0)
