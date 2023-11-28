import ruamel.yaml as yaml
import tempfile
import subprocess

from metaskingcli.args import CliArgs
from metaskingcli.api.log import read, update
from metaskingcli.api.record import delete as delete_record


def edit_file(editor_cmd: str, filename: str) -> None:
    # Reslove full path to editor
    editor_cmd = subprocess.run(["which", editor_cmd], capture_output=True) \
        .stdout.decode("utf-8").strip()
    # Open the file in the editor
    subprocess.run([editor_cmd, filename])


async def execute(args: CliArgs) -> int:
    assert args.edit is not None
    log = await read(args.server, args.edit.id)

    # Preprocessing
    if log.get("category") is not None:
        log["category"] = log["category"]["name"]
    if log.get("task") is not None:
        log["task"] = log["task"]["name"]
    if log.get("flags") is not None:
        flags = []
        for flag in log["flags"]:
            flags.append(flag["name"])
        log["flags"] = flags

    record_ids = [
        record["id"] for record in log["records"]
    ]

    # Dump the log to yaml and allow the user to edit it
    with tempfile.NamedTemporaryFile(mode="w+", suffix='.yml') as f:
        y = yaml.YAML(typ="safe")
        y.default_flow_style = False
        y.dump(log, f)
        f.flush()
        edit_file(args.edit.editor, f.name)
        f.seek(0)
        log = y.load(f)

    # Postprocessing
    log_id = log["id"]
    del log["id"]

    # Update the log
    await update(
        args.server,
        log_id,
        create_category=True,
        create_task=True,
        **log
    )

    # Delete records that are not in the edited log
    new_record_ids = {
        record["id"] for record in log["records"]
    }
    for record_id in record_ids:
        if record_id in new_record_ids:
            continue

        # Ask the user for confirmation
        if not args.edit.force:
            print(f"Delete record {record_id}? [y/N] ", end="")
            answer = input()
            if answer.lower() != "y":
                continue

        # Delete the record
        await delete_record(args.server, record_id)
    return 0
