# vim: foldmethod=marker
# Imports. {{{1
import unittest
import prawtoys
import praw

# Lookalike classes. {{{1
class SubredditLookalike(object): # {{{2
    def __init__(self, display_name):
        self.display_name = display_name

class PostLookalike(object): # {{{2
    '''A generic for CommentLookalike and SubmissionLookalike'''
    def __init__(self, subreddit):
        if isinstance(subreddit, SubredditLookalike):
            self.subreddit = subreddit
        else:
            self.subreddit = SubredditLookalike(subreddit)

class CommentLookalike(PostLookalike): # {{{2
    '''Designed to generate test data for PRAWToys to munch on.'''
    def __init__(self, text='foo', subreddit='foo', url='http://foo/',
            submission=None):
        self.text       = text
        self.submission = submission or SubmissionLookalike()
        self.permalink  = url
        super(CommentLookalike, self).__init__(subreddit)

    def __str__(self):
        return self.text

class SubmissionLookalike(PostLookalike): # {{{2
    '''Designed to generate test data for PRAWToys to munch on.'''
    def __init__(self, title='foo', subreddit='foo', url='http://foo/',
            is_self=False, comments=[], over_18=False):
        self.title      = title
        self.short_link = url
        #self.permalink  = url # TODO: Do submissions have a permalink parameter?
        self.is_self    = is_self
        self.comments   = comments
        self.over_18    = over_18
        super(SubmissionLookalike, self).__init__(subreddit)

# Monkey patch is_comment and is_submission to recognize the Lookalikes. {{{1
is_comment_backup = prawtoys.is_comment
def is_comment(submission):
    return (isinstance(submission, CommentLookalike) or
        is_comment_backup(submission))
prawtoys.is_comment = is_comment

is_submission_backup = prawtoys.is_submission
def is_submission(submission):
    return (isinstance(submission, SubmissionLookalike) or
        is_submission_backup(submission))
prawtoys.is_submission = is_submission

# The actual tests. {{{1
class GenericPRAWToysTest(unittest.TestCase): # {{{2
    def setUp(self):
        ''' This gets run before every test_* function. '''
        if not hasattr(self, 'prawtoys'):
            self.prawtoys = prawtoys.PRAWToys()
        else:
            self.reset()

    def cmd(self, *args, **kwargs):
        ''' Shortcut for self.prawtoys.onecmd '''
        return self.prawtoys.onecmd(*args, **kwargs)

    def reset(self):
        return self.cmd('reset')

    def assert_all_items(self, f):
        for i in self.prawtoys.items:
            self.assertTrue( f(i) )

class TestOffline(GenericPRAWToysTest): # {{{2
    TEST_DATA      = ['foo', 'bar', 'baz', 'foo', 'qux', u'\xfcmlaut']
    BOOL_TEST_DATA = [True, True, False, True, False, False, True]

    def test_reset(self):
        self.prawtoys.items = ['foo']
        self.cmd('reset')
        self.assertTrue(self.prawtoys.items == [])

    def data_tester(self, data):
        def func(cmd_string, lambda_func):
            self.prawtoys.items = data[:]
            self.cmd(cmd_string)
            self.assert_all_items(lambda_func)

        return func

    def test_sub_nsub(self):
        dt = self.data_tester([
            SubmissionLookalike(subreddit=i) for i in self.TEST_DATA])

        # There's no reason to do display_name.lower() here, since the TEST_DATA
        # is already all lowercase, but it's important to keep up the habit.
        dt('sub foo bar', lambda i:
            i.subreddit.display_name.lower() in ['foo', 'bar'])

        dt('nsub foo bar', lambda i:
            i.subreddit.display_name.lower() not in ['foo', 'bar'])

    def test_title_ntitle(self):
        dt = self.data_tester([
            SubmissionLookalike(title=i) for i in self.TEST_DATA])

        dt('title foo', lambda i: 'foo' in i.title)

        dt('title ba[rz]', lambda i:
            'bar' in i.title or 'baz' in i.title)

        dt('ntitle foo', lambda i: 'foo' not in i.title)

        dt('ntitle ba[rz]', lambda i:
            'bar' not in i.title and 'baz' not in i.title)

    def test_sfw_nsfw(self):
        test_data = [
            SubmissionLookalike(over_18=i) for i in self.BOOL_TEST_DATA]

        test_data += [
            CommentLookalike(i, i, i) for i in self.TEST_DATA]

        dt = self.data_tester(test_data)

        dt('nsfw', lambda i:
            is_comment(i) or i.over_18)

        dt('sfw', lambda i:
            is_comment(i) or not i.over_18)

    def test_self_nself(self):
        dt = self.data_tester([
            SubmissionLookalike(is_self=i) for i in self.BOOL_TEST_DATA])

        dt('self', lambda i: i.is_self)
        dt('nself', lambda i: not i.is_self)

    def test_x(self):
        self.cmd('x self.test_worked = True')
        self.assertTrue(
            hasattr(self.prawtoys, 'test_worked')
            and self.prawtoys.test_worked)

    def test_submission_and_comment(self):
        test_data  = [CommentLookalike(i, i, i)    for i in self.TEST_DATA]
        test_data += [SubmissionLookalike(i, i, i) for i in self.TEST_DATA]

        self.data_tester(test_data)('submission', prawtoys.is_submission)
        self.data_tester(test_data)('comment',    prawtoys.is_comment)

class TestOnline(GenericPRAWToysTest): # {{{2
    def test_user(self):
        self.cmd('user winter_mutant 10')
        self.assertTrue(len(self.prawtoys.items) == 10)

        self.assert_all_items(lambda i:
            i.author.name == 'winter_mutant')

    def test_user_comments(self):
        self.cmd('user_comments winter_mutant 10')
        self.assertTrue(len(self.prawtoys.items) == 10)

        self.assert_all_items(lambda i:
            prawtoys.is_comment(i)
            and i.author.name == 'winter_mutant')

    def test_user_submissions(self):
        self.cmd('user_submissions winter_mutant 10')
        self.assertTrue(len(self.prawtoys.items) == 10)

        self.assert_all_items(lambda i:
            prawtoys.is_submission(i)
            and i.author.name == 'winter_mutant')

    def test_get_from(self):
        def creatively_named_function(cmd_string, limit, lambda_func):
            self.cmd(cmd_string)
            self.assertTrue(len(self.prawtoys.items) == limit)
            self.assert_all_items(lambda_func)
            self.reset()

        creatively_named_function('get_from askreddit 10 top', 10, lambda i:
            i.subreddit.display_name.lower() == 'askreddit')

        creatively_named_function('get_from aww 9 new', 9, lambda i:
            i.subreddit.display_name.lower() == 'aww')

        creatively_named_function('get_from awwnime 8 rising', 8, lambda i:
            i.subreddit.display_name.lower() == 'awwnime')
