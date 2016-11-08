#!/usr/bin/python3
# vim: foldmethod=marker colorcolumn=80
# Comments. {{{1
# Anything that's been changed without testing will have U_NTESTED* in the
# docstring. Anything with a comment saying "unit-tested" means that it's
# tested in tests.py and there shouldn't be any unseen bugs lurking around.
#
# * Example slightly obscured so that ctrl-f (or your text editor's equivalent)
#   won't get confused and find a false positive.
#
# TODO: Nodupes command, praw.objects.Submission has .__eq__() so == should
#       work. Seems to work after a bit of testing. Also, wasn't there a
#       command in URLToys that filtered out BOTH of the dupes? Might come in
#       handy too.
# TODO: Progress indicator when loading items. Is this even possible? If not,
#       just have one thread making a pretty loading animation while the other
#       thread is waiting on the server.
# TODO: sfw and nsfw should filter out comments based on the thread type. Same
#       for title and ntitle.
# TODO: Use OAuth because now the login command is broken. :(
# TODO: unittests for the thread command.
# TODO: unittests for the rm command.
# TODO: Test PRAWToys.input and migrate code over to using it. If any code even
#       needs input().
# TODO: Same but for PRAWToys.print. This one should be easy.
# TODO: All docstrings should be in this format:
#       '''f(oo) <bar> [baz]
#
#       Foos a bar and then bazzes stuff. 'qux' is
#       an alias for this command.
#       '''
#
#       It's much prettier and more consistant.

# Imports. {{{1
import cmd
import os
import re
import sys
import itertools
import traceback
import webbrowser
from pprint import pprint
import collections
import pickle

import praw
import OAuth2Util

import ahto_lib

# Constants and functions and stuff. {{{1
# When displaying comments/submissions, how many characters should we show?
# I.E., how many characters wide should we assume the user's terminal window is?
ASSUMED_CONSOLE_WIDTH = 80

def check_praw_version(min_version): # {{{2
    ''' Checks if the current praw version is at least min_version.

    >>> import praw
    >>> praw.__version__ = '3.5.0'
    >>> check_praw_version('3.0.0')
    True
    >>> check_praw_version('4.0.0')
    False
    '''
    global praw

    min_version  = [int(i) for i in min_version.split('.')]
    praw_version = [int(i) for i in praw.__version__.split('.')]

    if len(min_version) != 3:
        raise ValueError('min_version must be in the form:'
            ' version.subversion.bugfix')
    elif len(praw_version) != 3:
        raise RuntimeError('Unable to parse praw.__version__: '
            + repr(praw.__version__))

    for min, praw_ in zip(min_version, praw_version):
        if praw_ < min:
            return False

    return True

def is_comment(submission): # {{{2
    return isinstance(submission, praw.objects.Comment)

def is_submission(submission): # {{{2
    return isinstance(submission, praw.objects.Submission)

def comment_str(comment:praw.objects.Comment, # {{{2
        characters_needed=0) -> str:
    '''
    Convert a comment into to a string that perfectly fits on a terminal that's
    ASSUMED_CONSOLE_WIDTH characters wide.

    +-----------------------------------------------+
    | >>> ASSUMED_CONSOLE_WIDTH = 45                |
    | >>> print(comment_str(foo))                   |
    | 123: This is an ex... :: /r/example_subreddit |
    +-----------------------------------------------+

    characters_needed is for code that wants to print comment_str with other
    stuff on the same line. For example:

    +-----------------------------------------------+
    | >>> ASSUMED_CONSOLE_WIDTH = 45                |
    | >>> print("123: " + comment_str(foo))         |
    | 123: What did you just fucking... :: /r/circl |
    | ejerk                                         |
    +-----------------------------------------------+

    Notice how the "123: " makes the string 5 characters too long? Now watch
    this:

    +-----------------------------------------------+
    | >>> ASSUMED_CONSOLE_WIDTH = 45                |
    | >>> print("123: " + comment_str(foo, 5))      |
    | 123: What did you just fu... :: /r/circlejerk |
    +-----------------------------------------------+

    It's perfectly lined up with the terminal size.
    '''
    # TODO: Instead of taking characters_needed, take a header string and a
    #       footer string and combine them together inside this function.
    #       I'm procrastinating on this because I'd need to rewrite a lot of
    #       code in a lot of different places, and I'm still not 100% sure that
    #       It's a good approach yet.
    max_width = ASSUMED_CONSOLE_WIDTH - characters_needed

    subreddit_indicator = ' :: /r/' + comment.subreddit.display_name

    # How much width do we have left to fill up with the text of the comment?
    # Most comments are pretty long, so we should use as much space as we can
    # spare.
    max_comment_width = max_width - len(subreddit_indicator)

    # We shorten str(comment) to be only max_width characters long here, to
    # potentially save on processing power in the later code, where we
    # str.replace a bunch of special characters. Imagine if this comment were
    # 10,000 characters long or something. That's a lot of replacement that
    # wouldn't accomplish anything.
    comment_text = str(comment)[:max_width]

    # Actually printing these characters would result in very messy output, so
    # replace them with something a little more readable.
    comment_text.replace('\n', '\\n')
    comment_text.replace('\t', '\\t')
    comment_text.replace('\r', '\\r')

    comment_text = ahto_lib.shorten_string(str(comment), max_comment_width)
    return comment_text + subreddit_indicator

def submission_str(submission:praw.objects.Submission, # {{{2
        characters_needed=0) -> str:
    '''
    convert a submission to a string

    See comment_str for more information about this code.
    '''
    max_width = ASSUMED_CONSOLE_WIDTH - characters_needed

    subreddit_indicator = ' :: /r/' + submission.subreddit.display_name
    max_title_width = max_width - len(subreddit_indicator)

    # As far as I know, reddit submissions can't have tabs, newlines, or
    # carriage returns in their text. So it shouldn't be necessary to escape
    # those like we did in comment_str.
    title = ahto_lib.shorten_string(submission.title, max_title_width)

    return title + subreddit_indicator

def praw_object_to_string(praw_object, characters_needed=0): # {{{2
    ''' only works on submissions and comments

    BE CAREFUL! Sometimes returns a Unicode string. Use str.encode.
    This might not actually matter now that we're using Python 3.

    See comment_str for an explanation of how characters_needed works.
    '''
    if is_submission(praw_object):
        return submission_str(praw_object, characters_needed)
    elif is_comment(praw_object):
        return comment_str(praw_object, characters_needed)

def praw_object_url(praw_object): # {{{2
    ''' returns a unicode url for the given submission or comment '''
    if is_submission(praw_object):
        return praw_object.short_link
    elif is_comment(praw_object):
        return praw_object.permalink + '?context=824545201'
    else:
        raise ValueError(
            "praw_object_url only handles submissions and comments")

class PRAWToys(cmd.Cmd): # {{{1
    prompt = '0> '
    VERSION = "PRAWToys 2.0.0"

    def __init__(self, *args, **kwargs): # {{{2
        """ See cmd.Cmd.__init__ for valid arguments """
        # This is arguably more readable than having an if/else, but I'll
        # understand if you don't like the way it looks.
        can_use_readline = (isinstance(sys.stdout.write, collections.Callable)
            and isinstance(sys.stdin.readline, collections.Callable))

        # Don't use raw input if we can use readline, the better alternative.
        self.use_rawinput = not can_use_readline

        self.items = []
        self.reddit_session = praw.Reddit(self.VERSION)

        super(PRAWToys, self).__init__(self, *args, **kwargs)

    def print(self, *args, **kwargs): # {{{2
        """ A version of print that always uses self.stdout """
        kwargs['file'] = self.stdout
        return print(*args, **kwargs)

    def input(self, prompt=""): # {{{2
        """ A version of input that always uses self.stdin UNTESTED """
        self.print(prompt, end="")
        self.stdin.readline()

    # General settings. {{{2
    def emptyline(self): # {{{3
        # Disable empty line repeating the last command. Who thought that was a
        # good default?
        pass

    def postcmd(self, r, l): # {{{3
        ''' Runs after every command.

        Just updates the prompt to show the current number of items in
        self.items.
        '''
        # If you really wanted to, you could optimize this so that postcmd
        # doesn't do anything, and any command that could possibly change
        # self.items will automatically run self.update_prompt() after it's done
        # running. You'd probably want to make an @updates_items decorator for
        # that, too. And don't forget to copy over the docstring.

        # But personally, I think there are too many opportunities for
        # programmer oversight with that system. So I'm going with the slower
        # but safer (and more maintainable!) approach.
        self.update_prompt()

    def do_EOF(self, arg): # {{{3
        # If the user types an EOF character, exit PRAWToys.
        exit(0)
    do_exit = do_EOF

    # Undo and reset. {{{2
    def do_undo(self, arg): # {{{3
        '''undo

        Resets the item list one change back in time.
        '''
        if hasattr(self, 'old_items'):
            self.items = self.old_items[:]
        else:
            print('No undo history found. Nothing to undo.')
    do_u = do_undo

    def do_reset(self, arg): # {{{3
        '''reset

        Clear all items from the item list.
        '''
        self.items = []

    # Debug commands. {{{2
    def do_x(self, arg): # {{{3
        ''' x <command>

        Execute <command> as python code and pretty-print the result (if any).
        '''
        try:
            pprint(eval(arg))
        except SyntaxError:
            # If 'arg' doesn't return a value, eval(arg) will raise a
            # SyntaxError. So instead, just exec() it and don't print the
            # (nonexistant) result.
            exec(arg)
        except:
            traceback.print_exception(*sys.exc_info())

    def do_help(self, arg): # {{{2
        'List available commands with "help" or detailed help with "help cmd".'
        # HACK: This is pretty much the cmd.Cmd.do_help method copied verbatim,
        # with a few changes here-and-there. I wanted to be able to sort
        # commands into categories, because there are so many different commands
        # and command aliases that PRAWToys has to offer it can be kind of
        # intimidating to look at the list of commands without them.

        # TODO: This method's code is really ugly. I'm sorry in advance.

        # If they want help on a specific command, just pass them off to
        # the original method. No reason to reinvent the wheel in this
        # particular case.
        if arg: return cmd.Cmd.do_help(self, arg)

        prawtoys_instance = self # For use inside the classes below.
        class CommandCategory(object):
            def __init__(self, header, command_names):
                ''' command_names example: ['ls', 'foo', 'bar'] '''
                self.header = header
                self.command_names = command_names

                for i in command_names:
                    if not hasattr(prawtoys_instance, 'do_' + i):
                        raise ValueError('CommandCategory called with '
                            'nonexistent command: ' + i)

        class CommandCategories(object):
            def __init__(self, *args):
                '''You can call this as:

                    CommandCategories([
                        CommandCategory(header, [command_name, ...]),
                        ...])

                    But you can also call it as:

                    CommandCategories([
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
                            CommandCategory(header, command_names))
                else:
                    raise ValueError("CommandCategories was called with an"
                        " invalid number of arguments:" + str(len(args)))

            def get_all_command_names(self):
                command_names = []

                for category in self.command_categories:
                    command_names += category.command_names

                return command_names

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

        names = self.get_names()
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

        self.stdout.write("%s\n" % str(self.doc_leader))

        for i in command_categories.command_categories:
            self.print_topics(i.header, i.command_names, 15,80)

        self.print_topics('Uncategorized commands.', misc_commands, 15,80)
        self.print_topics(self.misc_header, list(help.keys()), 15,80)
        self.print_topics(self.undoc_header, undocumented_commands, 15,80)

    def update_prompt(self): # {{{3
        """ Change the prompt to show how many matches there are. """
        items_len = str(len(self.items))
        self.prompt = items_len + '> '

    def add_items(self, l): # {{{3
        self.old_items = self.items[:]
        self.items += list(l)

    def filter_items(self, f, invert=False): # {{{3
        if invert:
            new_items = itertools.filterfalse(f, self.items)
        else:
            new_items = filter(f, self.items)

        self.old_items = self.items
        self.items = list(new_items)

    def get_items_from_subs(self, *subs): # {{{3
        '''given a list of subs, return all stored items from those subs'''
        subs = [i.lower() for i in subs]
        filter_func = lambda i: i.subreddit.display_name.lower() in subs
        return list(filter(filter_func, self.items))

    def arg_to_matching_subs(self, subs_string=None): # {{{3
        '''
        given a string like 'aww askreddit creepy', returns all items from those
        subreddits. If no subs_string is given, or the subs_string is
        empty/all whitespace, just return self.items.
        '''
        if subs_string:
            subs = subs_string.split()

            if len(subs_string) > 0:
                return self.get_items_from_subs(*subs)

        return self.items

    def print_item(self, index, item=None, index_rjust=None): # {{{3
        ''' index_rjust is how far to rjust the index number. If it's None,
        we'll just rjust it based on the highest index in self.items

        If that doesn't make any sense, just keep it as None and you should be
        fine.
        '''

        if item == None:
            item = self.items[index]

        if index_rjust == None:
            index_rjust = len(str(len(self.items)))

        index_str = str(index).rjust(index_rjust)

        # TODO: This code might crash on some systems because it might print
        #       unicode characters to the console. Try using str.encode and/or
        #       str.decode.
        item_str = praw_object_to_string(item, index_rjust+2)
        print('{index_str}: {item_str}'.format(**locals()))

    def logged_in_command(f): # {{{3
        """ A decorator for commands that need the user to be logged in.

        Checks if the user is logged in. If so, runs the function. If not,
        prints an error and returns.

        Since decorators are run on methods before there's any 'self' to speak
        of, this decorator doesn't take 'self' as an argument. If it did, it
        wouldn't work.
        """

        def new_f(self, *args, **kwargs):
            if (not hasattr(self.reddit_session, 'user')
                    or not self.reddit_session.user):
                print('You need to be logged in first. Try typing "help login".')
                return

            f(self, *args, **kwargs)

        # This was a bitch to debug. The help command reads help from each do_*
        # command's docstrings.
        new_f.__doc__ = f.__doc__

        return new_f

    def do_login(self, arg): # {{{2
        """login

        Logs in to your reddit account. If this is your first time running
        login, it'll open a web browser and reddit will ask for permission to
        log you in.

        Requires praw 3.2 and above. If your praw is outdated, try updating it
        with:
        python -m pip install --upgrade praw
        """

        if not check_praw_version('3.2.0'):
            print("This feature only works on praw 3.2 and above.")
            return

        # "Starting with version 3.2 praw will refresh the token automatically
        # if it encounters an InvalidTokenException. If you want to use this
        # new feature, you should call o.refresh(force=True) once at the start
        # to make sure praw has a valid refresh token."
        # Source: https://github.com/SmBe19/praw-OAuth2Util/blob/master/OAuth2Util/README.md
        OAuth2Util.OAuth2Util(self.reddit_session).refresh(force=True)

        print("If everything worked, this should be your link karma: ", end='')
        print(self.reddit_session.user.link_karma)

    def do_width(self, arg): # {{{2
        """width [width]

        Set or view target console width. How many characters wide is your
        console? Let PRAWToys know and it'll do a better job of printing things
        for you.
        """
        global ASSUMED_CONSOLE_WIDTH
        args = arg.split()

        if len(args) > 0:
            ASSUMED_CONSOLE_WIDTH = int(args[0])
        else:
            print("width =", ASSUMED_CONSOLE_WIDTH)

    # Commands to add items. {{{2
    @logged_in_command # do_saved {{{3
    def do_saved(self, arg):
        '''saved

        Get your saved items. Must be logged in.
        '''
        self.add_items(
            self.reddit_session.user.get_saved(limit=None))

    def do_user(self, arg): # {{{3
        '''user <username> [limit=None]

        Get up to [limit] of a user's comments and submissions. If 'limit' is
        left blank, get ALL of them. Which, by the way, could take awhile.
        '''
        # If you change this docstring, also change the ones for
        # do_user_comments and do_user_submissions.
        # Unit-tested.
        args = arg.split()
        user = self.reddit_session.get_redditor(arg.split()[0])

        try:
            limit = int(args[1])
        except IndexError:
            limit = None

        self.add_items(list(user.get_overview(limit=limit)))

    def do_user_comments(self, arg): # {{{3
        '''user_comments <username> [limit=None]

        Get up to [limit] of a user's comments. If 'limit' is left blank, get ALL
        of them. Which, by the way, could take awhile.
        '''
        # If you change this docstring, also change the ones for do_user and
        # do_user_submissions.
        # Unit-tested.
        args = arg.split()
        user = self.reddit_session.get_redditor(arg.split()[0])

        try:
            limit = int(args[1])
        except IndexError:
            limit = None

        self.add_items(list( user.get_comments(limit=limit) ))

    def do_user_submissions(self, arg): # {{{3
        '''user_submissions <username> [limit=None]

        Get up to [limit] of a user's submissions. If 'limit' is left blank,
        get ALL of them. Which, by the way, could take awhile.
        '''
        # If you change this docstring, also change the ones for do_user and
        # do_user_comments.
        # Unit-tested.
        args = arg.split()
        user = self.reddit_session.get_redditor(arg.split()[0])

        try:
            limit = int(args[1])
        except IndexError:
            limit = None

        self.add_items(list( user.get_submitted(limit=limit) ))

    @logged_in_command # do_mine {{{3
    def do_mine(self, arg):
        '''mine

        Get your own submissions and comments. Same as "user <your username>".
        '''
        # TODO: Add limit and copy over do_user_submissions docstring.
        self.do_user(self.reddit_session.user.name)

    @logged_in_command # do_my_submissions {{{3
    def do_my_submissions(self, arg):
        '''my_submissions: get your submissions'''
        # TODO: Add limit and copy over do_user_submissions docstring.
        if not hasattr(self.reddit_session, 'user'):
            print('You need to be logged in first.')
            return

        self.do_user_submissions(self.reddit_session.user.name)

    @logged_in_command # do_my_comments {{{3
    def do_my_comments(self, arg):
        '''my_coments: get your comments'''
        # TODO: Add limit and copy over do_user_submissions docstring.
        if not hasattr(self.reddit_session, 'user'):
            print('You need to be logged in first.')
            return

        self.do_user_comments(self.reddit_session.user.name)

    def do_thread(self, arg): # {{{3
        '''thread <submission id> [n=10,000]: get <n> comments from thread. BUGGY'''
        #raise NotImplementedError

        args = arg.split()
        sub_id = args[0]
        print('Retrieving thread id: {sub_id}'.format(**locals()))

        try:
            n = int(args[1])
        except IndexError as ValueError:
            n = 10000

        sub = praw.objects.Submission.from_id(
                self.reddit_session, sub_id)

        print('Retrieving comments...')
        #while True:
        #    coms = praw.helpers.flatten_tree(sub.comments)
        #    ncoms = 0

        #    for i in coms:
        #        if type(i) != praw.objects.MoreComments:
        #            ncoms += 1

        #    print '\r{ncoms}/{n}'.format(**locals()),

        #    if ncoms >= n: break
        #    sub.replace_more_comments(limit=1)

        #print

        #self.add_items(list(coms))
        self.add_items(
            i for i in praw.helpers.flatten_tree(sub.comments)
            if type(i) != praw.objects.MoreComments
        )

    def do_get_from(self, arg): # {{{3
        ''' get_from <subreddit> [n=1000] [sort=hot]

        Get [n] submissions from /r/<subreddit>, sorting by [sort]. [sort] can
        be 'hot', 'new', 'top', 'controversial', and maybe 'rising' (which is
        untested).

        You can set [n] to 'none' or 'all' (case insensitive) and you'll get
        EVERYTHING from the chosen subreddit. This is obviously going to take
        awhile, depending on the subreddit. 
        '''
        # Unit-tested.

        args      = arg.split()
        subreddit = args[0]

        if len(args) > 1:
            if args[1].lower() in ['none', 'all']:
                limit = None
            else:
                limit = int(args[1])
        else:
            limit = 1000

        if len(args) > 2:
            sort = args[2]
        else:
            sort = 'hot'

        sub = self.reddit_session.get_subreddit(subreddit)

        self.add_items(sub.search('', limit=limit, sort=sort))

    def do_load_from_file(self, arg): # {{{3
        '''load_from_file <filename>

        Load the items stored in <filename>.pickle. This is generally to get
        items stored with the save_to_file command.

        Be careful when openning pickle files from sources you don't trust! It's
        very easy for a hacker to write malicious pickle files.

        UNTESTED
        '''
        try:
            filename = arg.split()[0] + '.pickle'
        except IndexError:
            print('No file specified!')
            return

        with open(filename, 'rb') as file_:
            self.items += pickle.load(file_)

    # Commands for filtering. {{{2
    def do_submission(self, arg): # {{{3
        '''submission

        Filter out all but links and self posts.'''
        # Unit-tested.
        self.filter_items(is_submission)

    def do_comment(self, arg): # {{{3
        '''comment

        Filter out all but comments.'''
        # Unit-tested.
        self.filter_items(is_comment)

    def sub_nsub(self, invert, arg): # {{{3
        ''' do_sub calls this with invert=False, and vice versa for do_nsub.

        This function is basically to help with the whole "don't repeat
        yourself" thing, since sub and nsub do pretty much the same thing,
        except exactly the opposite.
        '''
        target_subs = [i.lower() for i in arg.split()]

        self.filter_items(invert=invert, f=lambda item:
            item.subreddit.display_name.lower() in target_subs)

    def do_sub(self, arg): # {{{3
        '''
        sub <subreddit>...: filter out anything not in the listed subreddits.
        Don't include /r/
        '''
        # Unit-tested.
        self.sub_nsub(invert=False, arg=arg)

    def do_nsub(self, arg): # {{{3
        '''
        nsub <subreddit>: filter out anything in the listed subreddits. Don't
        include /r/
        '''
        # Unit-tested.
        self.sub_nsub(invert=True, arg=arg)

    def sfw_nsfw(self, filter_sfw, arg): # {{{3
        ''' See the docstring for sub_nsub. filter_sfw == True means filter out sfw.
        Otherwise, filters out nsfw.
        '''

        def filter_func(item):
            if is_comment(item):
                return True

            sfw = not item.over_18
            return filter_sfw != sfw

        self.filter_items(filter_func)

    def do_sfw(self, arg): # {{{3
        '''sfw: filter out anything nsfw. Keeps comments.'''
        self.sfw_nsfw(filter_sfw=False, arg=arg)

    def do_nsfw(self, arg): # {{{3
        '''nsfw: filter out anything sfw. Keeps comments.'''
        self.sfw_nsfw(filter_sfw=True, arg=arg)

    def self_nself(self, invert, arg): # {{{3
        ''' See the docstring for sub_nsub. invert==True will filter out all
        self-posts.
        '''
        self.filter_items(lambda item:
            is_comment(item) or (invert != item.is_self))

    def do_self(self, arg): # {{{3
        '''self: filter out all but self-posts (and comments)'''
        self.self_nself(invert=False, arg=arg)

    def do_nself(self, arg): # {{{3
        '''nself: filter out all self-posts'''
        self.self_nself(invert=True, arg=arg)

    def title_ntitle(self, invert, arg): # {{{3
        ''' See the docstring for sub_nsub. invert==True means filter out
        matches, not non-matches.
        '''

        def filter_func(item):
            if is_comment(item):
                return True

            search_success = bool(re.search(arg, item.title))

            return invert != search_success

        self.filter_items(filter_func)

    def do_title(self, arg): # {{{3
        '''
        title <regex>: filter out anything whose title doesn't match <regex>

        You can have spaces in your command, like "title asdf fdsa", but don't
        put any quotation marks if you don't want them taken as literal
        characters!

        Also implicitely filters out comments.
        '''

        self.title_ntitle(invert=False, arg=arg)

    def do_ntitle(self, arg): # {{{3
        '''
        ntitle <regex>: filter out anything whose title matches <regex>

        You can have spaces in your command, like "ntitle asdf fdsa", but don't
        put any quotation marks if you don't want them taken as literal
        characters!

        Also implicitely filters out comments.
        '''
        self.title_ntitle(invert=True, arg=arg)

    def do_rm(self, arg): # {{{3
        '''rm <index>...: remove items by index'''
        indicies = list(map(int, arg.split()))

        items_len = len(self.items)
        for i in indicies:
            if i < 0 or i > items_len-1:
                print("Out of range:", i)
                return

        self.old_items = self.items[:]

        for i in indicies:
            self.items[i] = None

        self.items = [i for i in self.items if i != None]

    # Commands for viewing list items. {{{2
    def do_ls(self, arg): # {{{3
        '''
        ls [start [n=10]]: list items, with [start] list [n] items starting at
        [start]
        '''
        if len(self.items) == 0:
            return

        args = arg.split()

        to_print = list( enumerate(self.items) )

        if len(args) > 0:
            start = int(args[0])
            to_print = to_print[start:]

            if len(args) > 1:
                n = int(args[1])
                to_print = to_print[:n]

        index_rjust = len(str(
            max(index for index, item in to_print)))
        for index, item in to_print:
            self.print_item(index, item, index_rjust)

    def do_head(self, arg): # {{{3
        '''head [n=10]: show first [n] items'''
        args = arg.split()
        if len(args) > 0:
            n = int(args[0])
        else:
            n = 10

        self.do_ls('0 ' + str(n))

        #to_print = list(enumerate(self.items))[:n]
        #for i, v in enumerate(self.items[:n]):
        #    self.print_item(i, v)

    def do_tail(self, arg): # {{{3
        '''tail [n=10]: show last [n] items'''
        args = arg.split()
        if len(args) > 0:
            n = int(args[0])
        else:
            n = 10

        start = len(self.items) - n
        self.do_ls( str(start) + ' ' + str(n) )

    def do_view_subs(self, arg): # {{{3
        '''view_subs: shows how many of the list items are from which sub'''
        frequency_by_sub = {}

        for i in self.items:
            sub_name = i.subreddit.display_name.lower()

            try:
                frequency_by_sub[sub_name] += 1
            except KeyError:
                frequency_by_sub[sub_name] = 1

        # Convert to [(k, v)] and then sort (ascending) by v.
        frequency_by_sub = list(frequency_by_sub.items())
        frequency_by_sub.sort(key=lambda item: item[1])

        # This tells us how much we should rjust the numbers in our printout.
        max_number_length = len(str(len(self.items)))

        for sub, number in frequency_by_sub:
            print('{number} : /r/{sub}'.format(sub=sub,
                    number=str(number).rjust(max_number_length)))
    do_vs = do_view_subs # {{{3

    def do_lsub(self, arg): # {{{3
        '''lsub <sub>...: show all items from the given sub(s)'''
        subs = arg.split()
        items_with_indicies = enumerate(self.items)
        items_with_indicies = [(i, v) for i, v in items_with_indicies if
            v.subreddit.display_name.lower() in subs]

        rjust = len(str(max(i for i, v in items_with_indicies)))
        for i, v in items_with_indicies:
            self.print_item(i, v, rjust)

    def do_get_links(self, arg): # {{{3
        '''
            get_links [sub]...: generates an HTML file with all the links to
            everything (or everything in a given subreddit(s)) and opens it in
            your default browser.
        '''
        target_items = self.arg_to_matching_subs(arg)

        with open('urls.html', 'w') as html_file:
            html_file.write('<html><body>')

            for item in target_items:
                item_string = praw_object_to_string(item).encode(
                    encoding='ascii', errors='xmlcharrefreplace')

                item_url = praw_object_url(item).encode(
                    'ascii', 'xmlcharrefreplace')

                html_file.write(
                    '<a href="{item_url}">{item_string}</a><br>'.format(
                        **locals()))

            html_file.write('</body></html>')

        webbrowser.open('file://' + os.getcwd() + '/urls.html')
    do_gl = do_get_links # {{{3


    # Commands for doing stuff with the items. {{{2
    def open(self, index_or_item): # {{{3
        if type(index_or_item) == int:
            item = self.items[index_or_item]
        else:
            item = index_or_item

        webbrowser.open( praw_object_url(item) )

    def open_all(self, indicies_andor_items): # {{{3
        len_ = len(indicies_andor_items)
        if len_ >= 5:
            yes_no_prompt = ("You're about to open {} different tabs. Are you"
                " sure you want to continue?").format(len_)

            if not ahto_lib.yes_no(False, yes_no_prompt):
                return
        elif len_ <= 0:
            return

        ahto_lib.progress_map(self.open, indicies_andor_items)

    def do_open(self, arg): # {{{3
        '''
        open [sub]...: open all items using the webbrowser module. optionally
        filter by sub(s)
        '''
        self.open_all(self.arg_to_matching_subs(arg))

    def do_open_index(self, arg): # {{{3
        '''open_index <index>...

        Open the item(s) at the given index/indicies.
        '''
        args = map(int, arg.split())
        target_items = [self.items[i] for i in args]

        self.open_all(target_items)

    do_oi = do_open_index # {{{3

    def do_save_to_file(self, arg): # {{{3
        '''save_to_file <filename>

        Save the current items to <filename>.pickle, so that you can load them
        later with load_from_file.

        UNTESTED
        '''
        try:
            filename = arg.split()[0] + '.pickle'
        except ValueError:
            print('No file specified!')
            return

        with open(filename, 'wb') as file_:
            pickle.dump(self.items, file_)

    @logged_in_command # do_upvote {{{3
    def do_upvote(self, arg):
        '''upvote

        Upvote EVERYTHING in the current list.

        Note: Untested for comments.
        '''

        print("You're about to upvote EVERYTHING in the current list.")
        continue_ = ahto_lib.yes_no(False, "Do you really want to continue?")

        if continue_:
            ahto_lib.progress_map( (lambda i: i.upvote()), self.items )
        else:
            print("Cancelled. Phew.")

    @logged_in_command # do_clear_vote {{{3
    def do_clear_vote(self, arg):
        '''clear_vote

        Clear your vote on EVERYTHING in the current list.

        UNTESTED
        '''
        continue_ = ahto_lib.yes_no(False, "You're about to clear your votes on"
            " EVERYTHING in the current list. Do you really want to"
            " continue?")

        if continue_:
            ahto_lib.progress_map( (lambda i: i.clear_vote()), self.items )
        else:
            print("Cancelled. Phew.")

if __name__ == '__main__': # {{{1
    import traceback

    prawtoys = PRAWToys()

    if sys.argv[1].lower() == 'debug':
        prawtoys.cmdloop()
    else:
        while True:
            try:
                prawtoys.cmdloop()
            except Exception as err:
                traceback.print_exc()
            else:
                break
