import os
from menu import read_setting

from PIL import ImageGrab
import pygame
from pygame.constants import KEYDOWN, K_1, K_ESCAPE
import ctypes
from ctypes import wintypes 
from enum import Enum

import math
# for clipboard saving
import win32clipboard as clip
import win32con
from io import BytesIO

OFFSET_CENTER = (50, 50)

class State(Enum):
    SNIPPING = 1
    CROPPING = 2
    CROP = 3
    CROPPED = 4

    # Window states
    # (NOTE: will only pan cropped image)
    IDLE = 5
    PANNING = 6
    ZOOMING = 7

# Get window position offset (on real screen) for when cropping.
# Get window position: https://python-forum.io/Thread-pygame-get-window-position http://www.akeric.com/blog/?page_id=814
# api docs: https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowrect
class Window_Info():
    def __init__(self):
        # pygame tracks the window handler, and makes it available
        self.window_handler = pygame.display.get_wm_info()["window"]
        # build a GetWindowRect
        self.get_window_rect = self.build_win_info_function()
    
    def build_win_info_function(self):
        builder = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    
        # 1==we're passing this in, 2==ctypes is passing it back to us
        flags = ((1, "hwnd"), (2, "lprect"))
    
        # now that we've described the function, we indicate where it exists so we can call it
        func = builder(("GetWindowRect", ctypes.windll.user32), flags)
        return func

    def get_window_position(self):
        position = {"upper": 0, "left": 0, "right": 0, "lower": 0}
        # get the current window info
        window_info = self.get_window_rect(self.window_handler)
        position["upper"] = window_info.top
        position["left"] = window_info.left
        position["right"] = window_info.right
        position["lower"] = window_info.bottom
        return position


class Snip:
    def __init__(self):
        self.state = State.SNIPPING
        self.crop_rectangle = {"left": 0, "upper": 0, "right": 0, "lower": 0}
        self.window_info = Window_Info()
        #self.prev_window_pos = self.window_info.get_window_position()
        self.grab_screen()

        self.window_state = State.IDLE
        self.pan_offset = (0, 0)
        self.zoom_scale = 1
        self.pivot = (0, 0)
        #self.previous_zoom_pos = (0, 0)

    def load(self, img):
        return pygame.image.load(img).convert_alpha()
 
    def grab_screen(self):
        # minimize screen to "hide" it
        pygame.display.set_mode((1,1), pygame.NOFRAME)

        # grab screen shot of entire screen
        screenshot = ImageGrab.grab()
        screenshot.save('screen_shot.png', 'PNG') 
        self.screenshot_img = self.load("screen_shot.png")

        # return to unminimized screen
        pygame.display.set_mode((700,600), pygame.RESIZABLE)
        # For now, cannot use fullscreen due to bug https://github.com/pygame/pygame/issues/2360 
        # Get full screen size of user
        # user32 = ctypes.windll.user32
        # user32.SetProcessDPIAware()
        # width = user32.GetSystemMetrics(0)
        # height = user32.GetSystemMetrics(1)
        # pygame.display.set_mode((width - 100, height - 100), pygame.RESIZABLE)
        #pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    # SNIPPING before mouseDown
    # display screen
    def snip(self, screen):
        # set screen shot
        screen.blit(self.screenshot_img, (0, 0))

        # draw overlay
        overlay_color = (220, 220, 220)
        overlay = pygame.Surface((pygame.display.get_surface().get_width(), pygame.display.get_surface().get_height()))
        overlay.set_alpha(50)
        overlay.fill(overlay_color)
        screen.blit(overlay, (0,0))

    # CROPPING after mouseDown, before mouseUp
    # Crop on top of screen AND draw rectangle
    def cropping(self, screen):
        screen.blit(self.screenshot_img, (0, 0))

        # draw rectangle
        self.draw_rect(screen)

    # CROP if mouseUp
    # save crop
    def crop(self, screen):
        # on mouseUp, change to CROPPED state and save crop
        self.crop_pic(screen, "cropped.png")
        self.state = State.CROPPED
        self.cropped(screen)

        # change window size to crop size and padding, but at least minimum size
        image = self.cropped_img.get_rect()
        width = max(image.width + 100, 225)

        # reposition to previous position - workaround to fullscreen bug setting window outside screen https://github.com/pygame/pygame/issues/2360 
        # pygame.display.quit()
        # pygame.quit()
        # os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (self.prev_window_pos["left"], self.prev_window_pos["upper"])
        # pygame.init()
        # pygame.display.init()
        pygame.display.set_mode( (width, image.height + 100), pygame.RESIZABLE)

    # self.state == State.CROPPED after mouseUp
    # display crop
    def cropped(self, screen):
        #image = self.cropped_img

        # Clamp maximum zoom at 150 to prevent memory error (note: smaller image = can zoom in more, bigger = zoom in less)
        # small images max: 150-200. medium/big image max: 57
        # TODO: maybe scale only a small portion of original image that will be visible -> disregard rest (calculate and crop)

        # Workaround is use pillow to resize an image file in separate name, and only resize by factor of resize image, not original
        # CON: if big zoom, may still be scaling large image -- not necessarily work, could even be slower
        # https://opensource.com/life/15/2/resize-images-python
        # https://stackoverflow.com/questions/4373141/dealing-with-huge-potentially-over-30000x30000-images-in-python

        # Maybe: get width and height, clamp to max. (prevent scaling too large image)
        
        #scale_image = pygame.transform.scale(image, (img_width, img_height))  # NOTE: may want to separately save transformed image and recale only on zoom,
        # not every frame so not as resource intensive.
        screen.blit(self.cropped_zoomed_img, (self.pan_offset[0] + OFFSET_CENTER[0], self.pan_offset[1] + OFFSET_CENTER[1]))

        #TODO: Also display cropped image size in px, on window.

    def set_pan_offset(self):
        # pan only if already cropped
        offset_x = pygame.mouse.get_pos()[0] - self.pivot[0] 
        offset_y = pygame.mouse.get_pos()[1] - self.pivot[1]
        self.pan_offset = (offset_x, offset_y)

    def increment_zoom(self, factor):
        # temporary fix to not being able to scale too much - out of memory issue.
        img_width = self.cropped_img.get_width()*self.zoom_scale
        img_height = self.cropped_img.get_height()*self.zoom_scale
        #print(img_width, img_height)

        if factor > 1 and (img_height > 4000 or img_width > 4000):
            return False # cannot zoom in more, or overflow
        # otherwise, zoom in more, or zoom out
        self.zoom_scale *= factor

        img_width = int(self.cropped_img.get_width()*self.zoom_scale)
        img_height = int(self.cropped_img.get_height()*self.zoom_scale)
        self.cropped_zoomed_img = pygame.transform.scale(self.cropped_img, (img_width, img_height)) 

        # To zoom relative to mouse and NOT topleft corner of image
        #print(self.cropped_img.get_rect().center) # doesn't work since we blit a copy of image, not image itself
        #self.pan_offset = (self.pan_offset[0]-pygame.mouse.get_pos()[0], self.pan_offset[1]-pygame.mouse.get_pos()[1])

        # GOAL: get mouse position on image itself
        # subtract mouse position relative to image topleft in game.
        # Image position (topleft): (self.pan_offset[0] + OFFSET_CENTER[0], self.pan_offset[1] + OFFSET_CENTER[1])
        # img.get_Width and get_height * zoom_scale <- factor?

        # Mouse position over image. https://stackoverflow.com/questions/53085568/how-do-i-get-the-mouse-position-on-a-pygame-scaled-surface
        # print((pygame.mouse.get_pos()[0] - self.pan_offset[0] - OFFSET_CENTER[0]) / self.zoom_scale,
        #         (pygame.mouse.get_pos()[1] - self.pan_offset[1] - OFFSET_CENTER[1])  / self.zoom_scale)

        # current_zoom_pos = ((pygame.mouse.get_pos()[0] - self.pan_offset[0] - OFFSET_CENTER[0]) / self.zoom_scale,
        #         (pygame.mouse.get_pos()[1] - self.pan_offset[1] - OFFSET_CENTER[1])  / self.zoom_scale)

        # # READ THIS: zoom at mouse https://medium.com/@benjamin.botto/zooming-at-the-mouse-coordinates-with-affine-transformations-86e7312fd50b
        # if factor > 1: 
        #     sign = -1
        # else:
        #     sign = 1
        # self.pan_offset = (self.pan_offset[0] + sign*current_zoom_pos[0], 
        #                     self.pan_offset[1] + sign*current_zoom_pos[1])

        # self.pan_offset = (self.pan_offset[0] - -1*(current_zoom_pos[0] - self.previous_zoom_pos[0]), 
        #                     self.pan_offset[1] - -1*(current_zoom_pos[1] - self.previous_zoom_pos[1]))

        #self.previous_zoom_pos = current_zoom_pos
        # self.previous_zoom_pos
        
        #self.pan_offset = ( (pygame.mouse.get_pos()[0] - self.pan_offset[0] - OFFSET_CENTER[0]) / self.zoom_scale,
        #        (pygame.mouse.get_pos()[1] - self.pan_offset[1] - OFFSET_CENTER[1])  / self.zoom_scale)

        # perfect: zoom and pan https://stackoverflow.com/questions/41656176/tkinter-canvas-zoom-move-pan/48137257#48137257

    def set_pivot(self, point):
        pivot_x = point[0] - self.pan_offset[0]
        pivot_y = point[1] - self.pan_offset[1]
        self.pivot = (pivot_x, pivot_y)

    def set_left_upper(self, point):
        self.crop_rectangle["left"], self.crop_rectangle["upper"] = point

    def set_right_lower(self, point):
        self.crop_rectangle["right"], self.crop_rectangle["lower"] = point

    def crop_pic(self, screen, filepath):
        offset = self.window_info.get_window_position()
        offset_left = offset["left"] + 8 # extra offset due to OS stuff
        offset_upper = offset["upper"] + 1 # extra offset due to OS stuff

        # make sure to crop original screen, without rectangle
        screen.blit(self.screenshot_img, (0, 0))
        pygame.display.flip()

        # Then save crop
        cropped = None
        if self.set_corners():
            # Valid rectangle cropped
            cropped = ImageGrab.grab(bbox=(self.crop_rectangle["left"] + offset_left, 
                                                self.crop_rectangle["upper"] + offset_upper + 30, # 30 is window bar size
                                                self.crop_rectangle["right"] + offset_left, 
                                                self.crop_rectangle["lower"] + offset_upper + 30))
        else:
            # invalid rectangle cropped (size 0). Just crop single pixel.
            cropped = ImageGrab.grab(bbox=(0, 0, 1, 1))
        cropped.save(filepath, 'PNG')
        if read_setting() == "True":
            self.save_to_clipboard(cropped)
        self.cropped_img = self.load(filepath)
        self.cropped_zoomed_img = self.cropped_img

    # save to windows clipboard
    def save_to_clipboard(self, img):    
        output = BytesIO()
        img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()

        clip.OpenClipboard()
        clip.EmptyClipboard()
        clip.SetClipboardData(win32con.CF_DIB, data)
        clip.CloseClipboard()

    # draws bounding rectangle of area to be cropped
    def draw_rect(self, screen):
        x, y = pygame.mouse.get_pos()
        left = self.crop_rectangle["left"]
        upper = self.crop_rectangle["upper"]

        # Specific swap for drawing rectangle to specify left vs right, up vs down, based on mins/max
        if left > x:
            #swap
            temp = x
            x = left
            left = temp
        if y < upper:
            #swap
            temp = y
            y = upper
            upper = temp

        # draw rectangle
        rect_color = (220, 100, 150)
        pygame.draw.rect(screen, rect_color, (left, upper, x - left, y - upper), width = 1)
    
    # Swap rectangle corners to match description 
    # Returns whether rectangle is valid (not size of 0)
    def set_corners(self):
        if self.crop_rectangle["left"] > self.crop_rectangle["right"]:
            self.swap("left", "right")
        if self.crop_rectangle["lower"] < self.crop_rectangle["upper"]:
            self.swap("lower", "upper")
        # Check size is not 0
        if (self.crop_rectangle["left"] == self.crop_rectangle["right"]) or (self.crop_rectangle["lower"] == self.crop_rectangle["upper"]):
            return False # invalid size.
        return True

    def swap(self, one, two):
        temp = self.crop_rectangle[one]
        self.crop_rectangle[one] = self.crop_rectangle[two]
        self.crop_rectangle[two] = temp

    # change action and screen based on state
    def update(self, screen):
        if self.state == State.SNIPPING:
            self.snip(screen)
        elif self.state == State.CROPPING:
            self.cropping(screen)
        elif self.state == State.CROP:
            self.crop(screen)
        elif self.state == State.CROPPED:
            self.cropped(screen)
        
        if self.state == State.CROPPED and self.window_state == State.PANNING:
            self.set_pan_offset()

