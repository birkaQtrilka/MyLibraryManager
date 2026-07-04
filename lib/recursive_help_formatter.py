
import argparse

class RecursiveHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Shows subcommands of subcommands in the main help output."""
    def _format_action(self, action):
        # For a subparsers action, we walk through its subparsers and
        # recursively show their subcommands as well.
        if isinstance(action, argparse._SubParsersAction):
            parts = [self._format_action_invocation(action), ""]
        
            # Map parser name -> help text
            helps = {a.dest: a.help for a in action._choices_actions}
        
            for name, subparser in sorted(action._name_parser_map.items()):
                parts.append(f"  {name:<15} {helps.get(name, '')}")
        
                # Nested subcommands
                for sub_action in subparser._actions:
                    if isinstance(sub_action, argparse._SubParsersAction):
                        sub_helps = {a.dest: a.help for a in sub_action._choices_actions}
                        for sub_name, _ in sorted(sub_action._name_parser_map.items()):
                            parts.append(f"    {sub_name:<13} {sub_helps.get(sub_name, '')}")
        
                parts.append("")
        
            return "\n".join(parts)
        return super()._format_action(action)