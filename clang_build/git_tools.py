import logging as _logging
import subprocess as _subprocess

_LOGGER = _logging.getLogger("clang_build.clang_build")


def needs_download(url, download_directory, version=None):
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
                    _LOGGER.debug(
                        f"External sources folder exists but local url='{local_url}', while target url='{url}'"
                    )
                    return True

                if version:
                    checkout_version(version, download_directory, url)
                else:
                    get_latest_changes(download_directory)

                _LOGGER.debug(
                    f"External sources found in '{download_directory.resolve()}'"
                )

                return False
        else:
            error_message = f"Tried to download '{url}' to '{download_directory.resolve()}', but '{download_directory.resolve()}' is a file."
            raise RuntimeError(error_message)

    return True


def clone_repository(url, download_directory, recursive):
    _LOGGER.debug(f"Downloading external target to '{download_directory}'")
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
        _LOGGER.exception(error_message)
        raise RuntimeError(error_message)

    _LOGGER.debug(f"External target downloaded")


def checkout_version(version, repository, url):
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
        _LOGGER.exception(error_message)
        raise RuntimeError(error_message)

def get_latest_changes(repository):
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
        _LOGGER.exception(error_message)
        raise RuntimeError(error_message)
