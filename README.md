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

Requires Python 3. Try running `python --version` to make sure you're using the right version. On some Linux systems, Python 3 is installed as `python3`, where `python` is Python 2 instead. If that's the case (you can check with `python3 --version`), use `python3` in the below commands.

Because of compatibility issues with PRAW 4, PRAWToys needs to be run in a virtual environment. Here's how you set one up:

    python -m pip install virtualenv
    virtualenv virtualenv
    virtualenv/Scripts/pip install -r requirements.txt

To run PRAWToys:

    virtualenv/Scripts/python.exe prawtoys.py

To run unittests on PRAWToys:

    virtualenv/Scripts/python.exe -m unittest -v tests

## Notes

Just a small warning: This script is a little bit slow if you give it too much
to chew on, so be ready for that.
