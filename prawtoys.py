#!/usr/bin/python
# vim: foldmethod=marker
#TODO: Nodupes command, praw.objects.Submission has .__eq__() so == should work.
#TODO: Only ask user for login if needed
#TODO: head ls and tail should show indicies

#TODO: do_* methods should error like this (python standard)
#      print '*** error text here'
#      return

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
VERSION = "PRAWToys 0.5.0"

# When displaying comments, how many characters should we show?
MAX_COMMENT_TEXT = 20

def is_comment(submission):
    return isinstance(submission, praw.objects.Comment)

def is_submission(submission):
    return isinstance(submission, praw.objects.Submission)

def comment_str(comment):
    '''convert a comment to a string'''
    comment_text = str(comment)

    if len(comment_text) > MAX_COMMENT_TEXT:
        comment_text = comment_text[:MAX_COMMENT_TEXT-3] + '...'

    context_link = comment.permalink + '?context=99'

    return "{comment_text} :: {context_link}".format(**locals())

def submission_str(submission):
    '''convert a submission to a string'''
    return submission.title +' :: /r/' + submission.subreddit.display_name + ' :: ' + submission.url

def print_all(submissions, file_=sys.stdout):
    '''print all submissions'''
    for i in submissions:
        if is_submission(i):
            try:
                file_.write(submission_str(i)+'\n')
            except UnicodeEncodeError:
                print '[Failed to .write() a submission (short_link:{}) here: UnicodeEncodeError]'.format(
                    repr(i.short_link))
        else:
            try:
                file_.write(comment_str(i)+'\n')
            except UnicodeEncodeError:
                print '[Failed to .write() a comment (permalink:{}) here: UnicodeEncodeError]'.format(
                    repr(i.permalink))

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

        # TODO: Test.
        #self.items = [i for i in self.items if f(i)]
        self.items = filter(f, self.items)

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
        '''sub <subreddit>: filter out anything not in <subreddit>, don't include /r/'''
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
        ''' title <regex>: filter out anything whose title doesn't match <regex>

            You can have spaces in your command, like "title asdf fdsa", but don't
            put any quotation marks if you don't want them taken as literal characters!

            Also implicitely filters out comments.
        '''
        self.filter_items(lambda x:
            not is_comment(x) and re.search(arg, x.title)
        )

    def do_ntitle(self, arg):
        ''' ntitle <regex>: filter out anything whose title matches <regex>

            You can have spaces in your command, like "title asdf fdsa", but don't
            put any quotation marks if you don't want them taken as literal characters!

            Also implicitely filters out comments.
        '''
        self.filter_items(lambda x:
            not is_comment(x) and not re.search(arg, x.title)
        )

    def do_url(self, arg):
        ''' url <regex>: filter out anything whose url doesn't match <regex>

            You can have spaces in your command, like "url asdf fdsa", but don't
            put any quotation marks if you don't want them taken as literal characters!

            Also implicitely filters out comments.
        '''
        self.filter_items(lambda x:
            not is_comment(x) and re.search(arg, x.title)
        )

    def do_nurl(self, arg):
        ''' nurl <regex>: filter out anything whose url matches <regex>

            You can have spaces in your command, like "title asdf fdsa", but don't
            put any quotation marks if you don't want them taken as literal characters!

            Also implicitely filters out comments.
        '''
        self.filter_items(lambda x:
            not is_comment(x) and not re.search(arg, x.title)
        )

    # Commands for viewing list items. {{{2
    def do_ls(self, arg): # {{{3
        '''ls [start [n=10]]: list items, with [start] list [n] items starting at [start]'''
        #TODO: Something is wrong with start and n options.
        args = arg.split()

        try:
            start = int(args[0])
        except IndexError:
            start = None
        except ValueError:
            print "That's not a number!"
            return

        try:
            n = int(args[1])
        except IndexError:
            n = 10
        except ValueError:
            print "That's not a number!"
            return

        print_all(
            self.items if not start else self.items[start : start+n])

    def do_head(self, arg): # {{{3
        '''head [n=10]: show first [n] items'''
        try:
            n = int(arg.split()[0])
        except IndexError:
            n = 10
        except ValueError:
            print "That's not a number!"
            return

        print_all(self.items[:n])

    def do_tail(self, arg): # {{{3
        '''tail [n=10]: show last [n] items'''
        try:
            n = int(arg.split()[0])
        except IndexError:
            n = 10
        except ValueError:
            print "That's not a number!"
            return

        print_all(self.items[-n:])

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
            get_links: generates an HTML file with all the links to everything
            and opens it in your default browser.
        '''
        with open('urls.html', 'w') as html_file:
            html_file.write('<html><body>')
            html_file.write('</body></html>')


    # Commands for doing stuff with the items. {{{2
    def do_open(self, arg):
        '''open: open all items using xdg-open'''
        self.do_open_with( 'xdg-open ' + arg )

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
        print_all(self.items, file_)

    def do_upvote(self, arg):
        # NOTE untested for comments
        '''upvote: upvote EVERYTHING'''
        continue_ = raw_input("You're about to upvote EVERYTHING in the current list. Do you really want to continue? [yN]")

        if continue_ in "yY":
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
        continue_ = raw_input("You're about to clear your votes on EVERYTHING in the current list. Do you really want to continue? [yN]")

        if continue_ in "yY":
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
