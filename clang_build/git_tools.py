import logging as _logging
import subprocess as _subprocess

_LOGGER = _logging.getLogger("clang_build.clang_build")

def needs_download(url, download_directory):
    if download_directory.exists():
        if download_directory.is_dir():
            if any(download_directory.iterdir()):

                ###### CHECK ORIGIN AND VERSION using """url"""!!!!
                _LOGGER.info(
                    f"External project sources found in '{download_directory}'"
                )

                return False
        else:
            ### There is a file called like the download folder
            error_message = ""
            raise RuntimeError(error_message)  ##### NEEDS content

    return True

def clone_repository(url, download_directory, recursive):
    _LOGGER.info(
        f"Downloading external project to '{download_directory}'"
    )
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
            f"Error trying to download external project. Message "
            + e.output
        )
        _LOGGER.exception(error_message)
        raise RuntimeError(error_message)

    _LOGGER.info(f"External project downloaded")

def checkout_version(version, repository, url):
    try:
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
        _LOGGER.exception(error_message)
        raise RuntimeError(error_message)
