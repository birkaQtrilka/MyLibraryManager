
import argparse

# ---------- Custom formatter to show nested subcommands ----------
class RecursiveHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Shows subcommands of subcommands in the main help output."""
    def _format_action(self, action):
        # For a subparsers action, we walk through its subparsers and
        # recursively show their subcommands as well.
        if isinstance(action, argparse._SubParsersAction):
            parts = []
            # Header line (e.g., "positional arguments:")
            parts.append(self._format_action_invocation(action))
            parts.append('')
            # Get the dict of subparsers: name -> ArgumentParser
            subparsers = action._name_parser_map
            for name, subparser in sorted(subparsers.items()):
                # Show subcommand name and its short help
                help_line = f"  {name:<15} {subparser.description or ''}"
                parts.append(help_line)
                # If this subparser itself has subparsers, repeat the process
                sub_actions = [a for a in subparser._actions if isinstance(a, argparse._SubParsersAction)]
                if sub_actions:
                    for sub_action in sub_actions:
                        sub_subparsers = sub_action._name_parser_map
                        for sub_name, sub_subparser in sorted(sub_subparsers.items()):
                            sub_help = f"    {sub_name:<13} {sub_subparser.description or ''}"
                            parts.append(sub_help)
                parts.append('')
            return '\n'.join(parts)
        return super()._format_action(action)