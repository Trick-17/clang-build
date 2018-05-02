import os
print("before compile here ", os.getcwd())
with open("version.h", 'w') as f:
    f.write(
        "#define VERSION_MAJOR 1\n"
        "#define VERSION_MINOR 2\n"
        "#define VERSION_PATCH 0")