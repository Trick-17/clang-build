nikoreun/tinygrad
==============================================

.. code-block:: TOML

    name = "tinygrad"
    url = "git@github.com:nikoreun/tinygrad.git"

    [tinygrad]
        target_type = "static library"
        public_dependencies = ["Eigen"]

    [example-autoencoder]
        sources = ["examples/test_autoencoder.cpp"]
        dependencies = ["tinygrad"]

    [example-logistic-regression]
        sources = ["examples/test_logistic_regression.cpp"]
        dependencies = ["tinygrad"]

    [example-neural-network]
        sources = ["examples/test_neural_network.cpp"]
        dependencies = ["tinygrad"]

    [Eigen]
        url = "https://gitlab.com/libeigen/eigen.git"
        target_type = "header only"
        [Eigen.flags]
            compile = ["-DEIGEN_HAS_STD_RESULT_OF=0", "-Wno-deprecated-declarations", "-Wno-shadow"]
            compile_release = ["-DEIGEN_NO_DEBUG"]