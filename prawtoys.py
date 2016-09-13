#!/usr/bin/python
# vim: foldmethod=marker
# Anything that's been changed without testing will have U_NTESTED in the
# docstring. (example obscured slightly so search doesn't find it) Anything with
# a comment saying "unit-tested" means that it's tested in tests.py and there
# shouldn't be any bugs.
#
# https://pythonhosted.org/cmd2/index.html
#
# TODO: Nodupes command, praw.objects.Submission has .__eq__() so == should
#       work. But test just to be sure.
# TODO: Only ask user for login if needed
# TODO: head ls and tail should show indicies
# TODO: Progress indicator when loading items.
# TODO: Login through cmd.
# TODO: login command inside of PRAWToys.
# TODO: sfw and nsfw should filter out comments based on the thread type. Same
#       for title and ntitle.
# TODO: A better way to invert commands than separately defining 'self' and
#       'nself.' A decorator or something.

# Imports. {{{1
import praw
#import cmd
import cmd2
import os
import re
import sys
import itertools
import traceback
import webbrowser
from pprint import pprint
#import example_oauth_webserver

# Constants and functions. {{{1
VERSION = "PRAWToys 0.7.0"
r = praw.Reddit(VERSION)

# When displaying comments, how many characters should we show?
MAX_COMMENT_TEXT = 80

def yes_no(default, question): # {{{2
    ''' default can be True, False, or None UNTESTED '''
    if default == None:
        question += ' [yn]'
    elif default:
        question += ' [Yn]'
    else:
        question += ' [yN]'

    answer = raw_input(question)

    if answer in 'yY':
        return True
    elif answer in 'nN':
        return False
    elif default != None:
        return default
    else:
        print "Invalid response: " + answer
        return yes_no(default, question)

def shorten_string(string, length): # {{{2
    ''' shortens a string and uses "..." to show it's been shortened '''
    if len(string) <= length:
        return string

    return string[:length-3] + '...'

def is_comment(submission): # {{{2
    return isinstance(submission, praw.objects.Comment)

def is_submission(submission): # {{{2
    return isinstance(submission, praw.objects.Submission)

def comment_str(comment): # {{{2
    '''convert a comment to a string'''
    return (
        shorten_string(unicode(comment), MAX_COMMENT_TEXT)
        + ' :: /r/' + comment.subreddit.display_name)

def submission_str(submission): # {{{2
    '''convert a submission to a string'''
    subreddit = submission.subreddit.display_name
    title     = shorten_string(submission.title, 40)
    string    = title + ' :: /r/' + subreddit

    if submission.is_self:
        return string
    else:
        url = shorten_string(submission.url, 20)
        return string + ' :: ' + url

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

class PRAWToys(cmd2.Cmd): # {{{1
    prompt = '0> '

    def __init__(self, reddit_session, *args, **kwargs): # {{{2
        # Don't use raw input if we can use the better alternative. (readline)
        self.use_rawinput = not (
            callable(sys.stdout.write) and callable(sys.stdin.readline))

        if self.use_rawinput:
            print "Looks like you don't have GNU readline installed. Oh, well."

        print

        self.items = []
        self.reddit_session = reddit_session

        # super() doesn't work on old-style classes like cmd.Cmd :(
        # TODO: What about cmd2.Cmd?
        cmd2.Cmd.__init__(self, *args, **kwargs)

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
    def update_prompt(self): # {{{3
        """ Change the prompt to show how many matches there are. """
        self.prompt = str(len(self.items)) + '> '

    def add_items(self, l): # {{{3
        self.old_items = self.items[:]
        self.items += list(l)

    def filter_items(self, f, invert=False): # {{{3
        if invert:
            old_f = f
            def f(*args, **kwargs):
                # If I don't do the old_f thing, the new f will call itself
                # here and make an infinite recursion loop.
                return not old_f(*args, **kwargs)

        self.old_items = self.items
        self.items = filter(f, self.items)

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
        UNTESTED
        '''
        if subs_string:
            subs = subs_string.split()

            if len(subs_string) > 0:
                return self.get_items_from_subs(*subs)

        return self.items

    def print_item(self, index, item=None): # {{{3
        if item == None:
            item = self.items[index]

        rjust_number = len(str(len(self.items)))
        index_str    = str(index).rjust(rjust_number)

        item_str = praw_object_to_string(item).encode(
            encoding='ascii', errors='backslashreplace')

        print '{index_str}: {item_str}'.format(**locals())

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
        # NOTE: Redundant with cmd2's py command. Might want to remove depending
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

    # Commands to add items. {{{2
    def do_saved(self, arg): # {{{3
        '''saved: get your saved items'''
        self.add_items(
            self.reddit_session.user.get_saved(limit=None)
        )

    def do_user(self, arg): # {{{3
        '''user <username> [limit=None]: get up to [limit] of a user's submitted items'''
        # Unit-tested.
        args = arg.split()
        user = self.reddit_session.get_redditor(arg.split()[0])

        try:
            limit = int(args[1])
        except IndexError:
            limit = None

        # TODO: Update docstring depending on if this works:
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

    def do_mine(self, arg): # {{{3
        '''mine: get your own submitted items'''
        self.do_user(self.reddit_session.user.name)

    def do_my_submissions(self, arg): # {{{3
        '''mysubs: get your submissions'''
        self.do_user_submissions(self.reddit_session.user.name)

    def do_my_comments(self, arg): # {{{3
        '''mycoms: get your comments'''
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
        get_from <subreddit> [n=1000] [sort=now]: get [n] submissions from
        /r/<subreddit>, sorting by [sort]. [sort] can be 'hot', 'new', 'top',
        'controversial', and maybe 'rising' (untested)
        '''
        # Unit-tested.

        args      = arg.split()
        subreddit = args[0]

        if len(args) > 1:
            limit = int(args[1])
        else:
            limit = 1000

        if len(args) > 2:
            sort = args[2]
        else:
            sort = 'now'

        sub = self.reddit_session.get_subreddit(subreddit)

        self.add_items(sub.search('', limit=limit, sort=sort))


    # Commands for filtering. {{{2
    def do_submission(self, arg): # {{{3
        '''submission: filter out all but links and self posts'''
        # Unit-tested.
        self.filter_items(is_submission)
    do_subs = do_submission

    def do_comment(self, arg): # {{{3
        '''comment: filter out all but comments'''
        # Unit-tested.
        self.filter_items(is_comment)
    do_coms = do_comment

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

        Be careful, because '|', '<', and '>' are used by cmd2 to pipe
        output into files. You can't even get away with '\|'.

        Also implicitely filters out comments.
        '''
        # TODO: Fix piping issue. (see docstring above) Also applies to ntitle.
        #       title "foo|bar" works fine and so does title 'foo|bar'

        self.title_ntitle(invert=False, arg=arg)

    def do_ntitle(self, arg): # {{{3
        '''
        ntitle <regex>: filter out anything whose title matches <regex>

        You can have spaces in your command, like "ntitle asdf fdsa", but don't
        put any quotation marks if you don't want them taken as literal
        characters!

        Be careful, because '|', '<', and '>' are used by cmd2 to pipe
        output into files. You can't even get away with '\|'.

        Also implicitely filters out comments.
        '''
        self.title_ntitle(invert=True, arg=arg)

    # Commands for viewing list items. {{{2
    def do_ls(self, arg): # {{{3
        '''
        ls [start [n=10]]: list items, with [start] list [n] items starting at
        [start]
        '''
        args = arg.split()

        to_print = self.items

        if len(args) > 0:
            try:
                start = int(args[0])
            except ValueError:
                print "got invalid <start> (not a number)"
                return

            if len(args) > 1:
                try:
                    n = int(args[1])
                except ValueError:
                    print "got invalid <n> (not a number)"
                    return

                to_print = to_print[start : start+n]
            else:
                to_print = to_print[start:]

        for i, v in enumerate(to_print):
            self.print_item(i, v)

    def do_head(self, arg): # {{{3
        '''head [n=10]: show first [n] items'''
        try:
            n = int(arg.split()[0])
        except IndexError:
            n = 10
        except ValueError:
            print "That's not a number!"
            return

        for i, v in enumerate(self.items[:n]):
            self.print_item(i, v)

    def do_tail(self, arg): # {{{3
        '''tail [n=10]: show last [n] items'''
        try:
            n = int(arg.split()[0])
        except IndexError:
            n = 10
        except ValueError:
            print "That's not a number!"
            return

        for i, v in enumerate(self.items[-n:]):
            self.print_item(i, v)

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
    do_vs = do_view_subs

    def do_get_links(self, arg): # {{{3
        '''
            get_links [sub]...: generates an HTML file with all the links to
            everything (or everything in a given subreddit(s)) and opens it in
            your default browser.
            UNTESTED
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
    do_gl = do_get_links


    # Commands for doing stuff with the items. {{{2
    def do_open(self, arg):
        '''
        open [sub]...: open all items using the webbrowser module. optionally
        filter by sub(s)
        progress indicator UNTESTED
        '''

        target_items = self.arg_to_matching_subs(arg)

        if len(target_items) >= 20:
            yes_no_prompt = ("You're about to open {} different tabs. Are you"
                " sure you want to continue?").format(len(target_items))

            if not yes_no(False, yes_no_prompt):
                return

        len_ = len(target_items)
        rjust_num = len(str(len_))
        for i, item in enumerate(target_items):
            print '\r' + str(i).rjust(rjust_num) + '/' + str(len_),
            webbrowser.open( praw_object_url(item) )

    def do_open_with(self, arg):
        '''open_with <command>: run command on all URLs UNTESTED'''
        #TODO: This is a really ugly way to handle this.

        if arg == '':
            print 'No command specified!'
            return

        for i in map(praw_object_to_string, self.items):
            # "2>/dev/null" pipes away stderr
            os.system('{arg} "{i}"'.format(**locals()))

    def do_save_to(self, arg):
        '''save_to <file>: save URLs to file'''
        try:
            filename = arg.split()[0]
        except ValueError:
            print 'No file specified!'
            return

        file_ = open(filename, 'w')
        print_all(self.items, file_) # TODO print_all deprecated

    def do_upvote(self, arg):
        # NOTE untested for comments
        '''upvote: upvote EVERYTHING'''
        continue_ = yes_no(False, "You're about to upvote EVERYTHING in the"
            " current list. Do you really want to continue?")

        if continue_:
            len_ = len(self.items)

            for k, v in enumerate(self.items):
                print "\r{k}/{len_}".format(**locals()),

                v.upvote()

            print ""
        else:
            print "Cancelled. Phew."

    def do_clear_vote(self, arg):
        '''clear_vote: clear vote on EVERYTHING - UNTESTED'''
        continue_ = yes_no("You're about to clear your votes on EVERYTHING"
            " in the current list. Do you really want to continue? [yN]")

        if continue_:
            len_ = len(self.items)

            for k, v in enumerate(self.items):
                print "\r{k}/{len_}".format(**locals()),

                v.clear_vote()

            print ""
        else:
            print "Cancelled. Phew."

# Init code. {{{1
if __name__ == '__main__':
    print VERSION

    login = raw_input('login? [Yn]')
    if not login in 'Nn' or login == '':
        # TODO: Use OAuth or everything will be slowed down on purpose.
        r.login(disable_warning=True)
        #r = example_oauth_webserver.get_r(VERSION)

        print "If everything worked, this should be your link karma: " + str(r.user.link_karma)
        print

    prawtoys = PRAWToys(r)
    while True:
        try:
            prawtoys.cmdloop()
            break
        except KeyboardInterrupt:
            break
        except Exception as err:
            print 'Error:', err
