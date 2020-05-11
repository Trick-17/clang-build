import logging as _logging
import subprocess as _subprocess


def needs_download(url, download_directory, logger, version=None):
    if download_directory.exists():
        if download_directory.is_dir():
            if any(download_directory.iterdir()):
                try:
                    local_url = _subprocess.check_output(
                        ["git", "config", "--get", "remote.origin.url"],
                        stderr=_subprocess.PIPE,
                        encoding="utf-8",
                        cwd=download_directory,
                    ).splitlines()[0]
                except _subprocess.CalledProcessError:
                    return True

                if local_url != url:
                    logger.debug(
                        f"External sources folder exists but local url='{local_url}', while target url='{url}'"
                    )
                    return True

                if version:
                    checkout_version(version, download_directory, url, logger)
                else:
                    get_latest_changes(download_directory, logger)

                logger.debug(
                    f"External sources found in '{download_directory.resolve()}'"
                )

                return False
        else:
            error_message = f"Tried to download '{url}' to '{download_directory.resolve()}', but '{download_directory.resolve()}' is a file."
            raise RuntimeError(error_message)

    return True


def clone_repository(url, download_directory, recursive, logger):
    logger.debug(f"Downloading external sources to '{download_directory}'")
    download_directory.mkdir(parents=True, exist_ok=True)
    try:
        clone_command = ["git", "clone"]

        if recursive:
            clone_command += ["--recurse-submodules"]

        _subprocess.run(
            clone_command + [url, str(download_directory)],
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            encoding="utf-8",
        )
    except _subprocess.CalledProcessError as e:
        error_message = (
            f"Error trying to download external target. Message " + e.output
        )
        logger.exception(error_message)
        raise RuntimeError(error_message)

    logger.debug(f"External sources downloaded")


def checkout_version(version, repository, url, logger):
    try:
        _subprocess.run(
            ["git", "fetch"],
            cwd=repository,
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            encoding="utf-8",
        )
        _subprocess.run(
            ["git", "checkout", version],
            cwd=repository,
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            encoding="utf-8",
        )
    except _subprocess.CalledProcessError as e:
        error_message = (
            f"Error trying to checkout version '{version}' from url '{url}'. Message "
            + e.output
        )
        logger.exception(error_message)
        raise RuntimeError(error_message)


def get_latest_changes(repository, logger):
    try:
        _subprocess.run(
            ["git", "pull"],
            cwd=repository,
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            encoding="utf-8",
        )
    except _subprocess.CalledProcessError as e:
        error_message = (
            f"Unabled to get latest changes in repository '{repository}'. Message "
            + e.output
        )
        logger.exception(error_message)
        raise RuntimeError(error_message)


def download_sources(url, directory, logger, version=None, clone_recursively=True):
    """Download sources using git.
    """
    # Check if directory is already present and non-empty
    if needs_download(url, directory, logger, version):
        logger.info(
            f"downloading external sources to '{str(directory.resolve())}'"
        )
        clone_repository(
            url, directory, clone_recursively, logger
        )
        if version:
            checkout_version(version, directory, url, logger)
        else:
            get_latest_changes(directory, logger)

    # Otherwise we download the sources
    else:
        logger.debug(f"external sources found in '{str(directory.resolve())}'")