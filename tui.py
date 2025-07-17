import curses
import subprocess
import sys
import math

def check_admin():
    """Checks for administrative privileges."""
    try:
        # Check if the script is running with admin privileges.
        subprocess.check_call(['pkexec', 'true'])
        return True
    except subprocess.CalledProcessError:
        return False

def rgb_to_xterm(r, g, b):
    """Converts an RGB color to the nearest color in the xterm 256-color palette."""
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return round(((r - 8) / 247) * 24) + 232

    # Find the nearest color in the 6x6x6 color cube
    color_index = 16 \
        + (36 * round(r / 255 * 5)) \
        + (6 * round(g / 255 * 5)) \
        + round(b / 255 * 5)
    return color_index

def edit_color(stdscr, initial_color):
    """
    Provides a TUI for interactively editing an RGB color with sliders.

    Args:
        stdscr: The standard screen object provided by curses.
        initial_color: A list [r, g, b] with the starting color.

    Returns:
        A list [r, g, b] with the final selected color.
    """
    color = list(initial_color)
    selected_channel = 0  # 0 for R, 1 for G, 2 for B

    # Define a curses color pair for the preview swatch. ID 10 is arbitrary.
    # We will redefine its color in the loop.
    curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_BLACK)

    while True:
        stdscr.clear()
        stdscr.addstr(0, 2, "Color Picker", curses.A_BOLD)
        stdscr.addstr(2, 2, "Use UP/DOWN to select a channel (R, G, B).")
        stdscr.addstr(3, 2, "Use LEFT/RIGHT to change the value.")
        stdscr.addstr(4, 2, "Press ENTER to confirm or 'q' to cancel.")

        # Display sliders for R, G, B
        channel_names = ["Red", "Green", "Blue"]
        for i, name in enumerate(channel_names):
            style = curses.A_REVERSE if i == selected_channel else curses.A_NORMAL
            bar_length = 50
            fill_length = int((color[i] / 255) * bar_length)
            bar = '█' * fill_length + '─' * (bar_length - fill_length)
            stdscr.addstr(6 + i * 2, 4, f"{name.ljust(6)}: [{bar}] {color[i]}", style)

        # Update and display the color preview swatch
        xterm_color_index = rgb_to_xterm(color[0], color[1], color[2])
        # curses.init_color is not universally supported, so we map to a 256-color palette.
        # We re-initialize the color pair on each update.
        curses.init_pair(10, curses.COLOR_WHITE, xterm_color_index)
        stdscr.addstr(6, 65, "Preview:", curses.A_BOLD)
        for i in range(4):
            stdscr.addstr(7 + i, 65, " " * 10, curses.color_pair(10))

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected_channel = (selected_channel - 1) % 3
        elif key == curses.KEY_DOWN:
            selected_channel = (selected_channel + 1) % 3
        elif key == curses.KEY_LEFT:
            color[selected_channel] = max(0, color[selected_channel] - 5)
        elif key == curses.KEY_RIGHT:
            color[selected_channel] = min(255, color[selected_channel] + 5)
        elif key == ord('\n'):  # Enter
            return color
        elif key == ord('q'):
            return initial_color

def main(stdscr):
    """
    Initializes the main TUI and handles user input.

    Args:
        stdscr: The standard screen object provided by curses.
    """
    if not check_admin():
        subprocess.call(['pkexec', 'python3', __file__])
        return

    curses.curs_set(0)
    # Check if the terminal supports colors
    if curses.has_colors():
        curses.start_color()
    
    selected_color = [0, 255, 0]
    path = "/sys/devices/platform/asus-nb-wmi/leds/asus::kbd_backlight/kbd_rgb_mode"
    
    modes = {"Static": "0", "Breathing": "1", "Color Cycle": "2"}
    speeds = {"Slow": "0", "Medium": "1", "Fast": "2"}
    
    current_mode_idx = 1
    current_speed_idx = 1
    
    # Define the sections the user can navigate through
    sections = ['mode', 'speed', 'color', 'submit']
    focused_section_idx = 0
    
    while True:
        stdscr.clear()
        
        stdscr.addstr(0, 2, "ASUS TUF Backlight Changer", curses.A_BOLD)
        stdscr.addstr(2, 2, "Use UP/DOWN arrows to change selection, TAB to switch sections.")
        stdscr.addstr(3, 2, "Press ENTER to select, and 'q' to quit.")
        
        # --- Mode Section ---
        is_focused = sections[focused_section_idx] == 'mode'
        stdscr.addstr(5, 2, "Mode:", curses.A_UNDERLINE | (curses.A_BOLD if is_focused else 0))
        for i, (text, val) in enumerate(modes.items()):
            style = curses.A_REVERSE if i == current_mode_idx and is_focused else curses.A_NORMAL
            stdscr.addstr(6 + i, 4, text, style)

        # --- Speed Section ---
        is_focused = sections[focused_section_idx] == 'speed'
        stdscr.addstr(10, 2, "Speed:", curses.A_UNDERLINE | (curses.A_BOLD if is_focused else 0))
        for i, (text, val) in enumerate(speeds.items()):
            style = curses.A_REVERSE if i == current_speed_idx and is_focused else curses.A_NORMAL
            stdscr.addstr(11 + i, 4, text, style)

        # --- Color Section ---
        is_focused = sections[focused_section_idx] == 'color'
        style = curses.A_REVERSE if is_focused else curses.A_NORMAL
        stdscr.addstr(15, 2, "Color:", curses.A_UNDERLINE | (curses.A_BOLD if is_focused else 0))
        stdscr.addstr(16, 4, f"RGB: {selected_color[0]}, {selected_color[1]}, {selected_color[2]}", style)
        stdscr.addstr(17, 4, "(Press Enter to edit)", curses.A_DIM)

        # --- Submit Section ---
        is_focused = sections[focused_section_idx] == 'submit'
        style = curses.A_REVERSE if is_focused else curses.A_NORMAL
        stdscr.addstr(19, 2, "Submit Changes", style)

        stdscr.refresh()
        key = stdscr.getch()

        if key == ord('q'):
            break
        elif key == ord('\t'): # TAB key
            focused_section_idx = (focused_section_idx + 1) % len(sections)
        elif key == curses.KEY_UP:
            if sections[focused_section_idx] == 'mode':
                current_mode_idx = (current_mode_idx - 1) % len(modes)
            elif sections[focused_section_idx] == 'speed':
                current_speed_idx = (current_speed_idx - 1) % len(speeds)
        elif key == curses.KEY_DOWN:
            if sections[focused_section_idx] == 'mode':
                current_mode_idx = (current_mode_idx + 1) % len(modes)
            elif sections[focused_section_idx] == 'speed':
                current_speed_idx = (current_speed_idx + 1) % len(speeds)
        elif key == ord('\n'): # Enter
            focused_section = sections[focused_section_idx]
            if focused_section == 'color':
                selected_color = edit_color(stdscr, selected_color)
            elif focused_section == 'submit':
                mode_val = list(modes.values())[current_mode_idx]
                speed_val = list(speeds.values())[current_speed_idx]
                r, g, b = selected_color
                
                bash_command = f'echo "1 {mode_val} {r} {g} {b} {speed_val}" | tee {path}'
                try:
                    process = subprocess.Popen(['pkexec', 'bash', '-c', bash_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()
                    
                    stdscr.clear()
                    if process.returncode == 0:
                        stdscr.addstr(2, 2, "Success! Keyboard backlight updated.")
                    else:
                        stdscr.addstr(2, 2, "Error:", curses.A_BOLD)
                        stdscr.addstr(4, 2, f"Details: {stderr.decode()}")
                    stdscr.addstr(6, 2, "Press any key to continue.")
                    stdscr.getch()
                except Exception as e:
                    stdscr.clear()
                    stdscr.addstr(2, 2, "An exception occurred:", curses.A_BOLD)
                    stdscr.addstr(4, 2, str(e))
                    stdscr.addstr(6, 2, "Press any key to continue.")
                    stdscr.getch()

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except curses.error as e:
        print(f"Curses error: {e}")
        print("This might happen if your terminal doesn't support colors or certain features.")