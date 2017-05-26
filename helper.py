"""
Used by PRAWToys.do_help, this extends the existing help system to have
categories other than 'documented' and 'undocumented'.

I wanted to be able to sort commands into categories, because there are so many
different commands and command aliases that PRAWToys has to offer it can be
kind of intimidating to look at the list of commands without them.
"""
# TODO: Generalize so any cmd.Cmd can use helper.Helper.


class CommandCategory(object):
    def __init__(self, prawtoys, header, command_names):
        ''' command_names example: ['ls', 'foo', 'bar'] '''
        self.header = header
        self.command_names = command_names

        for i in command_names:
            if not hasattr(prawtoys, 'do_' + i):
                raise ValueError(
                    'CommandCategory called with nonexistent command: ' + i)


class Helper(object):
    def __init__(self, prawtoys, *args):
        '''You can call this as:

            CommandCategories(prawtoys_instance, [
                CommandCategory(header, [command_name, ...]),
                ...])

            But you can also call it as:

            CommandCategories(prawtoys_instance, [
                header, [
                    command_name, ...]],

                ...)

            In which case it'll automatically create CommandCategory
            objects for you.
        '''
        if len(args) == 1:
            self.command_categories = args[0]
        elif len(args) % 2 == 0:
            self.command_categories = []

            for i in range(0, len(args), 2):
                header, command_names = args[i], args[i+1]

                self.command_categories.append(
                    CommandCategory(prawtoys, header, command_names))
        else:
            raise ValueError(
                "Helper was called with an invalid number of arguments:"
                + str(len(args) + 1))

    def get_all_command_names(self):
        command_names = []

        for category in self.command_categories:
            command_names += category.command_names

        return command_names

    def __call__(self, prawtoys, arg=''):
        ''' help [cmd]

        List available commands with "help" or detailed help with "help cmd".
        '''
        # This is pretty much the cmd.Cmd.do_help method copied verbatim, with
        # a few changes here-and-there.

        # If they want help on a specific command, just pass them off to
        # the original method. No reason to reinvent the wheel in this
        # particular case.
        if arg:
            return cmd.Cmd.do_help(self, arg)

        # TODO: Yeah, I know. This is very... Lisp.
        command_categories = CommandCategories(
            'Commands for adding items:', [
                'saved', 'user', 'user_comments', 'user_submissions', 'mine',
                'my_comments', 'my_submissions', 'thread', 'get_from',
                'load_from_file'],

            'Commands for filtering items:', [
                'submission', 'comment', 'sub', 'nsub', 'sfw', 'nsfw', 'self',
                'nself', 'title', 'ntitle', 'rm'],

            'Commands for viewing list items:', [
                'ls', 'head', 'tail', 'view_subs', 'vs', 'get_links', 'gl',
                'oi', 'open_index', 'lsub'],

            'Commands for interacting with items:', [
                'open', 'save_to_file', 'upvote', 'clear_vote'])

        names = prawtoys.get_names()
        misc_commands = []
        undocumented_commands = []

        help = {}
        for name in names:
            if name[:5] == 'help_':
                help[name[5:]] = 1

        names.sort()

        # There can be duplicates if routines overridden
        prevname = ''
        for name in names:
            if name[:3] == 'do_':
                if name == prevname:
                    continue

                prevname = name
                command = name[3:]

                if command in command_categories.get_all_command_names():
                    continue

                if command in help:
                    misc_commands.append(command)
                    del help[command]
                elif getattr(self, name).__doc__:
                    misc_commands.append(command)
                else:
                    undocumented_commands.append(command)

        prawtoys.print(prawtoys.doc_leader)

        for i in command_categories.command_categories:
            self.print_topics(i.header, i.command_names, 15, 80)

        self.print_topics('Uncategorized commands.', misc_commands, 15, 80)
        self.print_topics(self.misc_header, list(help.keys()), 15, 80)
        self.print_topics(self.undoc_header, undocumented_commands, 15, 80)
