#!/usr/bin/python
# vim: foldmethod=marker
#TODO: Nodupes command, praw.objects.Submission has .__eq__() so == should work.
#TODO: Only ask user for login if needed
#TODO: head ls and tail should show indicies
#TODO: Progress indicator when loading items.
#TODO: Login through cmd.
#TODO: nsub and sub could take multiple subreddit arguments.
#TODO: self and nself. praw.object.Submission.is_self

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
#import example_oauth_webserver

# Constants and functions. {{{1
VERSION = "PRAWToys 0.6.0"

# When displaying comments, how many characters should we show?
MAX_COMMENT_TEXT = 80

def yes_no(default, question): # {{{2
    ''' default can be True, False, or None '''
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

class PRAWToys(cmd.Cmd): # {{{1
    prompt = '0> '

    def __init__(self, reddit_session, *args, **kwargs): # {{{2
        # Don't use raw input if we can use the better alternative. (readline)
        self.use_rawinput = not (
            callable(sys.stdout.write) and callable(sys.stdin.readline))

        self.items = []
        self.reddit_session = reddit_session

        #  super() doesn't work on old-style classes like cmd.Cmd :(
        cmd.Cmd.__init__(self, *args, **kwargs)

    # General settings. {{{2
    def emptyline(self): pass # disable empty line repeating the last command

    def postcmd(self, r, l):
        """
        Change the prompt to show how many matches there are. Like URLToys.
        """
        self.prompt = str(len(self.items)) + '> '

    def do_EOF(self, arg):
        exit(0)
    do_exit = do_EOF

    # Internal utility methods. {{{2
    def add_items(self, l):
        self.old_items = self.items[:]
        self.items += list(l)

    def filter_items(self, f):
        self.old_items = self.items
        self.items = filter(f, self.items)

    def print_item(self, index, item=None):
        if item == None:
            item = self.items[index]

        rjust_number = len(str(len(self.items)))
        index_str    = str(index).rjust(rjust_number)

        item_str = praw_object_to_string(item).encode(
            encoding='ascii', errors='backslashreplace')

        print '{index_str}: {item_str}'.format(**locals())

    # Undo and reset. {{{2
    def do_undo(self, arg):
        '''undo: undoes last command'''
        self.items = self.old_items[:]
    do_u = do_undo

    def do_reset(self, arg):
        '''reset: clear all items'''
        self.items = []

    # Debug commands. {{{2
    def do_x(self, arg):
        '''
        x <command>: execute <command> as python code and pretty-print the
        result (if any)
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

    # Commands to add items. {{{2
    def do_submission(self, arg):
        '''submission: filter out all but links and self posts'''
        self.filter_items(is_submission)
    do_subs = do_submission

    def do_comment(self, arg):
        '''comment: filter out all but comments'''
        self.filter_items(is_comment)
    do_coms = do_comment

    def do_saved(self, arg):
        '''saved: get your saved items'''
        self.add_items(
            self.reddit_session.user.get_saved(limit=None)
        )

    def do_mine(self, arg):
        '''mine: get your own submitted items'''
        self.add_items(
              list(self.reddit_session.user.get_submitted(limit=None))
            + list(self.reddit_session.user.get_comments(limit=None))
        )

    def do_user(self, arg):
        '''user <username>: get a user's submitted items'''
        user = self.reddit_session.get_redditor(arg.split()[0])
        self.add_items(
              list(user.get_submitted(limit=None))
            + list(user.get_comments(limit=None))
        )

    def do_mysubs(self, arg):
        '''mysubs: get your submissions'''
        self.add_items(
            list(self.reddit_session.user.get_submitted(limit=None)))

    def do_mycoms(self, arg):
        '''mycoms: get your comments'''
        self.add_items(
            list(self.reddit_session.user.get_comments(limit=None)))

    def do_thread(self, arg):
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

    # Commands for filtering. {{{2
    def do_sub(self, arg):
        '''
        sub <subreddit>: filter out anything not in <subreddit>, don't
        include /r/
        '''
        target_sub = arg.split()[0].lower()

        self.filter_items(lambda x:
            x.subreddit.display_name.lower() == target_sub)

    def do_nsub(self, arg):
        '''nsub <subreddit>: filter out anything in <subreddit>, don't include /r/'''
        target_sub = arg.split()[0].lower()

        self.filter_items(lambda x:
            x.subreddit.display_name.lower() != target_sub)

    def do_sfw(self, arg):
        '''sfw: filter out anything nsfw'''
        self.filter_items(lambda x:
            # need to check is_comment or we'll get AttributeError
            is_comment(x) or not x.over_18)

    def do_nsfw(self, arg):
        '''nsfw: filter out anything sfw and all comments'''
        self.filter_items(lambda x:
            # need to check is_comment or we'll get AttributeError
            not is_comment(x) and x.over_18)

    def do_title(self, arg):
        '''
        title <regex>: filter out anything whose title doesn't match <regex>

        You can have spaces in your command, like "title asdf fdsa", but don't
        put any quotation marks if you don't want them taken as literal
        characters!

        Also implicitely filters out comments.
        '''
        self.filter_items(lambda x:
            not is_comment(x) and re.search(arg, x.title)
        )

    def do_ntitle(self, arg):
        '''
        ntitle <regex>: filter out anything whose title matches <regex>

        You can have spaces in your command, like "title asdf fdsa", but
        don't put any quotation marks if you don't want them taken as
        literal characters!

        Also implicitely filters out comments.
        '''
        self.filter_items(lambda x:
            not is_comment(x) and not re.search(arg, x.title)
        )

    def do_url(self, arg):
        '''
        url <regex>: filter out anything whose url doesn't match <regex>

        You can have spaces in your command, like "url asdf fdsa", but
        don't put any quotation marks if you don't want them taken as
        literal characters!

        Also implicitely filters out comments.
        '''
        self.filter_items(lambda x:
            not is_comment(x) and re.search(arg, x.title)
        )

    def do_nurl(self, arg):
        '''
        nurl <regex>: filter out anything whose url matches <regex>

        You can have spaces in your command, like "title asdf fdsa", but don't
        put any quotation marks if you don't want them taken as literal
        characters!

        Also implicitely filters out comments.
        '''
        self.filter_items(lambda x:
            not is_comment(x) and not re.search(arg, x.title)
        )

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
            get_links [sub]: generates an HTML file with all the links to
            everything (or everything in a given sub) and opens it in your
            default browser.
        '''
        target_items = self.items
        args = arg.split()

        if len(args) > 0:
            target_sub = args[0].lower()

            filter_func = (lambda i:
                i.subreddit.display_name.lower() == target_sub)

            target_items = filter(filter_func, target_items)

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
        '''open: open all items using the webbrowser module'''
        # TODO: Use webbrowser instead!
        if len(self.items) >= 20:
            continue_ = yes_no(False, ("You're about to open {} different tabs."
                " Are you sure you want to continue?").format(len(self.items)))

        for item in self.items:
            webbrowser.open( praw_object(item) )

    def do_open_with(self, arg):
        '''open_with <command>: run command on all URLs'''
        #TODO: This is a really ugly way to handle this.
        def get_link(submission):
            try:
                return submission.url
            except AttributeError:
                return comment_str(submission)

        if arg == '':
            print 'No command specified!'
            return

        for i in map(get_link, self.items):
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
        # NOTE untested
        '''clear_vote: clear vote on EVERYTHING'''
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

    def do_get_new(self, arg):
        # NOTE untested
        '''get_new <subreddit> [<n=1000>]: get <n> submissions from /r/<subreddit>/new'''

        try:
            arg = arg.split()
            subreddit = arg[0]
        except IndexError:
            print "No subreddit specified."
            return

        try:
            n = int(arg[1])
        except IndexError:
            n = 1000
        except ValueError:
            print "Invalid number: " + repr(n)
            return

        print "Getting {n} submissions to /r/{subreddit}.".format(**locals())
        sub = self.reddit_session.get_subreddit(subreddit)
        # NOTE itertools.islice?
        self.add_items(
            sub.get_new(limit=n)
        )

# Init code. {{{1
r = praw.Reddit(VERSION)
print VERSION

login = raw_input('login? [Yn]')
if not login in 'Nn' or login == '':
    # TODO: Use OAuth or everything will be slowed down on purpose.
    r.login(disable_warning=True)
    #r = example_oauth_webserver.get_r(VERSION)

    print "If everything worked, this should be your link karma: " + str(r.user.link_karma)

try:
    PRAWToys(r).cmdloop()
except KeyboardInterrupt:
    pass
