import praw

# When displaying comments/submissions, how many characters should we show?
# I.E., how many characters wide should we assume the user's terminal window is?
ASSUMED_CONSOLE_WIDTH = 80

def check_praw_version(min_version):
    ''' Checks if the current praw version is at least min_version.

    >>> import praw
    >>> praw.__version__ = '3.5.0'
    >>> check_praw_version('3.0.0')
    True
    >>> check_praw_version('4.0.0')
    False
    '''
    global praw

    min_version  = [int(i) for i in min_version.split('.')]
    praw_version = [int(i) for i in praw.__version__.split('.')]

    if len(min_version) != 3:
        raise ValueError('min_version must be in the form:'
            ' version.subversion.bugfix')
    elif len(praw_version) != 3:
        raise RuntimeError('Unable to parse praw.__version__: '
            + repr(praw.__version__))

    for min, praw_ in zip(min_version, praw_version):
        if praw_ < min:
            return False

    return True

def is_comment(submission):
    return isinstance(submission, praw.objects.Comment)

def is_submission(submission):
    return isinstance(submission, praw.objects.Submission)

def comment_str(comment:praw.objects.Comment,
        characters_needed=0) -> str:
    '''
    Convert a comment into to a string that perfectly fits on a terminal that's
    ASSUMED_CONSOLE_WIDTH characters wide.

    +-----------------------------------------------+
    | >>> ASSUMED_CONSOLE_WIDTH = 45                |
    | >>> print(comment_str(foo))                   |
    | 123: This is an ex... :: /r/example_subreddit |
    +-----------------------------------------------+

    characters_needed is for code that wants to print comment_str with other
    stuff on the same line. For example:

    +-----------------------------------------------+
    | >>> ASSUMED_CONSOLE_WIDTH = 45                |
    | >>> print("123: " + comment_str(foo))         |
    | 123: What did you just fucking... :: /r/circl |
    | ejerk                                         |
    +-----------------------------------------------+

    Notice how the "123: " makes the string 5 characters too long? Now watch
    this:

    +-----------------------------------------------+
    | >>> ASSUMED_CONSOLE_WIDTH = 45                |
    | >>> print("123: " + comment_str(foo, 5))      |
    | 123: What did you just fu... :: /r/circlejerk |
    +-----------------------------------------------+

    It's perfectly lined up with the terminal size.
    '''
    # TODO: Instead of taking characters_needed, take a header string and a
    #       footer string and combine them together inside this function.
    #       I'm procrastinating on this because I'd need to rewrite a lot of
    #       code in a lot of different places, and I'm still not 100% sure that
    #       It's a good approach yet.
    max_width = ASSUMED_CONSOLE_WIDTH - characters_needed

    subreddit_indicator = ' :: /r/' + comment.subreddit.display_name

    # How much width do we have left to fill up with the text of the comment?
    # Most comments are pretty long, so we should use as much space as we can
    # spare.
    max_comment_width = max_width - len(subreddit_indicator)

    # We shorten str(comment) to be only max_width characters long here, to
    # potentially save on processing power in the later code, where we
    # str.replace a bunch of special characters. Imagine if this comment were
    # 10,000 characters long or something. That's a lot of replacement that
    # wouldn't accomplish anything.
    comment_text = str(comment)[:max_width]

    # Actually printing these characters would result in very messy output, so
    # replace them with something a little more readable.
    comment_text.replace('\n', '\\n')
    comment_text.replace('\t', '\\t')
    comment_text.replace('\r', '\\r')

    comment_text = ahto_lib.shorten_string(str(comment), max_comment_width)
    return comment_text + subreddit_indicator

def submission_str(submission:praw.objects.Submission,
        characters_needed=0) -> str:
    '''
    convert a submission to a string

    See comment_str for more information about this code.
    '''
    max_width = ASSUMED_CONSOLE_WIDTH - characters_needed

    subreddit_indicator = ' :: /r/' + submission.subreddit.display_name
    max_title_width = max_width - len(subreddit_indicator)

    # As far as I know, reddit submissions can't have tabs, newlines, or
    # carriage returns in their text. So it shouldn't be necessary to escape
    # those like we did in comment_str.
    title = ahto_lib.shorten_string(submission.title, max_title_width)

    return title + subreddit_indicator

def praw_object_to_string(praw_object, characters_needed=0):
    ''' only works on submissions and comments

    BE CAREFUL! Sometimes returns a Unicode string. Use str.encode.
    This might not actually matter now that we're using Python 3.

    See comment_str for an explanation of how characters_needed works.
    '''
    if is_submission(praw_object):
        return submission_str(praw_object, characters_needed)
    elif is_comment(praw_object):
        return comment_str(praw_object, characters_needed)

def praw_object_url(praw_object):
    ''' returns a unicode url for the given submission or comment '''
    if is_submission(praw_object):
        return praw_object.short_link
    elif is_comment(praw_object):
        return praw_object.permalink + '?context=824545201'
    else:
        raise ValueError(
            "praw_object_url only handles submissions and comments")

