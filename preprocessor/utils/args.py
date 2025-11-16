import argparse
from typing import (
    Any,
    Dict,
    List,
    Tuple,
)

Argument = Tuple[str, Dict[str, str]]
ParserModes = Dict[str, List[Argument]]
def parse_multi_mode_args(description: str, modes: ParserModes, mode_helps: Dict[str, str]) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Choose mode")

    for mode, flags in modes.items():
        subparser = subparsers.add_parser(mode, help=mode_helps[mode], formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        for flag, options in flags:
            subparser.add_argument(flag, **options)

    return vars(parser.parse_args())
