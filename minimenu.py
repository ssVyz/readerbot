"""
- Copy/paste this file into your repo.
- Import one of the relevant menu classes: Selection_menu,

"""





##########################################
### Minimenu: tiny CLI menu for python ###
##########################################


import sys
import os
from pathlib import Path

try:
    import msvcrt
    sys_code = "win"
except:
    try:
        import termios
        import tty
        sys_code = "lin"
    except:
        raise Exception("Can not determine system for input method")


### The wrapper class that contains shared methods

class Menu:

    def __init__(self, input_list: list = None, header = None, footer = None, padding: int = 0):
        self.padding = padding
        self.display_frame = []
        self.pointer = 0
        self.limit = 0
        self.header = header
        self.footer = footer
        self.result = []
        self.simple_result = None

        if input_list is not None:
            self.input_list = input_list
        else:
            self.input_list = []

    def add_item(self, new_item: str):
        if isinstance(new_item, str):
            self.input_list.append(new_item)
        else:
            raise Exception("Tried adding item that is not a string")
        
    def load_list(self, new_list: list):
        if isinstance(new_list, list):
            self.input_list = new_list
        else:
            raise Exception("Tried loading something other than a list")
    
    def build_frame(self):
        pass
        
    def show_frame(self):
        pass

    def move_pointer(self, key):
        pass

    def build_result(self):
        pass


    def present(self, simple: bool = False):
        confirmed_select = False
        self.limit = len(self.input_list)-1

        while confirmed_select == False:

            self.build_frame()
            self.show_frame()
            #print(f"Current pointer: {self.pointer}, current limit: {self.limit}")
            key = decode_key(get_next_key())
            if key == "enter":
                confirmed_select = True
            if key == "quit":
                return None
            if key == "select":
                return "select"
            else:
                if key is not None:
                    self.move_pointer(key)
        
        self.build_result()
        self.simple_result = self.pointer
        if simple == True:
            return self.simple_result
        return self.result

    def insert_padding(self):
        for pad in range(self.padding):
                print("")



### Subclass for the selection menu
    
class Selection_menu(Menu):

    def __init__(self, input_list: list = None, header = None, footer = None, padding: int = 0):
        super().__init__(input_list, header, footer, padding)

    def build_frame(self):
        self.display_frame = []
        size_of_list = len(self.input_list)
        for i in range(0, size_of_list):
            a = ""
            if i == self.pointer:
                a = " --> "
            else:
                a = "     "
            b = self.input_list[i]
            self.display_frame.append((a, b))
        
    def show_frame(self):
        clear_screen()
        print("")
        if self.header is not None:
            print(self.header)
            print("")
        for i in range(0, len(self.display_frame)):
            self.insert_padding()
            print(f"{self.display_frame[i][0]} {self.display_frame[i][1]}")
            
        print("")
        self.insert_padding()
        if self.footer is not None:
            print(self.footer)
            print("")

    def move_pointer(self, key):
        upper_bounds = self.limit
        if key == "up":
            self.pointer -= 1 if self.pointer > 0 else self.pointer
        if key == "left":
            self.pointer -= 1 if self.pointer > 0 else self.pointer
        if key == "down":
            self.pointer += 1
        if key == "right":
            self.pointer += 1
        if self.pointer > upper_bounds:
            self.pointer = upper_bounds

    def build_result(self):
        result_fields = len(self.input_list)
        result_list = []
        for i in range(result_fields):
            if i == self.pointer:
                result_list.append(1)
            else:
                result_list.append(0)
        self.result = result_list
        
        

class Checkbox_menu(Menu):

    def __init__(self, input_list: list = None, header = None, footer = None, padding: int = 0):
        super().__init__(input_list, header, footer, padding)
        self.checked = []

    def update_checked(self, checked_list: list[int]):
        if len(self.input_list) == len(checked_list):
            self.checked = checked_list
        else:
            raise Exception("tried to set pre-checked list that is not the same length as the input list.")

    def build_frame(self):
        self.display_frame = []
        size_of_list = len(self.input_list)
        if self.checked == []:
            for _ in range(len(self.input_list)):
                self.checked.append(0)
        elif len(self.checked) != len(self.input_list):
            raise Exception("input list and checked list are not the same length")
        
        for i in range(0, size_of_list):
            a = ""
            if i == self.pointer:
                a = " --> "
            else:
                a = "     "
            
            b = ""
            if self.checked[i] == 1:
                b = " [X] "
            else:
                b = " [ ] "

            c = ""
            c = self.input_list[i]
            self.display_frame.append((a, b, c))
        

    def show_frame(self):
        clear_screen()
        print("")
        if self.header is not None:
            print(self.header)
            print("")
        for i in range(0, len(self.display_frame)):
            self.insert_padding()
            print(f"{self.display_frame[i][0]} {self.display_frame[i][1]} {self.display_frame[i][2]}")
        print("")
        self.insert_padding()
        if self.footer is not None:
            print(self.footer)
            print("")

    def move_pointer(self, key):
        upper_bounds = self.limit
        if key == "up":
            self.pointer -= 1 if self.pointer > 0 else self.pointer
        if key == "left":
            self.checked[self.pointer] = 0
        if key == "down":
            self.pointer += 1
        if key == "right":
            self.checked[self.pointer] = 1
        if self.pointer > upper_bounds:
            self.pointer = upper_bounds

    def build_result(self):
        self.result = self.checked



### Miniexplore block ###

class Work_folder:

    def __init__(self, start_folder):

        self.current_dir = Path(start_folder)
        if self.current_dir.exists() == False:
            self.current_dir = Path.cwd()

        
    def select_folder(self):
        contents_list = []
        name_list = []
        for item in self.current_dir.iterdir():
            contents_list.append(item)
            name_list.append(item.name)

        contents_list.append(self.current_dir.parent)
        name_list.append("cd ..")
                    
        mim = Selection_menu(name_list, f"Current folder: {str(self.current_dir)} \nSelect a folder or file", "Use arrow keys to navigate. Use enter to select a file. Use s-key to select current folder. Use q-key to exit without selecting.")
        result = mim.present(True)

        if result == None:
            return None
        elif result == "select":
            return "select"
        else:
            selected_item = contents_list[result]

        #print(f"You selected {selected_item}")
        
        return selected_item
        


    def go_to_parent(self):

        self.current_dir = self.current_dir.parent

        self.select_folder()



# Miniexplore function

def select_file(starting_folder=(Path.cwd())):

    wf = Work_folder(starting_folder)
    result_file_path = ""

    last_item = starting_folder
    while True:

        current_item = wf.select_folder()
        if current_item == None:
            return None
        elif current_item == "select":
            return last_item
        elif current_item.is_dir() == True:
            wf.current_dir = current_item
            last_item = current_item
        else:
            return str(current_item)







### Keyboard operrations ###

def empty_key_buffer():
    if sys_code == "win":
        while msvcrt.kbhit():
            msvcrt.getch()
    elif sys_code == "lin":
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)

def get_next_key() -> str:
    if sys_code == "win":
        empty_key_buffer()
        current_key = msvcrt.getch()
        if current_key == b'\xe0':
            return msvcrt.getch()
        return current_key
    
    if sys_code == "lin":
        return get_linux_key()

    
def decode_key(key):
    if sys_code == "win":
        if key == b'H':
            return "up"
        elif key == b'P':
            return "down"
        elif key == b'K':
            return "left"
        elif key == b'M':
            return "right"
        elif key == b'\r':
            return "enter"
        elif key == b's':
            return "select"
        elif key == b'q':
            return "quit"
        else:
            return None
        
    elif sys_code == "lin":
        return key


def get_linux_key():
    empty_key_buffer()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    tty.setcbreak(fd)

    chars = sys.stdin.read(1)
    output = None
    if chars == '\x1b':
        chars += sys.stdin.read(1)
        chars += sys.stdin.read(1)

        if chars == '\x1b[A':
            output = "up"
        elif chars == '\x1b[B':
            output = "down"
        elif chars == '\x1b[C':
            output = "right"
        elif chars == '\x1b[D':
            output = "left"
    
    elif chars == '\n' or chars == '\r':
        output = "enter"
    elif chars == 's':
        output = "select"
    elif chars == 'q':
        output = "quit"

    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return output


def clear_screen():
    if sys_code == "win":
        os.system("cls")
    if sys_code == "lin":
        os.system("clear")



### Running tests. Not run if called from the outside ###

def main():


    print("Running the test suite:")
    print(f"Detected system: {sys.platform}")
    
    '''
    key = get_next_key()
    print(key)
    print(decode_key(key))
    '''



if __name__ == "__main__":
    main()





