# prawtoys

## The swiss army knife of karma whoring.

prawtoys is a utility based on the syntax of URLToys. You can use it to filter,
interact with, and play with reddit comments and submissions.

Get the 10 top posts from AskReddit, and open them in the browser:

    0> get_from AskReddit 10 top
    10> open
    10/10
    10>

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

First of all, install Python 3 and make sure it's in your PATH. Then run:

    python -m pip install praw<4.0.0 praw-oauth2util<1.0.0

Then, run prawtoys with:

    python prawtoys.py

If that doesn't work, it could mean that you have a pre-existing copy of `praw` or `praw-oauth2util`. You can fix that with:

    python -m pip uninstall praw praw-oauth2util
    python -m pip install praw<4.0.0 praw-oauth2util<1.0.0

However, it might break other programs that expect later versions of `praw`.

You can also test prawtoys to make sure it's running properly:

    python -m unittest -v tests

## Notes

Just a small warning: This script is a little bit slow if you give it too much
to chew on, so be ready for that.
