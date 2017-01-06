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

Requires Python 3. To install, first make sure you have virtualenv installed. Run the following as an administrator / root:

    python3 -m pip install virtualenv

You may need to change `python3` to `python` to get it to work. If neither work, try (re-)installing Python 3.

From there, just run:

    python setup.py

Once that's done, you can run PRAWToys by using either `prawtoys.bat` or `prawtoys.sh` depending on your operating system.

## Notes

Just a small warning: This script is a little bit slow if you give it too much
to chew on, so be ready for that.
