import argparse


def add_repeatable_argument_group(parser, name):
    group_parser = argparse.ArgumentParser()
    
    class RepeatableGroupAction(argparse.Action):
        def __init__(self, *args, **kwargs):
            argparse.Action.__init__(
                self,
                *args,
                required=False,
                nargs=argparse.REMAINDER,
                default=[],
                **kwargs
            )
        
        def __call__(self, parser, namespace, values, option_string=None):
            if not hasattr(namespace, self.dest):
                setattr(namespace, self.dest, [])
            
            remaining_argv = values
            
            while remaining_argv:
                if name in remaining_argv:
                    group_end_index = remaining_argv.index(name)
                    group_argv = remaining_argv[:group_end_index]
                else:
                    group_end_index = len(remaining_argv)
                    group_argv = remaining_argv
                    
                result = group_parser.parse_args(group_argv)
                
                getattr(namespace, self.dest).append(result)
                
                remaining_argv = remaining_argv[group_end_index + 1:]
            
    
    parser.add_argument(name, action=RepeatableGroupAction)
    return group_parser
