import pygame
# for clipboard saving
import win32clipboard as clip
import win32con
from io import BytesIO
from PIL import Image

pygame.font.init() 
myfont = pygame.font.SysFont('Segoe UI', 18, bold=True)
COLOR_TEXT = (10, 10, 10)
COLOR_DARKER = (120, 120, 120)
COLOR_DARK = (180, 180, 180)
COLOR_LIGHT = (200, 200, 200)
NEW_SNIP = pygame.event.custom_type()

def set_setting(text):
    # Write to settings. Currently sets a single boolean saving Autocopy preference.
    f = open("settings.txt", "w")
    f.write(text)
    f.close()

def read_setting():
    #read settings. Currently a single boolean holding Autocopy preference.
    f = open("settings.txt", "r")
    return f.read()

# Holder for buttons to change prefernces, new snip, etc.
class Toolbar():
    def __init__(self):
        self.visible = True
        self.color = (220, 220, 220)
        self.height = 35
        # Add new buttons of NAME, (position), width, height.
        self.buttons = {"NewSnip":Button("New Snip", (10, 5), 100, 25),
                        "Save": Button("Copy", (120, 5), 100, 25),
                        "AutoCopy?": Button("AutoCopy?", (330, 5), 150, 25)}

    def draw(self, screen):
        # Draw toolbar as rectangle.
        width = pygame.display.get_surface().get_width()
        pygame.draw.rect(screen, self.color, pygame.Rect((0, 0), (width, self.height)))

    def update(self, screen, clicked):
        if self.visible:
            # Draw the toolbar.
            self.draw(screen)
            for button in self.buttons:
                # Draw each button.
                self.buttons[button].update(screen, clicked)

# Button for toolbar.
class Button():
    def __init__(self, text, topLeft, width, height):
        self.color = COLOR_LIGHT
        self.rect = pygame.Rect(topLeft[0], topLeft[1], width, height)
        self.width = width
        self.height = height

        # Keep button on "clicked" visual for some time after click.
        self.total_time = 0
        self.clicked_time = -1000

        self.text = text
        if text == "AutoCopy?":
            if read_setting() == "True":
                self.text = "AutoCopy: On"
            else:
                self.text = "AutoCopy: Off"
        self.text_rect = myfont.render(self.text, False, COLOR_TEXT)

    def hover(self):
        # mouse hover (true if hover, false if not) - change color on hover.
        # only change to hover color if not on click state visual.
        self.total_time += 5
        if self.total_time > self.clicked_time + 800:
            self.color = COLOR_LIGHT
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.color = COLOR_DARK
                return True 
        return False

    def clicked(self):
        self.color = COLOR_DARKER
        self.clicked_time = self.total_time
        # Change behavior depending on button.
        if self.text == "New Snip":
            # Make a new snip.
            pygame.event.post(pygame.event.Event(NEW_SNIP))
        elif self.text == "Copy":
            # save to windows clipboard
            img = Image.open("cropped.png")
            output = BytesIO()
            img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
            output.close()

            clip.OpenClipboard()
            clip.EmptyClipboard()
            clip.SetClipboardData(win32con.CF_DIB, data)
            clip.CloseClipboard()
        # Change text of button depending on setting, and save settings for Autocopy (whether to automatically copy image after snip.)
        elif self.text == "AutoCopy: On":
            global AUTO_COPY
            set_setting("False")
            self.text = "AutoCopy: Off"
            self.text_rect = myfont.render(self.text, False, COLOR_TEXT)
        elif self.text == "AutoCopy: Off":
            set_setting("True")
            self.text = "AutoCopy: On"
            self.text_rect = myfont.render(self.text, False, COLOR_TEXT)

        # idealing use file dialog to save image https://stackoverflow.com/questions/3579568/choosing-a-file-in-python-with-simple-dialog
        # https://www.geeksforgeeks.org/python-askopenfile-function-in-tkinter/
        # Will revisit this later.

    def draw(self, screen):
        # Draw button.
        pygame.draw.rect(screen, self.color, self.rect)
        # Center text in button.
        text_x = self.rect.center[0] - self.text_rect.get_rect().center[0]
        text_y = self.rect.center[1] - self.text_rect.get_rect().center[1]
        screen.blit(self.text_rect, (text_x, text_y))

    def update(self, screen, clicked):
        if self.hover() and clicked:
            self.clicked()

        self.draw(screen)