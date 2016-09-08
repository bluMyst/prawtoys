import unittest
import prawtoys
import praw

class SubredditLookalike(object):
    def __init__(self, display_name):
        self.display_name = display_name

class PostLookalike(object):
    '''A generic for CommentLookalike and SubmissionLookalike'''
    def __init__(self, subreddit):
        if isinstance(subreddit, SubredditLookalike):
            self.subreddit = subreddit
        else:
            self.subreddit = SubredditLookalike(subreddit)

class CommentLookalike(PostLookalike):
    '''Designed to generate test data for PRAWToys to munch on.'''
    def __init__(self, text='foo', subreddit='foo', url='http://foo/',
            submission=None):
        self.text       = text
        self.submission = submission or SubmissionLookalike()
        self.permalink  = url
        super(CommentLookalike, self).__init__(subreddit)

    def __str__(self):
        return self.text

class SubmissionLookalike(PostLookalike):
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

# Monkey patch is_comment and is_submission to recognize the Lookalikes.
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

class GenericPRAWToysTest(unittest.TestCase):
    def setUp(self):
        if not hasattr(self, 'prawtoys'):
            self.prawtoys = prawtoys.PRAWToys(prawtoys.r)
        else:
            self.reset()

    def cmd(self, *args, **kwargs):
        return self.prawtoys.onecmd(*args, **kwargs)

    def reset(self):
        return self.cmd('reset')

    def assert_all_items(self, f):
        for i in self.prawtoys.items:
            self.assertTrue( f(i) )

class TestOffline(GenericPRAWToysTest):
    TEST_DATA = ['foo', 'bar', 'baz', 'foo', 'qux']
    BOOL_TEST_DATA = [True, True, False, True, False, False, True]

    def test_reset(self):
        self.prawtoys.items = ['foo']
        self.cmd('reset')
        self.assertTrue(self.prawtoys.items == [])

    def data_tester(self, data):
        def func(cmd_string, lambda_func):
            self.prawtoys.items = data
            self.cmd(cmd_string)
            self.assert_all_items(lambda_func)

        return func

    def test_sub_nsub(self):
        dt = self.data_tester([
            SubmissionLookalike(subreddit=i) for i in self.TEST_DATA])

        dt('sub foo bar', lambda i:
            i.subreddit.display_name in ['foo', 'bar'])

        dt('nsub foo bar', lambda i:
            i.subreddit.display_name not in ['foo', 'bar'])

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
        dt = self.data_tester([
            SubmissionLookalike(over_18=i) for i in self.BOOL_TEST_DATA])

        dt('nsfw', lambda i: i.over_18)
        dt('sfw', lambda i: not i.over_18)

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

class TestOnline(GenericPRAWToysTest):
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
            i.subreddit.display_name == 'askreddit')

        creatively_named_function('get_from aww 9 new', 9, lambda i:
            i.subreddit.display_name == 'aww')
