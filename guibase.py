import abc

class Vector2():

    __slots__ = ["x", "y"]

    def __init__(self, x, y):
        assert isinstance(x, int)
        assert isinstance(y, int)
        
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        return Vector2(self.x * other.x, self.y * other.y)

    def __div__(self, other):
        return Vector2(self.x // other.x, self.y // other.y)

    def __repr__(self):
        return "%d %d" % (self.x, self.y)

class Image():

    def __init__(self, data, w, h):
        self.data = data
        self.w = w
        self.h = h

class GUIObject(metaclass=abc.ABCMeta):

    def __init__(self):
        self.context = Context.current_ctx
        self.parent = None
        self.focused = False
        self.name = ""

    @abc.abstractmethod
    def getWidgetsToRender(self):
        ...

    def getTopLevelPosition(self):
        if self.parent is None:
            return Vector2(0, 0)
        else:
            return self.parent.getChildPosition(self) + self.parent.getTopLevelPosition()

    @abc.abstractmethod
    def onEvent(self, event):
        ...

    @abc.abstractmethod
    def render(self):
        ...

    @abc.abstractmethod
    def getDimensions(self):
        ...

    def clearFocus(self):
        self.focused = False

    def setFocus(self):
        l = []
        c = self
        while c.parent is not None:
            l.append(c)
            c = c.parent

        c.clearFocus()
        for i in l:
            i.focused = True

class CallNextEventHandler:
    def __new__(*_):
        raise NotImplementedError

class Widget(GUIObject, metaclass=abc.ABCMeta):

    def __init__(self, parent, **kwargs):
        assert isinstance(parent, Layout)
        
        super().__init__()
        self.parent = parent
        self.attrs = kwargs
        self.bound_events = {}

    def bind(self, event_type, callback):
        """DO NOT USE"""
        arr = [callback] + self.bound_events.get(event_type, [])
        self.bound_events[event_type] = arr

    def getWidgetsToRender(self):
        return [self]

    @abc.abstractmethod
    def render(self):
        ...

    def setFocus(self):
        super().setFocus()
        self.onEvent(Event(EventType.FOCUSED, None))

    def clearFocus(self):
        if self.focused:
            self.onEvent(Event(EventType.UNFOCUSED, None))
        super().clearFocus()

    def onEvent(self, event):
        if event.type in self.bound_events:
            for i in self.bound_events[event.type]:
                if i(self, event) is not CallNextEventHandler:
                    break

class Layout(GUIObject, metaclass=abc.ABCMeta):

    def __init__(self, parent, **kwargs):
        if parent is not None:
            assert isinstance(parent, Layout)

        super().__init__()
        self.parent = parent
        self.attrs = kwargs
        self.children = []
        self.bound_events = {}

    def bind(self, event_type, callback):
        arr = [callback] + self.bound_events.get(event_type, [])
        self.bound_events[event_type] = arr

    def onEvent(self, event):
        # print()
        # print("onEvent", self.name)
        if event.type in self.bound_events:
            for i in self.bound_events[event.type]:
                if i(self, event) is not CallNextEventHandler:
                    break
        
        # Get list of all widgets in rendering order
        widgets = self.getWidgetsToRender()
        
        if event.type in {EventType.LEFTCLICK, EventType.RIGHTCLICK}:
            clicked_widget = None
            for i in widgets:
                pos, size = i.getTopLevelPosition(), i.getDimensions()
                if (pos.x + size.x) >= event.value.x >= pos.x:
                    if (pos.y + size.y) >= event.value.y >= pos.y:
                        # print(event.type, i.name, "onEvent due to in range")
                        clicked_widget = i
                        # "break" intentionally missing
                    # else:
                        # print(i.name, "not in range")
                # else:
                    # print(i.name, "not in range")

            # print("clicked_widget is", clicked_widget.name)
            if clicked_widget is None:
                return
            
            clicked_widget.setFocus()
            clicked_widget.onEvent(event)

        else:
            for i in widgets:
                if i.focused:
                    # print(i.name, "onEvent")
                    i.onEvent(event)
                # else:
                    # print(i.name)

    def clearFocus(self):
        super().clearFocus()
        for i in self.children:
            i[0].clearFocus()

    @abc.abstractmethod
    def getWidgetsToRender(self):
        ...

    @abc.abstractmethod
    def getChildPosition(self, child):
        ...

    def render(self):
        for i in self.getWidgetsToRender():
            i.render()

    def add(self, child, **kwargs):
        for i, x in enumerate(self.children):
            if x is None:
                self.children[i] = child, kwargs
                cid = i
                break

        else:
            cid = len(self.children)
            self.children.append((child, kwargs))

        self.on_add(cid)

    def setChildAttribute(self, c, k, v):
        self.children[self.getChildID(c)][1][k] = v

    def getChildAttribute(self, c, k):
        return self.children[self.getChildID(c)][1][k]

    def remove(self, child):
        cid = self.getChildID(child)
        self.on_remove(cid)
        self.children[cid] = None
        return

    def getChildID(self, child):
        for i, x in enumerate(self.children):
            if x[0] is child:
                return i
        
        raise LookupError

    @abc.abstractmethod
    def on_add(self, cid):
        ...

    @abc.abstractmethod
    def on_remove(self, cid):
        ...

class Context(abc.ABC):

    current_ctx = None

    def __new__(cls, *_):
        Context.current_ctx = object.__new__(cls)
        return Context.current_ctx

    @abc.abstractmethod
    def flush(self):
        ...

    @abc.abstractmethod
    def draw_text(self, fontname, fontsize, text, Vector2):
        ...

    @abc.abstractmethod
    def draw_image(self, image, Vector2):
        ...

    @abc.abstractmethod
    def load_image(self, path_or_file, namehint=None):
        ...

    @abc.abstractmethod
    def get_text_dimensions(self, fontname, fontsize, text):
        ...
    
    @abc.abstractmethod
    def mainloop(self, toplevel):
        ...

    @abc.abstractmethod
    def tick(self, toplevel):
        ...

    @abc.abstractmethod
    def get_special_keys(self):
        ...

    @abc.abstractmethod
    def draw_line(self, start, end):
        ...

    @abc.abstractmethod
    def scale_image(self, image, newres):
        ...

class EventType:
    
    def __new__(self):
        raise TypeError("Cannot instantiate EventType")
 
    KEYDOWN      = 0
    KEYUP        = 1
    KEYHELD      = 2
    LEFTCLICK    = 3
    RIGHTCLICK   = 4
    SCROLLUP     = 5
    SCROLLDOWN   = 6
    LEFTRELEASE  = 7
    RIGHTRELEASE = 8

    # Special, never fired directly
    FOCUSED    = 1000
    UNFOCUSED  = 1001

class Event():

    def __init__(self, type, value):
        self.type = type
        self.value = value

class SpecialKeys():

    def __new__(self):
        raise TypeError("Cannot instantiate SpecialKeys")

    LCTRL = -1
    RCTRL = -2
    LSHFT = -3
    RSHFT = -4
    LALT  = -5
    RALT  = -6
    
    LARR  = -7
    RARR  = -8
    UARR  = -9
    DARR  = -10
