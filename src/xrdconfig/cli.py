"""Command Line Interface entry point for xrdconfig"""
from __future__ import annotations

import difflib
import fileinput
import shutil
from pathlib import Path
from typing import Any

import typer
from plumbum import CommandNotFound, local

app = typer.Typer()


def _get_cconfig() -> local:
    try:
        cconfig = local.get("cconfig")
    except CommandNotFound as error:
        typer.echo("cconfig not found - please make sure xrootd is installed", err=True)
        raise typer.Exit(1) from error
    return cconfig


def _copy_to_temporary_directory(config_path: Path, copy_to: Path) -> None:
    """Copy the configuration file and config.d directory to a temporary directory"""
    temp_dir = copy_to
    if temp_dir.exists():
        # clean existing temporary directory
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()

    config_file = local.path(config_path)
    config_file.copy(temp_dir)

    config_d = config_file.dirname / "config.d"
    if config_d.exists():
        config_d.copy(temp_dir / "config.d")


def _replace_continue_statement(config_path: Path, new_path: Path) -> None:
    """Replace the continue statement in the configuration file with new location"""
    new_confd_path = new_path / "config.d"
    with fileinput.input(files=(new_path / config_path.name), inplace=True) as file:
        for line in file:
            if line.startswith("continue"):
                print(f"continue {new_confd_path}")  # noqa: T201
            else:
                print(line, end="")  # noqa: T201


def _process_cconfig_output(output: str) -> dict[str, str]:
    """Process the output of the cconfig command"""
    result = {}
    for line in output.splitlines():
        if line.startswith("Config continuing with") or line.startswith("continue "):
            continue
        try:
            var, value = line.split(" ", 1)
        except ValueError:
            typer.echo(f"Unexpected output from cconfig: {line}", err=True)
            continue
        value = value.strip(" ")
        result[var] = value
    return result


@app.command()
def display(
    config: str = typer.Argument("/etc/xrootd/xrootd-clustered.cfg"),
    output_type: str = typer.Option("plain|json", "--output", "-o"),
) -> None:
    """Display the current configuration"""
    cconfig = _get_cconfig()

    # copy the config and config.d files to a temporary directory
    # replace the continue statement in the config file with temporary directory
    # run cconfig on the temporary directory
    # display the output
    # remove the temporary directory
    config_path: Path = local.path(config)
    copy_to = local.path("/tmp/xrdconfig")
    _copy_to_temporary_directory(config_path, copy_to)
    _replace_continue_statement(config_path, copy_to)
    # cconfig puts the output in stderr
    _, _, stderr = cconfig["-c"].run(copy_to / config_path.name)
    result = _process_cconfig_output(stderr)

    if output_type == "json":
        typer.echo(result)
    else:
        for var, value in sorted(result.items()):
            typer.echo(f"{var} {value}")


@app.command()
def diff(
    config1: str = typer.Argument("/etc/xrootd/xrootd-clustered.cfg"),
    config2: str = typer.Argument("/etc/xrootd/xrootd-clustered.cfg"),
) -> None:
    """Display the differences between the current configuration and the last saved version"""
    # https://stackoverflow.com/questions/19120489/compare-two-files-report-difference-in-python
    cconfig = _get_cconfig()
    config_path1: Path = local.path(config1)
    config_path2: Path = local.path(config2)
    copy_to_1 = local.path("/tmp/xrdconfig_diff1")
    copy_to_2 = local.path("/tmp/xrdconfig_diff2")

    _copy_to_temporary_directory(config_path1, copy_to_1)
    _copy_to_temporary_directory(config_path2, copy_to_2)
    _replace_continue_statement(config_path1, copy_to_1)
    _replace_continue_statement(config_path2, copy_to_2)

    _, _, stderr1 = cconfig["-c"].run(copy_to_1 / config_path1.name)
    _, _, stderr2 = cconfig["-c"].run(copy_to_2 / config_path2.name)
    result1 = _process_cconfig_output(stderr1)
    result2 = _process_cconfig_output(stderr2)
    plain_lines1 = [value for _, value in sorted(result1.items())]
    plain_lines2 = [value for _, value in sorted(result2.items())]

    diff_list = list(
        difflib.unified_diff(
            plain_lines1, plain_lines2, fromfile=config1, tofile=config2, n=0
        )
    )
    if not diff_list:
        typer.echo("No differences found")
    else:
        typer.echo("\n".join(diff))


@app.command()
def remote_diff() -> None:
    """Same as diff but for remote files"""
    typer.echo("Not implemented yet")


def main() -> Any:
    """Entry point for the "xrdconfig" command"""
    return app()
