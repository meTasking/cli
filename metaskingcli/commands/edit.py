import ruamel.yaml as yaml
import tempfile
import subprocess

from metaskingcli.args import CliArgs
from metaskingcli.api.log import read, update


def edit_file(editor_cmd: str, filename: str) -> None:
    # Reslove full path to editor
    editor_cmd = subprocess.run(["which", editor_cmd], capture_output=True) \
        .stdout.decode("utf-8").strip()
    # Open the file in the editor
    subprocess.run([editor_cmd, filename])


def execute(args: CliArgs) -> int:
    assert args.edit is not None
    log = read(args.server, args.edit.id)

    # Preprocessing
    if log["category"] is not None:
        log["category"] = log["category"]["name"]
    if log["task"] is not None:
        log["task"] = log["task"]["name"]

    # Dump the log to yaml and allow the user to edit it
    with tempfile.NamedTemporaryFile(mode="w+", suffix='.yml') as f:
        yaml.dump(log, f)
        f.flush()
        edit_file(args.edit.editor, f.name)
        f.seek(0)
        log = yaml.load(f, Loader=yaml.Loader)

    # Postprocessing
    log_id = log["id"]
    del log["id"]

    # Update the log
    update(
        args.server,
        log_id,
        create_category=True,
        create_task=True,
        **log
    )
    return 0
