codeplea/genann
==============================================

.. code-block:: TOML

    url = "git@github.com:codeplea/genann.git"
    name = "genann"

    [genann]
        target_type = "static library"
        sources = ["genann.c.c"]

    [example1]
        sources = ["example1.c"]
        dependencies = ["genann"]

    [example2]
        sources = ["example2.c"]
        dependencies = ["genann"]

    [example3]
        sources = ["example3.c"]
        dependencies = ["genann"]

    [example4]
        sources = ["example4.c"]
        dependencies = ["genann"]

    [test]
        sources = ["test.c"]
        dependencies = ["genann"]