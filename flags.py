import imgui

WINDOW_OVERLAY = (
    imgui.WINDOW_NO_TITLE_BAR |
    imgui.WINDOW_NO_RESIZE |
    imgui.WINDOW_NO_SCROLLBAR |
    imgui.WINDOW_NO_COLLAPSE |
    imgui.WINDOW_NO_BACKGROUND
)

WINDOW_PLAYER_LIST = (
    imgui.WINDOW_NO_TITLE_BAR |
    imgui.WINDOW_NO_RESIZE |
    imgui.WINDOW_ALWAYS_AUTO_RESIZE |
    imgui.WINDOW_NO_MOVE |
    imgui.WINDOW_NO_SAVED_SETTINGS |
    imgui.WINDOW_NO_SCROLLBAR
)



SCREEN_W               = 1920
SCREEN_H               = 1080
AVATAR_SIZE            = 22
MAX_NAME_LEN           = 15
FONT_SIZE              = 15
FONT_NAME              = "14-font.ttf"
WDA_EXCLUDEFROMCAPTURE = 0x00000011
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400