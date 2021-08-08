eidheim/tiny-process-library
==============================================

.. code-block:: TOML

    url = "git@gitlab.com:eidheim/tiny-process-library.git"
    name = "tiny-process"

    [tiny-process]
        target_type = "static library"
        [tiny-process.windows]
            sources = ["process.cpp", "process_win.cpp"]
        [tiny-process.linux]
            sources = ["process.cpp", "process_unix.cpp"]
        [tiny-process.osx]
            sources = ["process.cpp", "process_unix.cpp"]

    [examples]
        sources = ["examples.cpp"]
        dependencies = ["tiny-process"]

    [test-io]
        sources = ["tests/io_test.cpp"]
        dependencies = ["tiny-process"]

    [test-multithread]
        sources = ["tests/multithread_test.cpp"]
        dependencies = ["tiny-process"]

    [test-open-close]
        sources = ["tests/open_close_test.cpp"]
        dependencies = ["tiny-process"]