# Imports. {{{1
import unittest
import unittest.mock
import io

import prawtoys
import praw_tools

# TODO: Switch over to pytest.


# Lookalike classes. {{{1
class SubredditLookalike(object):  # {{{2
    def __init__(self, display_name):
        self.display_name = display_name


class PostLookalike(object):  # {{{2
    '''A generic for CommentLookalike and SubmissionLookalike'''
    def __init__(self, subreddit):
        if isinstance(subreddit, SubredditLookalike):
            self.subreddit = subreddit
        else:
            self.subreddit = SubredditLookalike(subreddit)


class CommentLookalike(PostLookalike):  # {{{2
    '''Designed to generate test data for PRAWToys to munch on.'''
    def __init__(self, text='foo', subreddit='foo', url='http://foo/',
                 submission=None):
        self.text       = text
        self.submission = submission or SubmissionLookalike()
        self.permalink  = url
        super(CommentLookalike, self).__init__(subreddit)

    def __str__(self):
        return self.text


class SubmissionLookalike(PostLookalike):  # {{{2
    '''Designed to generate test data for PRAWToys to munch on.'''
    def __init__(self, title='foo', subreddit='foo', url='http://foo/',
                 is_self=False, comments=[], over_18=False):
        self.title      = title
        self.short_link = url
        # TODO: Do submissions have a permalink parameter?
        # self.permalink  = url
        self.is_self    = is_self
        self.comments   = comments
        self.over_18    = over_18
        super(SubmissionLookalike, self).__init__(subreddit)

# Monkey patch is_comment and is_submission to recognize the Lookalikes. {{{1
is_comment_backup = praw_tools.is_comment
def is_comment(submission):
    return (isinstance(submission, CommentLookalike) or
        is_comment_backup(submission))
praw_tools.is_comment = is_comment

is_submission_backup = praw_tools.is_submission
def is_submission(submission):
    return (isinstance(submission, SubmissionLookalike) or
        is_submission_backup(submission))
praw_tools.is_submission = is_submission


# The actual tests. {{{1
class GenericPRAWToysTest(unittest.TestCase):  # {{{2
    def __init__(self, *args, **kwargs):
        """ Same arguments as unittest.TestCase """
        self.output   = io.StringIO()
        self.prawtoys = prawtoys.PRAWToys(stdout=self.output)

        super(GenericPRAWToysTest, self).__init__(*args, **kwargs)

    def setUp(self):
        ''' This gets run before every test_* function. '''
        pass

    def tearDown(self):
        ''' This gets run after every test_* function. '''
        self.output.truncate(0)
        self.prawtoys.items = []

    def cmd(self, *args, **kwargs):
        ''' Shortcut for self.prawtoys.onecmd '''
        return self.prawtoys.onecmd(*args, **kwargs)

    def reset(self):
        return self.cmd('reset')

    def assertAllItems(self, f):
        for i in self.prawtoys.items:
            self.assertTrue(f(i))

    def assertInOutput(self, s, clear_after=True):
        self.assertTrue(s in self.output.getvalue())

        if clear_after:
            self.output.truncate(0)


class Offline(GenericPRAWToysTest):  # {{{2
    TEST_DATA = [
        'foo', 'bar', 'baz', 'foo', 'qux', '\xfcmlaut', '\u2603_snowman']

    BOOL_TEST_DATA = [True, True, False, True, False, False, True]

    def test_reset(self):
        self.prawtoys.items = ['foo']
        self.cmd('reset')
        self.assertTrue(self.prawtoys.items == [])

    def data_tester(self, data):
        '''Example of how this is used:

        dt = self.data_tester(
            [SubmissionLookalike(subreddit=i) for i in self.TEST_DATA])

        dt('sub foo bar', lambda i:
            i.subreddit.display_name.lower() in ['foo', 'bar'])
        '''
        def func(cmd_string, lambda_func):
            self.prawtoys.items = data[:]
            self.cmd(cmd_string)
            self.assertAllItems(lambda_func)

        return func

    def test_sub_nsub(self):
        dt = self.data_tester([
            SubmissionLookalike(subreddit=i) for i in self.TEST_DATA])

        # There's no reason to do display_name.lower() here, since the
        # TEST_DATA is already all lowercase, but it's important to keep up
        # the habit.
        dt('sub foo bar', lambda i:
            i.subreddit.display_name.lower() in ['foo', 'bar'])

        dt('nsub foo bar', lambda i:
            i.subreddit.display_name.lower() not in ['foo', 'bar'])

    def test_title_ntitle(self):
        dt = self.data_tester(
            [SubmissionLookalike(title=i) for i in self.TEST_DATA])

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
            praw_tools.is_comment(i) or i.over_18)

        dt('sfw', lambda i:
            praw_tools.is_comment(i) or not i.over_18)

    def test_self_nself(self):
        dt = self.data_tester(
            [SubmissionLookalike(is_self=i) for i in self.BOOL_TEST_DATA])

        dt('self', lambda i: i.is_self)
        dt('nself', lambda i: not i.is_self)

    def test_undo(self):
        def test_undo_on(cmd, data):
            self.prawtoys.items = data[:]

            self.cmd(cmd)
            self.assertTrue(self.prawtoys.items != data)

            self.cmd('undo')
            self.assertTrue(self.prawtoys.items == data)

        test_undo_on(
            'title foo',
            [SubmissionLookalike(title=i) for i in self.TEST_DATA])

        test_undo_on(
            'sfw',
            [SubmissionLookalike(over_18=i) for i in self.BOOL_TEST_DATA])

    def test_x(self):
        self.cmd('x self.test_worked = True')
        self.assertTrue(
            hasattr(self.prawtoys, 'test_worked')
            and self.prawtoys.test_worked)

        self.output.truncate(0)
        self.cmd('x self.test_worked')
        self.assertInOutput('True\n')

    def test_width(self):
        self.cmd('width')
        self.assertInOutput(
            'width = ' + str(prawtoys.praw_tools.ASSUMED_CONSOLE_WIDTH) + '\n')

        old_width = prawtoys.praw_tools.ASSUMED_CONSOLE_WIDTH
        self.cmd('width 120')
        self.assertTrue(prawtoys.praw_tools.ASSUMED_CONSOLE_WIDTH == 120)

        self.cmd('width ' + str(old_width))
        self.assertTrue(prawtoys.praw_tools.ASSUMED_CONSOLE_WIDTH == old_width)

    def test_submission_and_comment(self):
        test_data  = [CommentLookalike(i, i, i)    for i in self.TEST_DATA]
        test_data += [SubmissionLookalike(i, i, i) for i in self.TEST_DATA]

        self.data_tester(test_data)('submission', praw_tools.is_submission)
        self.data_tester(test_data)('comment',    praw_tools.is_comment)


class Online(GenericPRAWToysTest):  # {{{2
    def test_user(self):
        self.cmd('user winter_mutant 10')
        self.assertTrue(len(self.prawtoys.items) == 10)

        self.assertAllItems(
            lambda i: i.author.name == 'winter_mutant')

        self.cmd('ls')

    def test_user_comments(self):
        self.cmd('user_comments winter_mutant 10')
        self.assertTrue(len(self.prawtoys.items) == 10)

        self.assertAllItems(
            lambda i:
                praw_tools.is_comment(i)
                and i.author.name == 'winter_mutant')

        self.cmd('ls')

    def test_user_submissions(self):
        self.cmd('user_submissions winter_mutant 10')
        self.assertTrue(len(self.prawtoys.items) == 10)

        self.assertAllItems(
            lambda i:
                praw_tools.is_submission(i)
                and i.author.name == 'winter_mutant')

        self.cmd('ls')

    def test_get_from(self):
        def creatively_named_function(cmd_string, limit, lambda_func):
            self.cmd(cmd_string)
            self.assertTrue(len(self.prawtoys.items) == limit)
            self.assertAllItems(lambda_func)
            self.cmd('ls')
            self.reset()

        creatively_named_function(
            'get_from askreddit 10 top',
            10,
            lambda i: i.subreddit.display_name.lower() == 'askreddit')

        creatively_named_function(
            'get_from aww 9 new',
            9,
            lambda i: i.subreddit.display_name.lower() == 'aww')

        creatively_named_function(
            'get_from awwnime 8 rising',
            8,
            lambda i: i.subreddit.display_name.lower() == 'awwnime')
