import unittest
import prawtoys
import praw

# TODO: Create lookalike classes for praw.objects.Comment and
# praw.objects.Submission

#test_r = praw.Reddit('PRAWToys unittester')
#test_submission = r.get_submission(submission_id='4lqc9m')
#test_comment = test_submission.comments[0]

# cmd.Cmd.onecmd('command')

class TestPRAWToysFiltering(unittest.TestCase):
    def setUp(self):
        self.prawtoys = prawtoys.PRAWToys(prawtoys.r)

    def test_sub_nsub(self):
        ''' tests reset, get_new (partially), undo, nsub, and sub '''
        self.prawtoys.onecmd('reset')
        self.assertTrue(self.prawtoys.items == [])

        self.prawtoys.onecmd('get_new aww 1')
        self.assertTrue(len(self.prawtoys.items) == 1)

        self.prawtoys.onecmd('get_new creepy 1')
        self.assertTrue(len(self.prawtoys.items) == 2)

        self.prawtoys.onecmd('get_new funny 1')
        self.assertTrue(len(self.prawtoys.items) == 3)

        self.prawtoys.onecmd('nsub aww creepy')
        self.assertTrue(len(self.prawtoys.items) == 1)
        self.assertTrue(
            self.prawtoys.items[0].subreddit.display_name == 'funny')

        self.prawtoys.onecmd('undo')
        self.assertTrue(len(self.prawtoys.items) == 3)

        self.prawtoys.onecmd('sub funny creepy')
        self.assertTrue(len(self.prawtoys.items) == 2)

        self.assertTrue(all(
            i.subreddit.display_name in ['funny', 'creepy']
            for i in self.prawtoys.items))
