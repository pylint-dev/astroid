# Copyright (c) 2020 rioj7

"""
Run the following script to generate the string to parse in the transform method

import turtle
def _make_global_funcs(functions, cls):
  funcs = []
  for methodname in functions:
    method = getattr(cls, methodname)
    paramslist, argslist = turtle.getmethparlist(method)
    if paramslist == "": continue
    funcs.append(f"def {methodname}{paramslist}: return")
  return funcs
funcs = []
funcs.extend(_make_global_funcs(turtle._tg_screen_functions, turtle._Screen))
funcs.extend(_make_global_funcs(turtle._tg_turtle_functions, turtle.Turtle))
print('\n'.join(funcs))
"""

import astroid

def transform():
  # these are the functions for turtle in Python v3.8.5
  return astroid.parse('''
def addshape(name, shape=None): return
def bgcolor(*args): return
def bgpic(picname=None): return
def bye(): return
def clearscreen(): return
def colormode(cmode=None): return
def delay(delay=None): return
def exitonclick(): return
def getcanvas(): return
def getshapes(): return
def listen(xdummy=None, ydummy=None): return
def mainloop(): return
def mode(mode=None): return
def numinput(title, prompt, default=None, minval=None, maxval=None): return
def onkey(fun, key): return
def onkeypress(fun, key=None): return
def onkeyrelease(fun, key): return
def onscreenclick(fun, btn=1, add=None): return
def ontimer(fun, t=0): return
def register_shape(name, shape=None): return
def resetscreen(): return
def screensize(canvwidth=None, canvheight=None, bg=None): return
def setup(width=0.5, height=0.75, startx=None, starty=None): return
def setworldcoordinates(llx, lly, urx, ury): return
def textinput(title, prompt): return
def title(titlestring): return
def tracer(n=None, delay=None): return
def turtles(): return
def update(): return
def window_height(): return
def window_width(): return
def back(distance): return
def backward(distance): return
def begin_fill(): return
def begin_poly(): return
def bk(distance): return
def circle(radius, extent=None, steps=None): return
def clear(): return
def clearstamp(stampid): return
def clearstamps(n=None): return
def clone(): return
def color(*args): return
def degrees(fullcircle=360.0): return
def distance(x, y=None): return
def dot(size=None, *color): return
def down(): return
def end_fill(): return
def end_poly(): return
def fd(distance): return
def fillcolor(*args): return
def filling(): return
def forward(distance): return
def get_poly(): return
def getpen(): return
def getscreen(): return
def get_shapepoly(): return
def getturtle(): return
def goto(x, y=None): return
def heading(): return
def hideturtle(): return
def home(): return
def ht(): return
def isdown(): return
def isvisible(): return
def left(angle): return
def lt(angle): return
def onclick(fun, btn=1, add=None): return
def ondrag(fun, btn=1, add=None): return
def onrelease(fun, btn=1, add=None): return
def pd(): return
def pen(pen=None, **pendict): return
def pencolor(*args): return
def pendown(): return
def pensize(width=None): return
def penup(): return
def pos(): return
def position(): return
def pu(): return
def radians(): return
def right(angle): return
def reset(): return
def resizemode(rmode=None): return
def rt(angle): return
def seth(to_angle): return
def setheading(to_angle): return
def setpos(x, y=None): return
def setposition(x, y=None): return
def settiltangle(angle): return
def setundobuffer(size): return
def setx(x): return
def sety(y): return
def shape(name=None): return
def shapesize(stretch_wid=None, stretch_len=None, outline=None): return
def shapetransform(t11=None, t12=None, t21=None, t22=None): return
def shearfactor(shear=None): return
def showturtle(): return
def speed(speed=None): return
def st(): return
def stamp(): return
def tilt(angle): return
def tiltangle(angle=None): return
def towards(x, y=None): return
def turtlesize(stretch_wid=None, stretch_len=None, outline=None): return
def undo(): return
def undobufferentries(): return
def up(): return
def width(width=None): return
def write(arg, move=False, align='left', font=('Arial', 8, 'normal')): return
def xcor(): return
def ycor(): return
''')

astroid.register_module_extender(astroid.MANAGER, "turtle", transform)
