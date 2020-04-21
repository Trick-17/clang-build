from .build_type import BuildType
from . import platform as _platform

def _parse_flags_config(options, build_type, flags_kind='flags'):
    flags_dicts   = []
    compile_flags = []
    link_flags    = []

    if flags_kind in options:
        flags_dicts.append(options.get(flags_kind, {}))

    flags_dicts.append(options.get(_platform.PLATFORM, {}).get(flags_kind, {}))

    for fdict in flags_dicts:
        compile_flags += fdict.get('compile', [])
        link_flags    += fdict.get('link', [])

        if build_type != BuildType.Default:
            compile_flags += fdict.get(f'compile_{build_type}', [])

    return compile_flags, link_flags


class BuildFlags:
    DEFAULT_COMPILE_FLAGS = {
        BuildType.Default: ["-Wall", "-Wextra", "-Wpedantic", "-Wshadow", "-Werror"],
        BuildType.Release: ["-O3", "-DNDEBUG"],
        BuildType.RelWithDebInfo: ["-O3", "-g3", "-DNDEBUG"],
        BuildType.Debug: [
            "-Og",
            "-g3",
            "-DDEBUG",
            "-fno-optimize-sibling-calls",
            "-fno-omit-frame-pointer",
            "-fsanitize=address",
            "-fsanitize=undefined",
        ],
        BuildType.Coverage: [
            "-Og",
            "-g3",
            "-DDEBUG",
            "-fno-optimize-sibling-calls",
            "-fno-omit-frame-pointer",
            "-fsanitize=address",
            "-fsanitize=undefined",
            "--coverage",
            "-fno-inline",
        ],
    }
    DEFAULT_LINK_FLAGS = {
        BuildType.Debug: ["-fsanitize=address", "-fsanitize=undefined"],
        BuildType.Coverage: [
            "-fsanitize=address",
            "-fsanitize=undefined",
            "--coverage",
            "-fno-inline",
        ],
    }

    def __init__(
        self, build_type, default_compile_flags=False, default_link_flags=False
    ):
        # TODO: Store default flags separately
        self.default_compile_flags = []
        self.default_link_flags = []

        self.compile_flags_private = []
        self.link_flags_private = []

        self.compile_flags_interface = []
        self.link_flags_interface = []

        self.compile_flags_public = []
        self.link_flags_public = []

        if default_compile_flags:
            self.default_compile_flags = self.DEFAULT_COMPILE_FLAGS[BuildType.Default]
            # self.compile_flags_private += DEFAULT_COMPILE_FLAGS.get(BuildType.Default, [])
            if build_type != BuildType.Default:
                self.default_compile_flags = self.DEFAULT_COMPILE_FLAGS.get(
                    build_type, []
                )
                # self.compile_flags_private += DEFAULT_COMPILE_FLAGS.get(build_type, [])

        if default_link_flags:
            self.default_link_flags = self.DEFAULT_LINK_FLAGS.get(build_type, [])
            # self.link_flags_private += DEFAULT_LINK_FLAGS.get(build_type, [])

    def make_private_flags_public(self):
        self.compile_flags_public += self.compile_flags_private
        self.compile_flags_private = []
        self.link_flags_public += self.link_flags_private
        self.link_flags_private = []

    def apply_public_flags(self, target):
        self.compile_flags_private += target.compile_flags_public
        self.link_flags_private += target.link_flags_public

    def forward_public_flags(self, target):
        self.compile_flags_public += target.compile_flags_public
        self.link_flags_public += target.link_flags_public

    def apply_interface_flags(self, target):
        self.compile_flags_private += target.compile_flags_interface
        self.link_flags_private += target.link_flags_interface

    def forward_interface_flags(self, target):
        self.compile_flags_interface += target.compile_flags_interface
        self.link_flags_interface += target.link_flags_interface

    def add_target_flags(self, config, build_type):
        # Own private flags
        cf, lf = _parse_flags_config(config, build_type, "flags")
        self.compile_flags_private += cf
        self.link_flags_private += lf

        # Own interface flags
        cf, lf = _parse_flags_config(config, build_type, "interface-flags")
        self.compile_flags_interface += cf
        self.link_flags_interface += lf

        # Own public flags
        cf, lf = _parse_flags_config(config, build_type, "public-flags")
        self.compile_flags_public += cf
        self.link_flags_public += lf

    def final_compile_flags_list(self):
        return self._generate_flag_list(
            self.compile_flags_private + self.compile_flags_public
        )

    def final_link_flags_list(self):
        return self._generate_flag_list(
            self.link_flags_private + self.link_flags_public
        )

    def _generate_flag_list(self, flags):
        # TODO: The below line (making flags unique) is still wrong. Should be removed!
        flags = list(dict.fromkeys(flags))
        return list(str(" ".join(flags)).split())

    def add_bundling_flags(self):
        self.link_flags_private += _platform.PLATFORM_BUNDLING_LINKER_FLAGS
