import yaml

from bot.bot import _merge
from bot.utils.exporters import HackMDExporter

NOTES_TEMPLATE = """CO & Staff meeting {month}
===

###### tags: `zeusops` `meeting`

###### date : {date}

[Previous notes](https://www.zeusops.com/meetings)

## Present
### COs
-
### Staff
- Capry
- Gehock
- Matt
- Miller

## Preface

### Notes

### TODO

- Assignee
    - [ ] Todo item 1

"""

NOTES_TEMPLATE_NO_TITLE = """###### date : {date}

[Previous notes](https://www.zeusops.com/meetings)

## Present
### COs
-
### Staff
- Capry
- Gehock
- Matt
- Miller

## Preface

### Notes

### TODO

- Assignee
    - [ ] Todo item 1

"""


ALL_NOTES = """# Zeusops CO & Staff meeting notes

###### tags: `zeusops` `meeting`

- [2023-07](https://hackmd.io/@zeusops/rysL2QNo2)
- [2023-06](https://hackmd.io/@zeusops/SyNYKB1Yh)
- [2023-05](https://hackmd.io/@zeusops/B1D55OMLh)
"""


def get_config() -> dict[str, dict]:
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
    with open("config_local.yaml") as f:
        local_config = yaml.safe_load(f)

    return _merge(config, local_config)


config = get_config()
hackmd_config = config["cogs"]["meetingnotes"]["hackmd"]


def test_get_title():
    text = NOTES_TEMPLATE.format(month="2021-07", date="2021-07-01")
    exporter = HackMDExporter(hackmd_config)
    assert exporter._get_title(text) == "CO & Staff meeting 2021-07"


def test_get_next_month():
    exporter = HackMDExporter(hackmd_config)
    assert exporter._get_next_month(ALL_NOTES) == "2023-08"


def test_remove_title_tags():
    exporter = HackMDExporter(hackmd_config)
    text = NOTES_TEMPLATE.format(month="2021-07", date="2021-07-01")
    assert exporter._remove_title_and_tags(text) == NOTES_TEMPLATE_NO_TITLE.format(
        month="2021-07", date="2021-07-01"
    )


def test_get_new_index():
    exporter = HackMDExporter(hackmd_config)

    new_index = """# Zeusops CO & Staff meeting notes

###### tags: `zeusops` `meeting`

- [2023-08](https://hackmd.io/@zeusops/example)
- [2023-07](https://hackmd.io/@zeusops/rysL2QNo2)
- [2023-06](https://hackmd.io/@zeusops/SyNYKB1Yh)
- [2023-05](https://hackmd.io/@zeusops/B1D55OMLh)
"""

    assert (
        exporter._get_new_index(
            ALL_NOTES, "2023-08", "https://hackmd.io/@zeusops/example"
        )
        == new_index
    )


# def test_export():
#     exporter = HackMDExporter(config["cogs"]["meetingnotes"]["hackmd"])
#     exporter.export(NOTES_TEMPLATE)
