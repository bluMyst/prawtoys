#!/usr/bin/python
# vim: foldmethod=marker
# Comments. {{{1
# Anything that's been changed without testing will have U_NTESTED* in the
# docstring. Anything with a comment saying "unit-tested" means that it's
# tested in tests.py and there shouldn't be any unseen bugs lurking around.
#
# * Example slightly obscured so that ctrl-f (or your text editor's equivalent)
#   won't get confused and find a false positive.
#
# TODO: Nodupes command, praw.objects.Submission has .__eq__() so == should
#       work. Seems to work after a bit of testing. Also, wasn't there a command
#       that filtered out BOTH of the dupes? Might come in handy too.
# TODO: All commands that need user to be logged in should fail gracefully.
# TODO: Progress indicator when loading items. Is this even possible? If not,
#       just have one thread making a pretty loading animation while the other
#       thread is waiting on the server.
# TODO: sfw and nsfw should filter out comments based on the thread type. Same
#       for title and ntitle.
# TODO: Use OAuth or everything will be slowed down on purpose.
# TODO: unittests for the thread command.

# Imports. {{{1
import praw
import cmd
import os
import re
import sys
import itertools
import traceback
import webbrowser
from pprint import pprint
import ahto_lib

# Constants and functions and stuff. {{{1
# When displaying comments/submissions, how many characters should we show?
ASSUMED_CONSOLE_WIDTH = 80

def is_comment(submission): # {{{2
    return isinstance(submission, praw.objects.Comment)

def is_submission(submission): # {{{2
    return isinstance(submission, praw.objects.Submission)

def comment_str(comment): # {{{2
    '''convert a comment to a string'''
    comment_string = ' :: /r/' + comment.subreddit.display_name

    comment_text = ahto_lib.shorten_string(unicode(comment),
        ASSUMED_CONSOLE_WIDTH - len(comment_string))

    comment_text.replace('\n', '\\n')

    comment_string = comment_text + comment_string
    return comment_string

def submission_str(submission): # {{{2
    '''convert a submission to a string'''
    subreddit_string = ' :: /r/' + submission.subreddit.display_name
    title  = ahto_lib.shorten_string(submission.title,
        ASSUMED_CONSOLE_WIDTH - len(subreddit_string))
    return title + subreddit_string

def praw_object_to_string(praw_object): # {{{2
    ''' only works on submissions and comments

    BE CAREFUL! Sometimes returns a Unicode string. Use str.encode.
    '''
    if is_submission(praw_object):
        return submission_str(praw_object)
    elif is_comment(praw_object):
        return comment_str(praw_object)

def praw_object_url(praw_object): # {{{2
    ''' returns a unicode url for the given submission or comment '''
    if is_submission(praw_object):
        return praw_object.short_link
    elif is_comment(praw_object):
        return praw_object.permalink + '?context=824545201'
    else:
        raise ValueError(
            "praw_object_url only handles submissions and comments")

def print_all(submissions, file_=sys.stdout): # {{{2
    '''print all submissions DEPRECATED'''
    for i in submissions:
        try:
            object_str = praw_object_to_string(i).encode(
                encoding='ascii', errors='backslashreplace')

            file_.write(object_str + '\n')
        except UnicodeEncodeError:
            print ('[Failed to .write() a submission/comment ({}) here:'
                'UnicodeEncodeError]').format(str(i))

class PRAWToys(cmd.Cmd): # {{{1
    prompt = '0> '
    VERSION = "PRAWToys 1.0.0"

    def __init__(self, *args, **kwargs): # {{{2
        # Don't use raw input if we can use the better alternative. (readline)
        self.use_rawinput = not (
            callable(sys.stdout.write) and callable(sys.stdin.readline))

        if self.use_rawinput:
            print "Looks like you don't have GNU readline installed. Oh, well."
            print

        self.items = []
        self.reddit_session = praw.Reddit(self.VERSION)

        # No super() with old-style classes. :(
        cmd.Cmd.__init__(self, *args, **kwargs)

    # General settings. {{{2
    def emptyline(self): pass # disable empty line repeating the last command

    def postcmd(self, r, l): # {{{3
        ''' Runs after every command.

        Just updates the prompt to show the current number of items in
        self.items.
        '''
        self.update_prompt()

    def do_EOF(self, arg): # {{{3
        exit(0)
    do_exit = do_EOF

    # Internal utility methods. {{{2
    def do_help(self, arg): # {{{3
        'List available commands with "help" or detailed help with "help cmd".'
        # HACK: This is pretty much the cmd.Cmd.do_help method copied verbatim,
        # with a few changes here-and-there.

        # If they want help on a specific command, just pass them off to
        # the original method.
        if arg:
            return cmd.Cmd.do_help(self, arg)

        names = self.get_names()
        misc_commands = []
        undocumented_commands = []
        help = {}

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
            def __init__(self, command_categories=[]):
                self.command_categories = command_categories

            def get_all_command_names(self):
                command_names = []

                for category in self.command_categories:
                    command_names += category.command_names

                return command_names

        prawtoys_instance = self # for use inside the objects below
        add_commands = CommandCategory('Commands for adding items', [
            'saved', 'user', 'user_comments', 'user_submissions', 'mine',
            'my_comments', 'my_submissions', 'thread', 'get_from'])

        filter_commands = CommandCategory('Commands for filtering items.', [
            'submission', 'comment', 'sub', 'nsub', 'sfw', 'nsfw', 'self',
            'nself', 'title', 'ntitle'])

        view_commands = CommandCategory('Commands for viewing list items.', [
            'ls', 'head', 'tail', 'view_subs', 'vs', 'get_links', 'gl'])

        interact_commands = CommandCategory(
            'Commands for interacting with items.',
            ['open', 'open_with', 'save_to', 'upvote', 'clear_vote'])

        command_categories = CommandCategories(
            [add_commands, filter_commands, view_commands, interact_commands])

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
        self.print_topics(self.misc_header, help.keys(), 15,80)
        self.print_topics(self.undoc_header, undocumented_commands, 15,80)

    def update_prompt(self): # {{{3
        """ Change the prompt to show how many matches there are. """
        self.prompt = str(len(self.items)) + '> '

    def add_items(self, l): # {{{3
        self.old_items = self.items[:]
        self.items += list(l)

    def filter_items(self, f, invert=False): # {{{3
        if invert:
            new_items = itertools.ifilterfalse(f, self.items)
        else:
            new_items = itertools.ifilter(f, self.items)

        self.old_items = self.items
        self.items = list(new_items)

    def get_items_from_subs(self, *subs): # {{{3
        '''given a list of subs, return all stored items from those subs'''
        subs = [i.lower() for i in subs]
        filter_func = lambda i: i.subreddit.display_name.lower() in subs
        return filter(filter_func, self.items)

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
        ''' index_rjust is how far to rjust the index number '''
        if item == None:
            item = self.items[index]

        if index_rjust == None:
            index_rjust = len(str(len(self.items)))

        index_str = str(index).rjust(index_rjust)

        item_str = praw_object_to_string(item).encode(
            encoding='ascii', errors='backslashreplace')

        print '{index_str}: {item_str}'.format(**locals())

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
                print 'You need to be logged in first. Try typing "help login".'
                return

            f(self, *args, **kwargs)

        return new_f

    # Undo and reset. {{{2
    def do_undo(self, arg): # {{{3
        '''undo: undoes last command'''
        if hasattr(self, 'old_items'):
            self.items = self.old_items[:]
        else:
            print 'No undo history found. Nothing to undo.'
    do_u = do_undo

    def do_reset(self, arg): # {{{3
        '''reset: clear all items'''
        self.items = []

    # Debug commands. {{{2
    def do_x(self, arg):
        '''
        x <command>: execute <command> as python code and pretty-print the
        result (if any)
        '''
        # NOTE: Redundant with cmd's py command. Might want to remove depending
        #       on how pretty the printing of do_py is.
        try:
            pprint(eval(arg))
        except SyntaxError:
            # If 'arg' doesn't return a value, eval(arg) will raise a
            # SyntaxError. So instead, just exec() it and don't print the
            # (nonexistant) result.
            exec(arg)
        except:
            traceback.print_exception(*sys.exc_info())

    def do_login(self, arg): # {{{2
        """ login [username]: log in to your reddit account """
        args = arg.split()

        if len(args) > 0:
            username = args[0]
        else:
            username = None

        self.reddit_session.login(username, disable_warning=True)
        print "If everything worked, this should be your link karma:",
        print self.reddit_session.user.link_karma

    # Commands to add items. {{{2
    @logged_in_command # do_saved {{{3
    def do_saved(self, arg):
        '''saved: get your saved items'''
        self.add_items(
            self.reddit_session.user.get_saved(limit=None))

    def do_user(self, arg): # {{{3
        '''user <username> [limit=None]: get up to [limit] of a user's submitted items'''
        # Unit-tested.
        args = arg.split()
        user = self.reddit_session.get_redditor(arg.split()[0])

        try:
            limit = int(args[1])
        except IndexError:
            limit = None

        self.add_items(list(user.get_overview(limit=limit)))

    def do_user_comments(self, arg): # {{{3
        '''user_comments <username> [limit=None]: get a user's comments'''
        # Unit-tested.
        args = arg.split()
        user = self.reddit_session.get_redditor(arg.split()[0])

        try:
            limit = int(args[1])
        except IndexError:
            limit = None

        self.add_items(list( user.get_comments(limit=limit) ))

    def do_user_submissions(self, arg): # {{{3
        '''user_submissions <username> [limit=None]: get a user's submissions'''
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
        '''mine: get your own submitted items'''
        self.do_user(self.reddit_session.user.name)

    @logged_in_command # do_my_submissions {{{3
    def do_my_submissions(self, arg):
        '''my_submissions: get your submissions'''
        if not hasattr(self.reddit_session, 'user'):
            print 'You need to be logged in first.'
            return

        self.do_user_submissions(self.reddit_session.user.name)

    @logged_in_command # do_my_comments {{{3
    def do_my_comments(self, arg):
        '''my_coments: get your comments'''
        if not hasattr(self.reddit_session, 'user'):
            print 'You need to be logged in first.'
            return

        self.do_user_comments(self.reddit_session.user.name)

    def do_thread(self, arg): # {{{3
        '''thread <submission id> [n=10,000]: get <n> comments from thread. BUGGY'''
        #raise NotImplementedError

        args = arg.split()
        sub_id = args[0]
        print 'Retrieving thread id: {sub_id}'.format(**locals())

        try:
            n = int(args[1])
        except IndexError, ValueError:
            n = 10000

        sub = praw.objects.Submission.from_id(
                self.reddit_session, sub_id)

        print 'Retrieving comments...'
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
        '''
        get_from <subreddit> [n=1000] [sort=hot]: get [n] submissions from
        /r/<subreddit>, sorting by [sort]. [sort] can be 'hot', 'new', 'top',
        'controversial', and maybe 'rising' (untested)

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


    # Commands for filtering. {{{2
    def do_submission(self, arg): # {{{3
        '''submission: filter out all but links and self posts'''
        # Unit-tested.
        self.filter_items(is_submission)

    def do_comment(self, arg): # {{{3
        '''comment: filter out all but comments'''
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
        indicies = map(int, arg.split())

        items_len = len(self.items)
        for i in indicies:
            if i < 0 or i > items_len-1:
                print "Out of range:", i
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
        frequency_by_sub = list(frequency_by_sub.iteritems())
        frequency_by_sub.sort(key=lambda (item): item[1])

        # This tells us how much we should rjust the numbers in our printout.
        max_number_length = len(str(len(self.items)))

        for sub, number in frequency_by_sub:
            print '{number} : /r/{sub}'.format(sub=sub,
                    number=str(number).rjust(max_number_length))
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
    def do_open(self, arg): # {{{3
        '''
        open [sub]...: open all items using the webbrowser module. optionally
        filter by sub(s)
        '''

        target_items = self.arg_to_matching_subs(arg)
        target_items_len = len(target_items)

        if target_items_len >= 20:
            yes_no_prompt = ("You're about to open {} different tabs. Are you"
                " sure you want to continue?").format(target_items_len)

            if not ahto_lib.yes_no(False, yes_no_prompt):
                return

        ahto_lib.progress_map(
            (lambda i: webbrowser.open( praw_object_url(i) )),
            target_items)

    def do_save_to(self, arg): # {{{3
        '''save_to <file>: save URLs to file'''
        try:
            filename = arg.split()[0]
        except ValueError:
            print 'No file specified!'
            return

        file_ = open(filename, 'w')
        print_all(self.items, file_) # TODO print_all deprecated

    @logged_in_command # do_upvote {{{3
    def do_upvote(self, arg):
        # NOTE untested for comments
        '''upvote: upvote EVERYTHING in the current list'''

        print "You're about to upvote EVERYTHING in the current list."
        continue_ = ahto_lib.yes_no(False, "Do you really want to continue?")

        if continue_:
            ahto_lib.progress_map( (lambda i: i.upvote()), self.items )
        else:
            print "Cancelled. Phew."

    @logged_in_command # do_clear_vote {{{3
    def do_clear_vote(self, arg):
        'clear_vote: clear vote on EVERYTHING in the current list - UNTESTED'
        continue_ = ahto_lib.yes_no("You're about to clear your votes on EVERYTHING"
            " in the current list. Do you really want to continue? [yN]")

        if continue_:
            ahto_lib.progress_map( (lambda i: i.clear_vote()), self.items )
        else:
            print "Cancelled. Phew."

# Init code. {{{1
if __name__ == '__main__':
    import traceback

    prawtoys = PRAWToys()
    while True:
        try:
            prawtoys.cmdloop()
            break
        except KeyboardInterrupt:
            # TODO: This doesn't work. Nothing gets printed.
            print "Ctrl-C detected. Bye!"
            break
        except Exception as err:
            traceback.print_exc()
