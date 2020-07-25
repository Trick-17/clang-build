from .build_type import BuildType
from . import platform as _platform

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
        self.compile_default = []
        self.link_default = []

        self.compile_private = []
        self.link_private = []

        self.compile_interface = []
        self.link_interface = []

        self.compile_public = []
        self.link_public = []

        self._build_type = build_type

        if default_compile_flags:
            self.compile_default = self.DEFAULT_COMPILE_FLAGS[BuildType.Default]
            # self.compile_private += DEFAULT_COMPILE_FLAGS.get(BuildType.Default, [])
            if build_type != BuildType.Default:
                self.compile_default = self.DEFAULT_COMPILE_FLAGS.get(
                    build_type, []
                )
                # self.compile_private += DEFAULT_COMPILE_FLAGS.get(build_type, [])

        if default_link_flags:
            self.link_default = self.DEFAULT_LINK_FLAGS.get(build_type, [])
            # self.link_private += DEFAULT_LINK_FLAGS.get(build_type, [])

    def make_private_flags_public(self):
        self.compile_public += self.compile_private
        self.compile_private = []
        self.link_public += self.link_private
        self.link_private = []

    def apply_public_flags(self, target):
        self.compile_private += target.build_flags.compile_public
        self.link_private += target.build_flags.link_public

    def forward_public_flags(self, target):
        self.compile_public += target.build_flags.compile_public
        self.link_public += target.build_flags.link_public

    def apply_interface_flags(self, target):
        self.compile_private += target.build_flags.compile_interface
        self.link_private += target.build_flags.link_interface

    def forward_interface_flags(self, target):
        self.compile_interface += target.build_flags.compile_interface
        self.link_interface += target.build_flags.link_interface

    def add_target_flags(self, config):
        # Own private flags
        cf, lf = self._parse_flags_config(config, "flags")
        self.compile_private += cf
        self.link_private += lf

        # Own interface flags
        cf, lf = self._parse_flags_config(config, "interface-flags")
        self.compile_interface += cf
        self.link_interface += lf

        # Own public flags
        cf, lf = self._parse_flags_config(config, "public-flags")
        self.compile_public += cf
        self.link_public += lf

    def add_bundling_flags(self):
        self.link_private += _platform.PLATFORM_BUNDLING_LINKER_FLAGS

    def final_compile_flags_list(self):
        # TODO: Add max_dialect and plattform specific flags here as well
        #       Need to see how we get around the target-type-specific flags issue
        return list(dict.fromkeys(self.compile_private + self.compile_public))

    def final_link_flags_list(self):
        return list(dict.fromkeys(self.link_private + self.link_public))

    def _parse_flags_config(self, options, flags_kind='flags'):
        flags_dicts   = []
        compile_flags = []
        link_flags    = []

        if flags_kind in options:
            flags_dicts.append(options.get(flags_kind, {}))

        flags_dicts.append(options.get(_platform.PLATFORM, {}).get(flags_kind, {}))

        for fdict in flags_dicts:
            compile_flags += fdict.get('compile', [])
            link_flags    += fdict.get('link', [])

            if self._build_type != BuildType.Default:
                compile_flags += fdict.get(f'compile_{self._build_type}', [])

        return compile_flags, link_flags
