from snip import Snip, State
from menu import Toolbar, NEW_SNIP
import pygame

SCREEN_COLOR = (100, 100, 100)
MIN_SCREEN_SIZE = (230,120)

def main():
    running = True
    WINDOW = pygame.display.set_mode(MIN_SCREEN_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("Snippy")
    ICON = pygame.image.load("icon.png").convert_alpha()
    pygame.display.set_icon(ICON)

    toolbar = Toolbar()
    current_snip = None
    while running:
        WINDOW.fill(SCREEN_COLOR)

        for event in pygame.event.get():
            if current_snip != None:
                # Get snipping coordinates.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_LEFT:
                    # Mouse was pressed down
                    # SNIPPING: Get first corner of rectangle
                    if current_snip.state == State.SNIPPING:
                        current_snip.set_left_upper(pygame.mouse.get_pos())
                        current_snip.state = State.CROPPING
                elif event.type == pygame.MOUSEBUTTONUP and event.button == pygame.BUTTON_LEFT:
                    # Mouse was released after pressed down
                    # SNIPPING: Get last corner of rectangle
                    if current_snip.state == State.CROPPING:
                        current_snip.set_right_lower(pygame.mouse.get_pos())
                        current_snip.state = State.CROP

                # Image view navigation.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_MIDDLE:
                    # VIEWING CROPPED image: pan and track mouse change position if hold mouse wheel.
                    if current_snip.window_state != State.PANNING:
                        current_snip.set_pivot(pygame.mouse.get_pos())
                        current_snip.window_state = State.PANNING
                elif event.type == pygame.MOUSEBUTTONUP and event.button == pygame.BUTTON_MIDDLE:
                    # stop pan if release mouse wheel.
                    current_snip.window_state = State.IDLE
                if current_snip.state == State.CROPPED:
                    # VIEWING CROPPED image: set zoom in and out with mouse wheel.
                    if (event.type == pygame.KEYDOWN and event.key == pygame.K_EQUALS) or \
                        (event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_WHEELUP):
                        current_snip.increment_zoom(1.5)
                    elif (event.type == pygame.KEYDOWN and event.key == pygame.K_MINUS) or \
                        (event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_WHEELDOWN):
                        current_snip.increment_zoom(0.75)

            # Create snip and crop if new snip.
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_1) or event.type == NEW_SNIP:
                current_snip = Snip()
            # Check which buttons on toolbar are pressed.
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_LEFT:
                toolbar.update(WINDOW, True)
                
            # Quit window if press ESC or exit.
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                pygame.quit()
                return

        # Only display toolbar if not snipping screenshot.
        if current_snip != None:
            current_snip.update(WINDOW)
            if current_snip.state == State.SNIPPING or current_snip.state == State.CROPPING:
                toolbar.visible = False
            else:
                toolbar.visible = True

        toolbar.update(WINDOW, False)
        pygame.display.update()


if __name__ == "__main__":
    main()

