#! usr/bin/env python3

from os.path import isfile
import sys
import pprint
import praw
import time
import argparse
import pandas as pd

# Get credentials from DEFAULT instance in praw.ini

class Scraper:

    # Checkpoint defines savepoints (save everytime n number of comments are collected).
    def __init__(self, sub_reddit, checkpoint=None, minimum=None):
        self.exectime = time.time()
        self.ids = []
        self.checkpoint = checkpoint
        self.interval = checkpoint
        self.minimum = minimum
        # By default, save everytime 5000 new comments are collected.
        if self.checkpoint is None:
            self.checkpoint = 10000
            self.interval = 10000
        if self.minimum is None:
            self.minimum = 200000
        if self.minimum < self.checkpoint:
            print("The minimum number (default: 200k) of records has to larger than checkpoint (default: 10k)")
            sys.exit()
        self.commentdata = {"comment_body": [],
                            "upvotes": [], "comment_ids": [], "author_ids": []}
        self.gildings = {"comment_ids": [], "gilds": [], "numgilds": []}
        self.author = {"author_ids": [], "comment_karma": [],
                       "link_karma": [], "created_utc": [], "is_premium": []}
        self.reddit = praw.Reddit()
        self.subreddit = self.reddit.subreddit(sub_reddit).top(limit=None)

    def retrieveUser(self, comment):
        """Takes in comment object as a parameter, which is used to obtain author information such as:
        Author id: is used as the shared column to merge with comments data table
        Comment karma, Link karma, and Premium Status (is_gold)"""

        self.author["author_ids"].append(comment.author.id)
        self.author["comment_karma"].append(
            comment.author.comment_karma)
        self.author["link_karma"].append(comment.author.link_karma)
        self.author["created_utc"].append(
            comment.author.created_utc)
        self.author["is_premium"].append(comment.author.is_gold)

    def retrieveComment(self, comment):
        """Takes in comment object as a parameter, which is used to obtain comment id, comment body
        and gilded information (only retrieved if the comment has received gilds).

        # Comment_id is used as the shared column for merging comment and gild data.

        Comment object is passed to parseUser function to obtain author information.
        
        Note that some suspended users will still be retrieved (i.e. their comments will be added, however
        their accounts won't have suspended attribute, but will return a 404 error). We will have to remove
        such comments if the author information cannot be found from authors data table.
        """

        # Skip if the comment has been deleted or if the user is suspended/deleted.

        suspended = None
        try:
            suspended = comment.author.is_suspended
        except:
            pass
        if (comment.author is None or comment.body is None or suspended != None):
            pass
        else:
            if (comment.author_fullname[3:] in self.author["author_ids"]):
                pass
            else:
                try:
                    self.retrieveUser(comment)
                except Exception as e:
                    pprint.pprint(vars(comment.author))
                    print(e)
                    return None
            self.commentdata["comment_ids"].append(comment.id)
            self.commentdata["comment_body"].append(comment.body)
            self.commentdata["upvotes"].append(comment.score)
            self.commentdata["author_ids"].append(comment.author_fullname[3:])
            if comment.gilded > 0:
                self.gildings["comment_ids"].append(comment.id)
                self.gildings["gilds"].append(comment.gildings)
                self.gildings["numgilds"].append(comment.gilded)
                    

    def addTo(self):
        """Takes the subreddit input from user as a parameter, calls respective method for retrieving relevant data."""

        for submission in self.subreddit:
            if (submission.id not in self.ids):
                self.ids.append(submission.id)
                submission.comments.replace_more(limit=None)
                all_comments = submission.comments.list()
                for comment in all_comments:
                    # comment.refresh()
                    self.retrieveComment(comment)
                self.save_files()

    def save_files(self):
        """Saves the files for every checkpoints, exits the program when minimum number of records is reached"""
        length  = len(self.commentdata["comment_ids"])
        if (length < self.checkpoint):
            pass
        else:
            t = time.localtime()
            current_time = time.strftime("%H:%M:%S", t)
            print("Collected {} records so far; Saving in progress. Time now: {}".format(length, current_time))
            data_f = pd.DataFrame(self.commentdata)
            authors_f = pd.DataFrame(self.author)
            gildings_f = pd.DataFrame(self.gildings)
            data_f.to_csv('data/comment_data.csv', mode="w", index=False)
            authors_f.to_csv('data/author_data.csv', mode="w", index=False)
            gildings_f.to_csv('data/gildings_data.csv', mode="w", index=False)
            self.checkpoint += self.interval
        if (length > self.minimum):
            self.exectime = ((time.time() - self.exectime ) / (60*60))
            print("Collected {} records so far; Exiting now. Total execution time: {} hours".format(length, self.exectime))
            sys.exit()
        
        


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sub_reddit", help="Specify the subreddit to scrape from")
    parser.add_argument("-m", "--minimum", help="Specify the minimum number of data records to collect",
                        type=int)
    parser.add_argument("-c", "--checkpoint",
                        help="Save the file every c comments", type=int)
    args = parser.parse_args()
    if (args.minimum and args.checkpoint):
        Scraper(args.sub_reddit, checkpoint=args.checkpoint,
                 minimum=args.minimum).addTo()
    if (args.minimum):
        Scraper(args.sub_reddit, minimum=args.minimum).addTo()
    if (args.checkpoint):
        Scraper(args.sub_reddit, checkpoint=args.checkpoint).addTo()
    Scraper(args.sub_reddit).addTo()


if __name__ == "__main__":
    main()
