# prawtoys

Based on the syntax of Perl's URLToys. Used to filter, interact with, and play
with reddit comments and submissions.

Get the 10 top sfw posts from AskReddit, and open them in the browser:

    0> get_from AskReddit 10 top
    10> open

Upvote every non-self-post in /r/free\_karma:

    0> get_from free_karma all
    386> nself
    272> upvote
    272/272
    272> 

See what subreddits gallowboob posts to most:

    0> user gallowboob
    1275> view_subs
      1 : /r/partyparrot
      1 : /r/dbz
      1 : /r/dataisbeautiful
    <snip>
     88 : /r/aww
    188 : /r/gifs
    277 : /r/pics

The possibilities are endless!

## Installing/running

First of all, install Python 2 and praw. You can install praw by running:

    python -m pip install praw

Then, run prawtoys with:

    python prawtoys.py

You can also test prawtoys to make sure it's running properly:

    python -m unittest -v tests

## Notes

Just a small warning: This script is a little bit slow if you give it too much
to chew on, so be ready for that.
